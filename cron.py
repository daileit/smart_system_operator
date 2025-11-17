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


def _get_metrics_key(server_id: int) -> str:
    """Get Redis key for server metrics queue."""
    return f"server_metrics:{server_id}"


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
    
    def _get_server_actions_cached(self, server_id: int) -> List[Dict[str, Any]]:
        """Get server's allowed actions with Redis caching (600s TTL)."""
        cache_key = f"cache:server_actions:{server_id}"
        
        # Try to get from Redis cache
        cached_data = self.redis.get_json(cache_key)
        if cached_data:
            self.logger.debug(f"Server actions cache HIT for server_id={server_id}")
            return cached_data
        
        # Cache miss - fetch from DB
        self.logger.debug(f"Server actions cache MISS for server_id={server_id}")
        actions = self.server_manager.get_server_actions(
            server_id=server_id,
            automatic_only=False
        )
        # Filter for command_get actions only
        actions = [a for a in actions if a.get('action_type') == 'command_get']
        
        # Store in Redis with 600s TTL
        self.redis.set_json(cache_key, actions, ttl=600)
        self.logger.debug(f"Server actions cached for server_id={server_id}: {len(actions)} actions")
        
        return actions
    
    async def _collect_server_metrics(self, server: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Collect get metrics for a single server."""
        server_id = server['id']
        server_name = server['name']
        
        try:
            # Get server's allowed command_get actions with caching
            allowed_actions = self._get_server_actions_cached(server_id)
            
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
                action_id = action['id']
                
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
                    key = _get_metrics_key(server['id'])
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
    
    def _get_all_get_actions_cached(self) -> List[Dict[str, Any]]:
        """Get all command_get actions with Redis caching (600s TTL)."""
        cache_key = "cache:all_get_actions"
        
        # Try to get from Redis cache
        cached_data = self.redis.get_json(cache_key)
        if cached_data:
            self.logger.debug("All actions cache HIT")
            return cached_data
        
        # Cache miss - fetch from DB
        self.logger.debug("All actions cache MISS")
        actions = self.action_manager.get_all_actions(
            action_type='command_get',
            active_only=True
        )
        
        # Store in Redis with 600s TTL
        self.redis.set_json(cache_key, actions, ttl=600)
        self.logger.debug(f"All actions cached: {len(actions)} actions")
        
        return actions
    
    def _get_server_cached(self, server_id: int) -> Optional[Dict[str, Any]]:
        """Get server info with Redis caching (600s TTL)."""
        cache_key = f"cache:server_info:{server_id}"
        
        # Try to get from Redis cache
        cached_data = self.redis.get_json(cache_key)
        if cached_data:
            self.logger.debug(f"Server info cache HIT for server_id={server_id}")
            return cached_data
        
        # Cache miss - fetch from DB
        self.logger.debug(f"Server info cache MISS for server_id={server_id}")
        server_data = self.server_manager.get_server(server_id, include_actions=True)
        
        if server_data:
            # Store in Redis with 600s TTL
            self.redis.set_json(cache_key, server_data, ttl=600)
            self.logger.debug(f"Server info cached for server_id={server_id}")
        
        return server_data
    
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
                        'recommended_actions': recommended_actions or []
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
        key = _get_metrics_key(server_id)
        metrics_list = self.redis.get_json_list(key)
        recent_metrics = metrics_list[:self.max_metrics_per_analysis] if metrics_list else []
        
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
            WHERE server_id = %s
            """,
            (server_id,)
        )
        
        return {
            'recent_metrics': recent_metrics,
            'historical_analysis': historical_analysis,
            'execution_logs': execution_logs,
            'server_stats': server_stats
        }
    
    def _log_analysis(self, server_id: int, decision) -> Optional[int]:
        """Log AI analysis to database and return analysis_id."""
        try:
            affected_rows, analysis_id = self.db.execute_update(
                """
                INSERT INTO ai_analysis 
                (server_id, reasoning, confidence, risk_level, requires_approval, recommended_actions)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    server_id,
                    decision.reasoning,
                    decision.confidence,
                    decision.risk_level,
                    decision.requires_approval,
                    json.dumps(decision.recommended_actions)
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
    
    async def _execute_and_store_get_action(self, server: Dict[str, Any], 
                                           action_rec: Dict[str, Any], 
                                           analysis_id: int) -> Optional[Dict[str, Any]]:
        """Execute a get action and return results for AI context."""
        action_id = action_rec.get('action_id')
        action_name = action_rec.get('action_name', 'unknown')
        
        try:
            result = self.action_manager.execute_action(
                action_id=action_id,
                server_info=server,
                params=action_rec.get('parameters', {})
            )
            
            # Log execution with reference to analysis
            self._log_execution(server['id'], action_id, result, analysis_id)
            
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
                             action_type: str, analysis_id: int) -> Optional[Dict[str, Any]]:
        """Process a single action (execute and log)."""
        action_id = action_rec.get('action_id')
        server_id = server['id']
        
        # Handle command_get actions - always execute
        if action_type == 'command_get':
            return await self._execute_and_store_get_action(server, action_rec, analysis_id)
        
        # Handle command_execute actions - check approval and automatic flag
        elif action_type == 'command_execute':
            # Check if low/medium risk and automatic
            if self.server_manager.is_action_automatic(server_id, action_id):
                result = self.action_manager.execute_action(
                    action_id=action_id,
                    server_info=server,
                    params=action_rec.get('parameters', {})
                )
                
                # Log execution with reference to analysis
                self._log_execution(server_id, action_id, result, analysis_id)
        
        return None
    
    async def _analyze_server(self, server_id: int):
        """Analyze metrics for a single server."""
        try:
            # Use cached server info
            server = self._get_server_cached(server_id)
            if not server:
                return
            
            context = self._get_server_context(server_id)
            if not context['recent_metrics']:
                return
            
            # Get assigned actions (for execution permission check)
            assigned_actions = server.get('allowed_actions', [])
            if not assigned_actions:
                return
            
            # Get ALL available command_get actions with caching
            all_get_actions = self._get_all_get_actions_cached()
            
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
            
            # Log AI analysis (always, even if no actions)
            analysis_id = self._log_analysis(server_id, decision)
            
            if not analysis_id:
                self.logger.error(f"Failed to log AI analysis for {server['name']}")
                return
            
            # Process each recommended action
            additional_metrics = []
            for action_rec in decision.recommended_actions:
                action_id = action_rec.get('action_id')
                
                # Verify action is assigned to this server before executing
                action_info = next((a for a in assigned_actions if a['id'] == action_id), None)
                
                if action_info:
                    get_data = await self._process_action(server, action_rec, action_info.get('action_type'), analysis_id)
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
                key = _get_metrics_key(server_id)
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
            key = _get_metrics_key(server_id)
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
