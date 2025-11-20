"""
Cron schedulers for Smart System Operator.
- Metrics Crawler: Collects server metrics via command_get actions
- AI Analyzer: Consumes metrics and feeds to OpenAI for analysis
"""
import asyncio
import time
import json
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import jsonlog
import config as env_config
from database import DatabaseClient
from redis_cache import RedisClient
from servers import ServerManager
from action import ActionManager
from openai_client import OpenAIClient

logger = jsonlog.setup_logger("cron")

def _get_metrics_key(server_id: int) -> str:
    """Get Redis key for server metrics queue."""
    return f"smart_system:server_metrics:{server_id}"

def _get_now_time() -> str:
    """Get current datetime in GMT+7 timezone without milliseconds."""
    return (datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%S")


class MetricsCrawler:
    """Crawls server metrics using command_get actions."""
    
    def __init__(self, db_client: DatabaseClient, redis_client: RedisClient, delay_seconds: int = 60):
        self.db = db_client
        self.redis = redis_client
        self.delay_seconds = delay_seconds
        self.server_manager = ServerManager(db_client, redis_client)
        self.action_manager = ActionManager(db_client, redis_client)
        self.logger = logger
        self.running = False
        self.task = None
        
        # Default monitoring actions to execute (kept simple for speed)
        self.monitoring_actions = [
            'get_cpu_usage',
            'get_memory_usage'
        ]
    
    async def _collect_server_metrics(self, server: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Collect get metrics for a single server."""
        server_id = server['id']
        server_name = server['name']
        
        try:
            # Get server's allowed command_get actions (using internal caching)
            allowed_actions = self.server_manager.get_server_actions(
                server_id=server_id,
                automatic_only=False
            )
            # Filter for command_get actions only
            allowed_actions = [a for a in allowed_actions if a.get('action_type') == 'command_get']
            
            if not allowed_actions:
                return None
            
            metrics = {
                'server_id': server_id,
                'server_name': server_name,
                'timestamp': _get_now_time(),
                'data': {}
            }
            
            # Execute all actions using connection reuse
            action_ids = [a['id'] for a in allowed_actions]
            results = self.action_manager.execute_multiple_actions(
                server_id=server_id,
                action_ids=action_ids,
                params={}
            )
            
            # Process results
            for action in allowed_actions:
                action_name = action['action_name']
                action_id = action['id']
                result = results.get(action_id)
                
                if result:
                    metrics['data'][action_name] = {
                        'output': result.output if result.success else None,
                        'error': result.error if not result.success else None,
                        'execution_time': result.execution_time,
                        'collected_at': _get_now_time()
                    }
                    
                    if not result.success:
                        self.logger.error(f"Failed: {action_name} on {server_name}")
                else:
                    self.logger.error(f"No result for {action_name} on {server_name}")
                    metrics['data'][action_name] = {
                        'error': 'No result returned',
                        'collected_at': _get_now_time()
                    }
            
            return metrics if metrics['data'] else None
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics for {server_name}: {e}")
            return None
    
    async def _crawl_cycle(self):
        """Execute one crawl cycle for all servers."""
        try:
            servers = self.server_manager.get_all_servers(include_actions=False)
            
            if not servers:
                return
            
            # Collect metrics for each server
            collected = 0
            for server in servers:
                metrics = await self._collect_server_metrics(server)
                
                if metrics and metrics['data']:
                    key = _get_metrics_key(server['id'])
                    # Use new native list operations - push to left (head) with limit
                    self.redis.lpush_json_with_limit(
                        key=key,
                        value=metrics,
                        limit=20,
                        ttl=600
                    )
                    collected += 1
            
            self.logger.info(f"Crawl complete: {collected}/{len(servers)} servers")
            
        except Exception as e:
            self.logger.error(f"Error in crawl cycle: {e}")
    
    async def _run_loop(self):
        """Main loop that runs crawl cycles."""
        self.logger.info(f"Metrics crawler started ({self.delay_seconds}s interval)")
        
        while self.running:
            try:
                await self._crawl_cycle()
                await asyncio.sleep(self.delay_seconds)
            except Exception as e:
                self.logger.error(f"Crawler loop error: {e}")
                await asyncio.sleep(self.delay_seconds)
    
    def start(self):
        """Start the metrics crawler."""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._run_loop())
    
    def stop(self):
        """Stop the metrics crawler."""
        if self.running:
            self.running = False
            if self.task:
                self.task.cancel()
            self.logger.info("Metrics crawler stopped")


class AIAnalyzer:
    """Consumes server metrics and feeds to OpenAI for analysis."""
    
    def __init__(self, db_client: DatabaseClient, redis_client: RedisClient, 
                 openai_client: OpenAIClient, delay_seconds: int = 300):
        self.db = db_client
        self.redis = redis_client
        self.openai = openai_client
        self.delay_seconds = delay_seconds
        self.server_manager = ServerManager(db_client, redis_client)
        self.action_manager = ActionManager(db_client, redis_client)
        self.logger = logger
        self.running = False
        self.task = None
        self.max_metrics_per_analysis = 5
    
    def _get_historical_analysis(self, server_id: int, limit: int = 2) -> List[Dict[str, Any]]:
        """Get last N AI analysis results for historical context."""
        try:
            historical = self.db.execute_query(
                """
                SELECT reasoning, confidence, risk_level, recommended_actions, analyzed_at
                FROM ai_analysis
                WHERE server_id = %s
                ORDER BY analyzed_at DESC
                LIMIT %s
                """,
                (server_id, limit)
            )
            
            results = []
            for row in historical or []:
                try:
                    recommended_actions = json.loads(row['recommended_actions']) if isinstance(row['recommended_actions'], str) else row['recommended_actions']
                    results.append({
                        'timestamp': row['analyzed_at'].isoformat() if row.get('analyzed_at') else 'Unknown',
                        'reasoning': row.get('reasoning', ''),
                        'confidence': float(row.get('confidence', 0)),
                        'risk_level': row.get('risk_level', 'unknown'),
                        'recommended_actions': recommended_actions[0].pop('reasoning') if isinstance(recommended_actions, list) and recommended_actions else []
                    })
                except Exception as e:
                    self.logger.warning(f"Error parsing historical analysis: {e}")
            return results
        except Exception as e:
            self.logger.error(f"Error getting historical analysis: {e}")
            return []
    
    def _get_server_context(self, server_id: int) -> Dict[str, Any]:
        """Get all context data for a server (metrics, logs, stats)."""
        # Get metrics from Redis using new native list operations
        key = _get_metrics_key(server_id)
        # Get first N items from the list (most recent, since we lpush)
        recent_metrics = self.redis.get_list_items(
            key=key,
            count=self.max_metrics_per_analysis,
            pop=False,
            direction='left'
        ) or []
        
        # Get historical analysis
        historical_analysis = self._get_historical_analysis(server_id)
        
        # Get execution logs
        execution_logs = self.db.execute_query(
            """
            SELECT el.*, a.action_name, a.action_type
            FROM execution_logs el
            LEFT JOIN actions a ON el.action_id = a.id
            WHERE el.server_id = %s
            ORDER BY el.executed_at DESC
            LIMIT 6
            """,
            (server_id,)
        )


        context = {
            'recent_metrics': recent_metrics,
            'historical_analysis': historical_analysis,
            'execution_logs': execution_logs
        }

        logger.debug(f"Fetched context for server_id={server_id}: {context}")
        
        return context
    
    def _log_analysis(self, server_id: int, decision) -> Optional[int]:
        """Log AI analysis to database and return analysis_id."""
        try:
            _, analysis_id = self.db.execute_update(
                """
                INSERT INTO ai_analysis 
                (server_id, reasoning, confidence, risk_level, requires_approval, recommended_actions, model)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    server_id,
                    decision.reasoning,
                    decision.confidence,
                    decision.risk_level,
                    decision.requires_approval,
                    json.dumps(decision.recommended_actions),
                    decision.model
                )
            )
            return analysis_id
        except Exception as e:
            self.logger.error(f"Error logging AI analysis: {e}")
            return None
    
    def _log_execution(self, server_id: int, action_id: int, result, analysis_id: Optional[int] = None):
        """Log action execution to database."""
        try:
            self.db.execute_update(
                """
                INSERT INTO execution_logs 
                (server_id, action_id, analysis_id, execution_result, status, error_message, execution_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    server_id,
                    action_id,
                    analysis_id,
                    result.output if result else None,
                    'success' if (result and result.success) else 'failed',
                    result.error if (result and not result.success) else None,
                    result.execution_time if result else None
                )
            )
        except Exception as e:
            self.logger.error(f"Error logging execution: {e}")
    
    async def _analyze_server(self, server_id: int):
        """Analyze metrics for a single server."""
        try:
            # Get server info (using internal caching)
            server = self.server_manager.get_server(server_id, include_actions=True)
            if not server:
                logger.warning(f"Server ID {server_id} not found, skipping analysis")
                return
            
            logger.info(f"Starting AI analysis for server {server['name']}")
            context = self._get_server_context(server_id)
            if not context['recent_metrics']:
                logger.warning(f"No recent metrics for server {server['name']}, skipping analysis")
                return
            
            # Get assigned actions and remove it from server dict           
            assigned_actions = server.pop('allowed_actions', [])
            if not assigned_actions:
                logger.warning(f"No assigned actions for server {server['name']}")
            
            # Get ALL available command_get actions
            all_get_actions = self.action_manager.get_all_actions(
                action_type='command_get',
                active_only=True
            )
            
            # Get assigned command_execute actions
            execute_actions = [a for a in assigned_actions if a.get('action_type') == 'command_execute']
            
            # Combine: ALL get actions + assigned execute actions
            available_actions_for_ai = all_get_actions + execute_actions
            
            # Call OpenAI for analysis with enhanced action list
            decision = self.openai.analyze_server_metrics(
                server_info=server,
                available_actions=available_actions_for_ai,
                assigned_action_ids=[a['id'] for a in assigned_actions],
                execution_logs=context['execution_logs'],
                current_metrics={
                    'latest': context['recent_metrics'][0] if context['recent_metrics'] else None,
                    'recent_metrics': context['recent_metrics'][1:] if len(context['recent_metrics']) > 1 else [],
                    'your_historical_analysis': context['historical_analysis']
                }
            )
            
            self.logger.info(
                f"AI analysis: {server['name']} - {len(decision.recommended_actions)} actions, "
                f"confidence: {decision.confidence:.2f}, risk: {decision.risk_level}"
            )
            
            analysis_id = self._log_analysis(server_id, decision)
            
            if not analysis_id:
                self.logger.error(f"Failed to log AI analysis for {server['name']}")
                return
            
            # Separate recommended actions by type
            get_actions = []
            execute_actions_to_run = []
            
            for action_rec in decision.recommended_actions:
                action_id = action_rec.get('action_id')
                action_info = next((a for a in available_actions_for_ai if a['id'] == action_id), None)
                
                if not action_info:
                    self.logger.warning(
                        f"AI recommended action_id={action_id} for {server['name']}, "
                        f"but it's not assigned. Skipping execution."
                    )
                    continue
                
                action_type = action_info.get('action_type')
                
                if action_type == 'command_get':
                    get_actions.append((action_rec, action_info))
                elif action_type == 'command_execute':
                    # Check if low/medium risk and automatic
                    if self.server_manager.is_action_automatic(server_id, action_id):
                        execute_actions_to_run.append((action_rec, action_info))
            
            # Execute all command_get actions in batch (reusing SSH connection)
            additional_metrics = []
            if get_actions:
                self.logger.info(f"Executing {len(get_actions)} GET actions in batch for {server['name']}")
                get_action_ids = [rec[1]['id'] for rec in get_actions]
                
                results = self.action_manager.execute_multiple_actions(
                    server_id=server_id,
                    action_ids=get_action_ids,
                    params={}
                )
                
                # Process results and log
                for action_rec, action_info in get_actions:
                    action_id = action_info['id']
                    action_name = action_info.get('action_name', 'unknown')
                    result = results.get(action_id)
                    
                    if result:
                        # Log execution with reference to analysis
                        self._log_execution(server_id, action_id, result, analysis_id)
                        
                        if result.success:
                            additional_metrics.append({
                                'action_name': action_name,
                                'output': result.output,
                                'execution_time': result.execution_time,
                                'collected_at': _get_now_time(),
                                'triggered_by': 'ai_recommendation'
                            })
            
            # Execute command_execute actions in batch (they may have side effects, but batch for performance)
            if execute_actions_to_run:
                self.logger.info(f"Executing {len(execute_actions_to_run)} EXECUTE actions in batch for {server['name']}")
                execute_action_ids = [rec[1]['id'] for rec in execute_actions_to_run]
                
                # Build params dict for all actions
                execute_params = {}
                for action_rec, action_info in execute_actions_to_run:
                    if action_rec.get('parameters'):
                        execute_params.update(action_rec.get('parameters', {}))
                
                results = self.action_manager.execute_multiple_actions(
                    server_id=server_id,
                    action_ids=execute_action_ids,
                    params=execute_params
                )
                
                # Log all executions
                for action_rec, action_info in execute_actions_to_run:
                    action_id = action_info['id']
                    result = results.get(action_id)
                    if result:
                        self._log_execution(server_id, action_id, result, analysis_id)
            
            # Add AI-requested metrics to Redis
            if additional_metrics:
                key = _get_metrics_key(server_id)
                
                new_metric = {
                    'server_id': server_id,
                    'server_name': server['name'],
                    'timestamp': _get_now_time(),
                    'data': {item['action_name']: item for item in additional_metrics},
                    'source': 'ai_requested'
                }
                
                # Push to head and keep max 100 items
                self.redis.lpush_json_with_limit(
                    key=key,
                    value=new_metric,
                    limit=100,
                    ttl=600
                )
            
            # Remove consumed metrics by popping them from the head
            key = _get_metrics_key(server_id)
            # Pop the items we just analyzed (from left/head)
            self.redis.get_list_items(
                key=key,
                count=self.max_metrics_per_analysis,
                pop=True,
                direction='left'
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing server {server_id}: {e}")
    
    async def _analysis_cycle(self):
        """Execute one analysis cycle for all servers with metrics."""
        try:
            servers = self.server_manager.get_all_servers(include_actions=False)
            if not servers:
                return
            
            analyzed = 0
            for server in servers:
                if self.redis.exists(_get_metrics_key(server['id'])):
                    await self._analyze_server(server['id'])
                    analyzed += 1
            
            self.logger.info(f"Analysis complete: {analyzed}/{len(servers)} servers")
            
        except Exception as e:
            self.logger.error(f"Error in analysis cycle: {e}")
    
    async def _run_loop(self):
        """Main loop that runs analysis cycles."""
        self.logger.info(f"AI analyzer started ({self.delay_seconds}s interval)")
        
        while self.running:
            try:
                await self._analysis_cycle()
                await asyncio.sleep(self.delay_seconds)
            except Exception as e:
                self.logger.error(f"Analyzer loop error: {e}")
                await asyncio.sleep(self.delay_seconds)
    
    def start(self):
        """Start the AI analyzer."""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._run_loop())
    
    def stop(self):
        """Stop the AI analyzer."""
        if self.running:
            self.running = False
            if self.task:
                self.task.cancel()
            self.logger.info("AI analyzer stopped")


class CronManager:
    """Manages all cron schedulers."""
    
    def __init__(self):
        # Load config
        app_config = env_config.Config(group="APP")
        
        self.crawler_delay = int(app_config.get("APP_CRAWLER_DELAY", "30"))
        self.analyzer_delay = int(app_config.get("APP_MODEL_DELAY", "120"))
        
        # Initialize clients
        self.db = DatabaseClient()
        self.redis = RedisClient()
        
        # Initialize OpenAI client
        try:
            self.openai = OpenAIClient()
        except Exception as e:
            logger.warning(f"OpenAI client initialization failed: {e}")
            self.openai = None
        
        # Initialize schedulers
        self.metrics_crawler = MetricsCrawler(self.db, self.redis, self.crawler_delay)
        self.ai_analyzer = AIAnalyzer(self.db, self.redis, self.openai, self.analyzer_delay) if self.openai else None
        
        self.logger = logger
    
    def start_all(self):
        """Start all cron schedulers."""
        try:
            self.metrics_crawler.start()
            
            if self.ai_analyzer:
                self.ai_analyzer.start()
            else:
                self.logger.warning("AI analyzer not started - OpenAI client unavailable")
            
            self.logger.info("All cron schedulers started")
            
        except Exception as e:
            self.logger.error(f"Error starting cron schedulers: {e}")
    
    def stop_all(self):
        """Stop all cron schedulers."""
        try:
            self.metrics_crawler.stop()
            
            if self.ai_analyzer:
                self.ai_analyzer.stop()
            
            self.logger.info("All cron schedulers stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping cron schedulers: {e}")
