"""
Cron schedulers for Smart System Operator.
- Metrics Crawler: Collects server metrics via command_get actions
- AI Analyzer: Consumes metrics and feeds to OpenAI for analysis
"""
import asyncio
import time
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
import jsonlog
import config as env_config
from database import DatabaseClient
from redis_cache import RedisClient
from servers import ServerManager
from action import ActionManager
from openai_client import OpenAIClient

logger = jsonlog.setup_logger("cron")


class MetricsCrawler:
    """Crawls server metrics using command_get actions."""
    
    def __init__(self, db_client: DatabaseClient, redis_client: RedisClient, delay_seconds: int = 60):
        self.db = db_client
        self.redis = redis_client
        self.delay_seconds = delay_seconds
        self.server_manager = ServerManager(db_client)
        self.action_manager = ActionManager(db_client)
        self.logger = logger
        self.running = False
        self.task = None
        
        # Default monitoring actions to execute (kept simple for speed)
        self.monitoring_actions = [
            'get_cpu_usage',
            'get_memory_usage'
        ]
    
    def _get_metrics_key(self, server_id: int) -> str:
        """Get Redis key for server metrics queue."""
        return f"server_metrics:{server_id}"
    
    async def _collect_server_metrics(self, server: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Collect get metrics for a single server."""
        server_id = server['id']
        server_name = server['name']
        
        try:
            # Get server's allowed CPU and RAM monitoring actions only
            allowed_actions = self.db.execute_query(
                """
                SELECT a.action_name, a.id as action_id
                FROM actions a
                JOIN server_allowed_actions saa ON a.id = saa.action_id
                WHERE saa.server_id = %s 
                  AND a.action_type = 'command_get' 
                  AND a.is_active = 1
                """,
                (server_id,)
            )
            
            if not allowed_actions:
                return None
            
            metrics = {
                'server_id': server_id,
                'server_name': server_name,
                'timestamp': datetime.now().isoformat(),
                'data': {}
            }
            
            # Collect basic metrics (CPU & RAM only)
            for action in allowed_actions:
                action_name = action['action_name']
                action_id = action['action_id']
                
                try:
                    logger.debug(f"Collecting {action_name} for {server_name}")
                    result = self.action_manager.execute_action(
                        action_id=action_id,
                        server_info=server,
                        params={}
                    )
                    
                    metrics['data'][action_name] = {
                        'output': result.output if result.success else None,
                        'error': result.error if not result.success else None,
                        'execution_time': result.execution_time,
                        'collected_at': datetime.now().isoformat()
                    }
                    
                    if not result.success:
                        self.logger.debug(f"Failed: {action_name} on {server_name}")
                
                except Exception as e:
                    self.logger.error(f"Error collecting {action_name} for {server_name}: {e}")
                    metrics['data'][action_name] = {
                        'error': str(e),
                        'collected_at': datetime.now().isoformat()
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
                    key = self._get_metrics_key(server['id'])
                    self.redis.append_json_list_with_limit(
                        key=key,
                        value=metrics,
                        limit=100,
                        ttl=86400,
                        position=0
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
        self.server_manager = ServerManager(db_client)
        self.action_manager = ActionManager(db_client)
        self.logger = logger
        self.running = False
        self.task = None
        self.max_metrics_per_analysis = 5
    
    def _get_metrics_key(self, server_id: int) -> str:
        """Get Redis key for server metrics queue."""
        return f"server_metrics:{server_id}"
    
    def _get_historical_analysis(self, server_id: int, limit: int = 2) -> List[Dict[str, Any]]:
        """Get last N AI analysis results for historical context."""
        try:
            historical = self.db.execute_query(
                """
                SELECT ai_reasoning, execution_details, status, executed_at
                FROM execution_logs
                WHERE server_id = %s 
                  AND execution_type = 'recommended'
                  AND ai_reasoning IS NOT NULL
                ORDER BY executed_at DESC
                LIMIT %s
                """,
                (server_id, limit)
            )
            
            results = []
            for row in historical or []:
                try:
                    details = json.loads(row['execution_details']) if isinstance(row['execution_details'], str) else row['execution_details']
                    results.append({
                        'timestamp': row['executed_at'].isoformat() if row.get('executed_at') else 'Unknown',
                        'reasoning': row.get('ai_reasoning', ''),
                        'action_name': details.get('action_name', 'Unknown'),
                        'status': row.get('status', 'unknown'),
                        'details': details
                    })
                except Exception as e:
                    self.logger.warning(f"Error parsing historical analysis: {e}")
            return results
        except Exception as e:
            self.logger.error(f"Error getting historical analysis: {e}")
            return []
    
    def _get_server_context(self, server_id: int) -> Dict[str, Any]:
        """Get all context data for a server (metrics, logs, stats)."""
        # Get metrics from Redis
        key = self._get_metrics_key(server_id)
        metrics_list = self.redis.get_json_list(key)
        recent_metrics = metrics_list[:self.max_metrics_per_analysis] if metrics_list else []
        
        # Get historical analysis
        historical_analysis = self._get_historical_analysis(server_id)
        
        # Get execution logs
        execution_logs = self.db.execute_query(
            """
            SELECT action_id, execution_type, status, execution_result, 
                   ai_reasoning, executed_at
            FROM execution_logs
            WHERE server_id = %s
            ORDER BY executed_at DESC
            LIMIT 10
            """,
            (server_id,)
        )
        
        # Get server statistics
        server_stats = self.db.fetch_one(
            """
            SELECT 
                COUNT(*) as total_executions,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_executions,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_executions,
                AVG(execution_time) as avg_execution_time
            FROM execution_logs
            WHERE server_id = %s AND execution_type = 'executed'
            """,
            (server_id,)
        )
        
        return {
            'recent_metrics': recent_metrics,
            'historical_analysis': historical_analysis,
            'execution_logs': execution_logs,
            'server_stats': server_stats
        }
    
    def _log_action(self, server_id: int, action_id: int, execution_type: str,
                   reasoning: str, action_data: Dict[str, Any], 
                   result: Optional[Any] = None, status: str = 'recommended',
                   recommendation_id: Optional[int] = None):
        """Log an action to database."""
        try:
            if execution_type == 'executed':
                # Execution: store result and reference to recommendation
                self.db.execute_update(
                    """
                    INSERT INTO execution_logs 
                    (server_id, action_id, execution_type, recommendation_id,
                     execution_result, status, execution_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        server_id, action_id, execution_type, recommendation_id,
                        result.output if result else None,
                        'success' if (result and result.success) else 'failed',
                        result.execution_time if result else None
                    )
                )
            else:
                # Recommendation: store reasoning and details, return ID
                affected_rows, last_id = self.db.execute_update(
                    """
                    INSERT INTO execution_logs 
                    (server_id, action_id, execution_type, ai_reasoning, execution_details, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (server_id, action_id, execution_type, reasoning, 
                     json.dumps(action_data), status)
                )
                return last_id  # Return recommendation ID for executions to reference
        except Exception as e:
            self.logger.error(f"Error logging action: {e}")
            return None
    
    def _is_action_automatic(self, server_id: int, action_id: int) -> bool:
        """Check if action is configured for automatic execution."""
        try:
            result = self.db.fetch_one(
                "SELECT automatic FROM server_allowed_actions WHERE server_id = %s AND action_id = %s",
                (server_id, action_id)
            )
            return result['automatic'] if result else False
        except Exception as e:
            self.logger.error(f"Error checking automatic flag: {e}")
            return False
    
    async def _execute_and_store_get_action(self, server: Dict[str, Any], 
                                           action_rec: Dict[str, Any], 
                                           reasoning: str,
                                           recommendation_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Execute a get action and return results for AI context."""
        action_id = action_rec.get('action_id')
        action_name = action_rec.get('action_name', 'unknown')
        
        try:
            result = self.action_manager.execute_action(
                action_id=action_id,
                server_info=server,
                params=action_rec.get('parameters', {})
            )
            
            # Log execution with reference to recommendation
            self._log_action(server['id'], action_id, 'executed', reasoning, action_rec, result, 
                           recommendation_id=recommendation_id)
            
            if result.success:
                return {
                    'action_name': action_name,
                    'output': result.output,
                    'execution_time': result.execution_time,
                    'collected_at': datetime.now().isoformat(),
                    'triggered_by': 'ai_recommendation'
                }
            return None
                
        except Exception as e:
            self.logger.error(f"Error executing GET '{action_name}': {e}")
            return None
    
    async def _process_action(self, server: Dict[str, Any], action_rec: Dict[str, Any], 
                             decision, action_type: str) -> Optional[Dict[str, Any]]:
        """Process a single action (log and optionally execute)."""
        action_id = action_rec.get('action_id')
        server_id = server['id']
        
        # Log as recommended and capture recommendation_id
        rec_id = self._log_action(server_id, action_id, 'recommended', decision.reasoning, action_rec)
        
        # Handle command_get actions - always execute
        if action_type == 'command_get':
            return await self._execute_and_store_get_action(server, action_rec, decision.reasoning, rec_id)
        
        # Handle command_execute actions - check approval and automatic flag
        elif action_type == 'command_execute':
            if decision.risk_level != 'high' and not decision.requires_approval:
                if self._is_action_automatic(server_id, action_id):
                    result = self.action_manager.execute_action(
                        action_id=action_id,
                        server_info=server,
                        params=action_rec.get('parameters', {})
                    )
                    
                    # Log execution with reference to recommendation
                    self._log_action(server_id, action_id, 'executed', decision.reasoning, 
                                   action_rec, result, recommendation_id=rec_id)
        
        return None
    
    async def _analyze_server(self, server_id: int):
        """Analyze metrics for a single server."""
        try:
            server = self.server_manager.get_server(server_id, include_actions=True)
            if not server:
                return
            
            context = self._get_server_context(server_id)
            if not context['recent_metrics']:
                return
            
            # Get assigned actions (for execution permission check)
            assigned_actions = server.get('allowed_actions', [])
            if not assigned_actions:
                return
            
            # Get ALL available command_get actions to enhance AI capability
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
                assigned_action_ids=[a['id'] for a in assigned_actions],  # Pass assigned IDs for validation
                execution_logs=context['execution_logs'],
                server_statistics=context['server_stats'],
                current_metrics={
                    'latest': context['recent_metrics'][0] if context['recent_metrics'] else None,
                    'recent_history': context['recent_metrics'][1:] if len(context['recent_metrics']) > 1 else [],
                    'ai_history': context['historical_analysis']
                }
            )
            
            self.logger.info(
                f"AI analysis: {server['name']} - {len(decision.recommended_actions)} actions, "
                f"confidence: {decision.confidence:.2f}, risk: {decision.risk_level}"
            )
            
            # If no actions but there's analysis, log it as observation
            if not decision.recommended_actions and decision.reasoning:
                self.db.execute_update(
                    """
                    INSERT INTO execution_logs 
                    (server_id, action_id, execution_type, ai_reasoning, execution_details, status)
                    VALUES (%s, NULL, %s, %s, %s, %s)
                    """,
                    (server_id, 'analyzed', decision.reasoning, 
                     json.dumps({
                         'confidence': decision.confidence,
                         'risk_level': decision.risk_level,
                         'requires_approval': decision.requires_approval
                     }), 'success')
                )
                self.logger.info(f"AI analysis logged (no actions needed): {server['name']}")
            
            # Process each recommended action
            additional_metrics = []
            for action_rec in decision.recommended_actions:
                action_id = action_rec.get('action_id')
                
                # Verify action is assigned to this server before executing
                action_info = next((a for a in assigned_actions if a['id'] == action_id), None)
                
                if action_info:
                    get_data = await self._process_action(server, action_rec, decision, action_info.get('action_type'))
                    if get_data:
                        additional_metrics.append(get_data)
                else:
                    # AI recommended an action not assigned to this server
                    self.logger.warning(
                        f"AI recommended action_id={action_id} for {server['name']}, "
                        f"but it's not assigned. Skipping execution."
                    )
            
            # Add AI-requested metrics to Redis
            if additional_metrics:
                key = self._get_metrics_key(server_id)
                current_metrics = self.redis.get_json_list(key) or []
                
                new_metric = {
                    'server_id': server_id,
                    'server_name': server['name'],
                    'timestamp': datetime.now().isoformat(),
                    'data': {item['action_name']: item for item in additional_metrics},
                    'source': 'ai_requested'
                }
                
                current_metrics.insert(0, new_metric)
                if len(current_metrics) > 100:
                    current_metrics = current_metrics[:100]
                
                self.redis.set_json_list(key, current_metrics)
            
            # Remove consumed metrics
            key = self._get_metrics_key(server_id)
            remaining = (self.redis.get_json_list(key) or [])[self.max_metrics_per_analysis:]
            
            if remaining:
                self.redis.set_json_list(key, remaining)
            else:
                self.redis.delete_key(key)
            
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
                if self.redis.exists(self._get_metrics_key(server['id'])):
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
        openai_config = env_config.Config(group="OPENAI")
        
        self.crawler_delay = int(app_config.get("APP_CRAWLER_DELAY", "60"))
        self.analyzer_delay = int(app_config.get("APP_MODEL_DELAY", "300"))
        
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
