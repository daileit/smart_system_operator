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
            metrics = {
                'server_id': server_id,
                'server_name': server_name,
                'timestamp': datetime.now().isoformat(),
                'data': {}
            }
            
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
                self.logger.warning(f"No get metrics actions configured for server {server_name} (ID: {server_id})")
                return None
            
            # Collect basic metrics (CPU & RAM only)
            for action in allowed_actions:
                action_name = action['action_name']
                action_id = action['action_id']
                
                try:
                    # Execute action (no parameters needed for CPU/RAM)
                    result = self.action_manager.execute_action(
                        action_id=action_id,
                        server_info=server,
                        params={}
                    )
                    
                    if result.success:
                        metrics['data'][action_name] = {
                            'output': result.output,
                            'execution_time': result.execution_time,
                            'collected_at': datetime.now().isoformat()
                        }
                        self.logger.debug(f"Collected {action_name} for {server_name}")
                    else:
                        self.logger.warning(f"Failed to collect {action_name} for {server_name}: {result.error}")
                        metrics['data'][action_name] = {
                            'error': result.error,
                            'collected_at': datetime.now().isoformat()
                        }
                
                except Exception as e:
                    self.logger.error(f"Error collecting {action_name} for {server_name}: {e}")
                    metrics['data'][action_name] = {
                        'error': str(e),
                        'collected_at': datetime.now().isoformat()
                    }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics for server {server_name} (ID: {server_id}): {e}")
            return None
    
    async def _crawl_cycle(self):
        """Execute one crawl cycle for all servers."""
        try:
            # Get all active servers
            servers = self.server_manager.get_all_servers(include_actions=False)
            
            if not servers:
                self.logger.info("No servers configured for monitoring")
                return
            
            self.logger.info(f"Starting metrics crawl for {len(servers)} servers")
            
            # Collect metrics for each server
            for server in servers:
                server_id = server['id']
                
                # Collect metrics
                metrics = await self._collect_server_metrics(server)
                
                if metrics and metrics['data']:
                    # Store in Redis as queue (list)
                    key = self._get_metrics_key(server_id)
                    
                    # Append to list with limit (keep last 100 entries)
                    self.redis.append_json_list_with_limit(
                        key=key,
                        value=metrics,
                        limit=100,
                        ttl=86400,  # 24 hours
                        position=0  # Insert at start
                    )
                    
                    self.logger.info(f"Cached metrics for server {server['name']} (ID: {server_id})")
                else:
                    self.logger.warning(f"No metrics collected for server {server['name']} (ID: {server_id})")
            
            self.logger.info(f"Completed metrics crawl for {len(servers)} servers")
            
        except Exception as e:
            self.logger.error(f"Error in crawl cycle: {e}")
    
    async def _run_loop(self):
        """Main loop that runs crawl cycles."""
        self.logger.info(f"Metrics crawler started with {self.delay_seconds}s delay")
        
        while self.running:
            try:
                await self._crawl_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(self.delay_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in crawler loop: {e}")
                await asyncio.sleep(self.delay_seconds)
    
    def start(self):
        """Start the metrics crawler."""
        if self.running:
            self.logger.warning("Metrics crawler already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        self.logger.info("Metrics crawler started")
    
    def stop(self):
        """Stop the metrics crawler."""
        if not self.running:
            return
        
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
                cursor = self.db.execute_update(
                    """
                    INSERT INTO execution_logs 
                    (server_id, action_id, execution_type, ai_reasoning, execution_details, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (server_id, action_id, execution_type, reasoning, 
                     json.dumps(action_data), status),
                    return_lastrowid=True
                )
                return cursor  # Return recommendation ID for executions to reference
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
        parameters = action_rec.get('parameters', {})
        server_id = server['id']
        
        try:
            self.logger.info(f"Executing GET action '{action_name}' for server {server['name']}")
            
            # Execute action
            result = self.action_manager.execute_action(
                action_id=action_id,
                server_info=server,
                params=parameters
            )
            
            # Log execution with reference to recommendation
            self._log_action(server_id, action_id, 'executed', reasoning, action_rec, result, 
                           recommendation_id=recommendation_id)
            
            if result.success:
                self.logger.info(f"GET action '{action_name}' executed successfully for {server['name']}")
                # Return data to be added to next AI analysis
                return {
                    'action_name': action_name,
                    'output': result.output,
                    'execution_time': result.execution_time,
                    'collected_at': datetime.now().isoformat(),
                    'triggered_by': 'ai_recommendation'
                }
            else:
                self.logger.warning(f"GET action '{action_name}' failed for {server['name']}: {result.error}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error executing GET action '{action_name}': {e}")
            return None
    
    async def _process_action(self, server: Dict[str, Any], action_rec: Dict[str, Any], 
                             decision, action_type: str) -> Optional[Dict[str, Any]]:
        """Process a single action (log and optionally execute)."""
        action_id = action_rec.get('action_id')
        action_name = action_rec.get('action_name', 'unknown')
        server_id = server['id']
        
        # Log as recommended and capture recommendation_id
        rec_id = self._log_action(server_id, action_id, 'recommended', decision.reasoning, action_rec)
        
        # Handle command_get actions - always execute regardless of approval
        if action_type == 'command_get':
            return await self._execute_and_store_get_action(server, action_rec, decision.reasoning, rec_id)
        
        # Handle command_execute actions - check approval and automatic flag
        elif action_type == 'command_execute':
            if decision.risk_level != 'high' and not decision.requires_approval:
                is_automatic = self._is_action_automatic(server_id, action_id)
                
                if is_automatic:
                    self.logger.info(f"Auto-executing action '{action_name}' for server {server['name']}")
                    
                    result = self.action_manager.execute_action(
                        action_id=action_id,
                        server_info=server,
                        params=action_rec.get('parameters', {})
                    )
                    
                    # Log execution with reference to recommendation
                    self._log_action(server_id, action_id, 'executed', decision.reasoning, 
                                   action_rec, result, recommendation_id=rec_id)
                    
                    self.logger.info(
                        f"Auto-executed action '{action_name}' for {server['name']}: "
                        f"{'success' if result.success else 'failed'}"
                    )
        
        return None
    
    async def _analyze_server(self, server_id: int):
        """Analyze metrics for a single server."""
        try:
            # Get server info
            server = self.server_manager.get_server(server_id, include_actions=True)
            if not server:
                self.logger.warning(f"Server {server_id} not found")
                return
            
            # Get all context
            context = self._get_server_context(server_id)
            
            if not context['recent_metrics']:
                self.logger.debug(f"No metrics available for server {server['name']} (ID: {server_id})")
                return
            
            self.logger.info(f"Analyzing {len(context['recent_metrics'])} metrics for server {server['name']} (ID: {server_id})")
            
            # Get available actions
            available_actions = server.get('allowed_actions', [])
            if not available_actions:
                self.logger.warning(f"No actions available for server {server['name']} (ID: {server_id})")
                return
            
            # Call OpenAI for analysis
            decision = self.openai.analyze_server_metrics(
                server_info=server,
                available_actions=available_actions,
                execution_logs=context['execution_logs'],
                server_statistics=context['server_stats'],
                current_metrics={
                    'latest': context['recent_metrics'][0] if context['recent_metrics'] else None,
                    'recent_history': context['recent_metrics'][1:] if len(context['recent_metrics']) > 1 else [],
                    'ai_history': context['historical_analysis']
                }
            )
            
            self.logger.info(
                f"AI analysis completed for {server['name']}: "
                f"{len(decision.recommended_actions)} actions recommended, "
                f"confidence: {decision.confidence:.2f}, risk: {decision.risk_level}"
            )
            
            # Process each recommended action
            additional_metrics = []
            for action_rec in decision.recommended_actions:
                action_id = action_rec.get('action_id')
                
                # Get action type from available actions
                action_info = next((a for a in available_actions if a['id'] == action_id), None)
                if not action_info:
                    self.logger.warning(f"Action {action_id} not found in available actions")
                    continue
                
                action_type = action_info.get('action_type')
                
                # Process action and collect any additional metrics from GET commands
                get_data = await self._process_action(server, action_rec, decision, action_type)
                if get_data:
                    additional_metrics.append(get_data)
            
            # If we executed GET commands, add their results to Redis for next analysis
            if additional_metrics:
                key = self._get_metrics_key(server_id)
                current_metrics = self.redis.get_json_list(key) or []
                
                # Create a new metrics entry with AI-requested data
                new_metric = {
                    'server_id': server_id,
                    'server_name': server['name'],
                    'timestamp': datetime.now().isoformat(),
                    'data': {item['action_name']: item for item in additional_metrics},
                    'source': 'ai_requested'
                }
                
                # Prepend to metrics list
                current_metrics.insert(0, new_metric)
                
                # Keep only last 100
                if len(current_metrics) > 100:
                    current_metrics = current_metrics[:100]
                
                self.redis.set_json_list(key, current_metrics)
                self.logger.info(f"Added {len(additional_metrics)} AI-requested metrics to Redis for {server['name']}")
            
            # Remove consumed metrics from queue (keep AI-requested ones)
            key = self._get_metrics_key(server_id)
            metrics_list = self.redis.get_json_list(key) or []
            remaining_metrics = metrics_list[self.max_metrics_per_analysis:]
            
            if remaining_metrics:
                self.redis.set_json_list(key, remaining_metrics)
            else:
                self.redis.delete_key(key)
            
        except Exception as e:
            self.logger.error(f"Error analyzing server {server_id}: {e}")
    
    async def _analysis_cycle(self):
        """Execute one analysis cycle for all servers with metrics."""
        try:
            # Get all active servers
            servers = self.server_manager.get_all_servers(include_actions=False)
            
            if not servers:
                self.logger.info("No servers configured for analysis")
                return
            
            self.logger.info(f"Starting AI analysis cycle for {len(servers)} servers")
            
            # Analyze each server
            analyzed_count = 0
            for server in servers:
                server_id = server['id']
                
                # Check if server has metrics to analyze
                key = self._get_metrics_key(server_id)
                if self.redis.exists(key):
                    await self._analyze_server(server_id)
                    analyzed_count += 1
            
            self.logger.info(f"Completed AI analysis cycle: {analyzed_count}/{len(servers)} servers analyzed")
            
        except Exception as e:
            self.logger.error(f"Error in analysis cycle: {e}")
    
    async def _run_loop(self):
        """Main loop that runs analysis cycles."""
        self.logger.info(f"AI analyzer started with {self.delay_seconds}s delay")
        
        while self.running:
            try:
                await self._analysis_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(self.delay_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in analyzer loop: {e}")
                await asyncio.sleep(self.delay_seconds)
    
    def start(self):
        """Start the AI analyzer."""
        if self.running:
            self.logger.warning("AI analyzer already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        self.logger.info("AI analyzer started")
    
    def stop(self):
        """Stop the AI analyzer."""
        if not self.running:
            return
        
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
