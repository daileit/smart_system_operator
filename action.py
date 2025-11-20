"""
Action execution module for Smart System Operator.
Handles action retrieval and execution via SSH (paramiko) and HTTP (requests).
"""

import jsonlog
import database as db
import config as env_config
from redis_cache import RedisClient
import paramiko
import requests
import time
import json
import re
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from string import Template

logger = jsonlog.setup_logger("action")


@dataclass
class Action:
    """Action data model."""
    id: Optional[int] = None
    action_name: str = ""
    action_type: str = ""
    description: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    command_template: Optional[str] = None
    timeout_seconds: Optional[int] = None
    http_method: Optional[str] = None
    http_url: Optional[str] = None
    http_headers: Optional[Dict[str, str]] = None
    http_body: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Action to dictionary."""
        return {
            'id': self.id,
            'action_name': self.action_name,
            'action_type': self.action_type,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'command_template': self.command_template,
            'timeout_seconds': self.timeout_seconds,
            'http_method': self.http_method,
            'http_url': self.http_url,
            'http_headers': self.http_headers,
            'http_body': self.http_body,
            'parameters': self.parameters
        }


@dataclass
class ExecutionResult:
    """Result of an action execution."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    status_code: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ExecutionResult to dictionary."""
        return {
            'success': self.success,
            'output': self.output,
            'error': self.error,
            'execution_time': self.execution_time,
            'status_code': self.status_code
        }


class ActionManager:
    """Action management and execution."""
    
    def __init__(self, db_client: db.DatabaseClient, redis_client: Optional[RedisClient] = None):
        self.db = db_client
        self.redis = redis_client
        self.logger = logger
        
        # Get APP_NAME for cache key prefix
        app_config = env_config.Config(group="APP")
        self.app_name = app_config.get("APP_NAME", "smart_system")
        
        # Cache TTL (5 minutes)
        self.cache_ttl = 300
    
    # ===== Action Retrieval =====
    
    def get_all_actions(self, action_type: Optional[str] = None, 
                       active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all available actions with Redis caching.
        
        Args:
            action_type: Filter by action type ('command_execute', 'command_get', 'http')
            active_only: Only return active actions
            
        Returns:
            List of action dictionaries with configs
        """
        try:
            # Check cache if Redis available
            if self.redis:
                cache_suffix = f"{action_type or 'all'}:{'active' if active_only else 'all'}"
                cache_key = f"{self.app_name}:actions:all_actions:{cache_suffix}"
                cached_data = self.redis.get_json(cache_key)
                if cached_data:
                    self.logger.debug(f"All actions cache HIT for type={action_type}, active_only={active_only}")
                    return cached_data
            
            # Fetch from database
            query = """
                SELECT a.*, 
                       cc.command_template, cc.timeout_seconds as cmd_timeout,
                       hc.http_method, hc.http_url, hc.http_headers, hc.http_body, 
                       hc.parameters, hc.timeout_seconds as http_timeout
                FROM actions a
                LEFT JOIN command_configs cc ON a.id = cc.action_id
                LEFT JOIN http_configs hc ON a.id = hc.action_id
                WHERE 1=1
            """
            params = []
            
            if action_type:
                query += " AND a.action_type = %s"
                params.append(action_type)
            
            if active_only:
                query += " AND a.is_active = 1"
            
            query += " ORDER BY a.action_type, a.action_name"
            
            actions = self.db.execute_query(query, tuple(params) if params else None)
            
            # Merge timeout fields and parse JSON
            for action in actions:
                action['timeout_seconds'] = action.get('cmd_timeout') or action.get('http_timeout') or 30
                if action.get('http_headers'):
                    try:
                        action['http_headers'] = json.loads(action['http_headers']) if isinstance(action['http_headers'], str) else action['http_headers']
                    except:
                        action['http_headers'] = {}
                if action.get('parameters'):
                    try:
                        action['parameters'] = json.loads(action['parameters']) if isinstance(action['parameters'], str) else action['parameters']
                    except:
                        action['parameters'] = {}
            
            # Cache the result
            if self.redis:
                self.redis.set_json(cache_key, actions, ttl=self.cache_ttl)
                self.logger.debug(f"All actions cached, expires in {self.cache_ttl}s")
            
            return actions
            
        except Exception as e:
            self.logger.error(f"Error getting actions: {e}")
            return []
    
    def get_action(self, action_id: int) -> Optional[Dict[str, Any]]:
        """
        Get action by ID.
        
        Args:
            action_id: Action ID
            
        Returns:
            Action dictionary with config, None if not found
        """
        try:
            action = self.db.fetch_one(
                """
                SELECT a.*, 
                       cc.command_template, cc.timeout_seconds as cmd_timeout,
                       hc.http_method, hc.http_url, hc.http_headers, hc.http_body, 
                       hc.parameters, hc.timeout_seconds as http_timeout
                FROM actions a
                LEFT JOIN command_configs cc ON a.id = cc.action_id
                LEFT JOIN http_configs hc ON a.id = hc.action_id
                WHERE a.id = %s
                """,
                (action_id,)
            )
            
            if action:
                action['timeout_seconds'] = action.get('cmd_timeout') or action.get('http_timeout') or 30
                if action.get('http_headers'):
                    try:
                        action['http_headers'] = json.loads(action['http_headers']) if isinstance(action['http_headers'], str) else action['http_headers']
                    except:
                        action['http_headers'] = {}
                if action.get('parameters'):
                    try:
                        action['parameters'] = json.loads(action['parameters']) if isinstance(action['parameters'], str) else action['parameters']
                    except:
                        action['parameters'] = {}
            
            return action
            
        except Exception as e:
            self.logger.error(f"Error getting action {action_id}: {e}")
            return None
    
    def get_action_by_name(self, action_name: str) -> Optional[Dict[str, Any]]:
        """
        Get action by name.
        
        Args:
            action_name: Action name
            
        Returns:
            Action dictionary with config, None if not found
        """
        try:
            action = self.db.fetch_one(
                """
                SELECT a.*, 
                       cc.command_template, cc.timeout_seconds as cmd_timeout,
                       hc.http_method, hc.http_url, hc.http_headers, hc.http_body, 
                       hc.parameters, hc.timeout_seconds as http_timeout
                FROM actions a
                LEFT JOIN command_configs cc ON a.id = cc.action_id
                LEFT JOIN http_configs hc ON a.id = hc.action_id
                WHERE a.action_name = %s
                """,
                (action_name,)
            )
            
            if action:
                action['timeout_seconds'] = action.get('cmd_timeout') or action.get('http_timeout') or 30
                if action.get('http_headers'):
                    try:
                        action['http_headers'] = json.loads(action['http_headers']) if isinstance(action['http_headers'], str) else action['http_headers']
                    except:
                        action['http_headers'] = {}
                if action.get('parameters'):
                    try:
                        action['parameters'] = json.loads(action['parameters']) if isinstance(action['parameters'], str) else action['parameters']
                    except:
                        action['parameters'] = {}
            
            return action
            
        except Exception as e:
            self.logger.error(f"Error getting action by name {action_name}: {e}")
            return None
     
    @staticmethod
    def _sanitize_output(text: Optional[str], text_type: Optional[str] = None) -> Optional[str]:
        if not text:
            return text            
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        return text.strip()
    
    def _substitute_template(self, template_str: str, params: Optional[Dict[str, str]], 
                            server_info: Optional[Dict[str, Any]] = None) -> str:
        """
        Substitute parameters in a template string.
        
        Args:
            template_str: Template string with $variable placeholders
            params: User-provided parameters
            server_info: Server information (ip_address, name)
            
        Returns:
            Substituted string
        """
        template = Template(template_str)
        substitution_vars = params.copy() if params else {}
        
        if server_info:
            substitution_vars['server_ip'] = server_info.get('ip_address', '')
            substitution_vars['server_name'] = server_info.get('name', '')
        
        return template.safe_substitute(substitution_vars)
    
    # ===== SSH Connection Management =====
    
    def _create_ssh_client(self, host: str, port: int, username: str, 
                          ssh_private_key: str, timeout: int = 30) -> paramiko.SSHClient:
        """
        Create and connect SSH client.
        
        Args:
            host: Server IP address
            port: SSH port
            username: SSH username
            ssh_private_key: SSH private key content (PEM format text)
            timeout: Timeout in seconds
            
        Returns:
            Connected SSH client
            
        Raises:
            paramiko.AuthenticationException: If authentication fails
            paramiko.SSHException: If SSH connection fails
        """
        from io import StringIO
        
        # Create SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Load private key from string
        try:
            key_file = StringIO(ssh_private_key)
            private_key = paramiko.RSAKey.from_private_key(key_file)
        except:
            try:
                key_file = StringIO(ssh_private_key)
                private_key = paramiko.Ed25519Key.from_private_key(key_file)
            except:
                key_file = StringIO(ssh_private_key)
                private_key = paramiko.ECDSAKey.from_private_key(key_file)
        
        # Connect
        ssh_client.connect(
            hostname=host,
            port=port,
            username=username,
            pkey=private_key,
            timeout=timeout,
            banner_timeout=timeout
        )
        
        return ssh_client
    
    def _execute_command_on_client(self, ssh_client: paramiko.SSHClient, 
                                   command: str, timeout: int = 30) -> ExecutionResult:
        """
        Execute a command on an existing SSH client.
        
        Args:
            ssh_client: Connected SSH client
            command: Command to execute
            timeout: Timeout in seconds
            
        Returns:
            ExecutionResult with output or error
        """
        import time
        start_time = time.time()
        
        try:
            # Execute command
            stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
            
            # Get output
            output = stdout.read().decode('utf-8', errors='replace')
            error = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            # Sanitize output - reduce multiple whitespaces
            output = self._sanitize_output(output)
            error = self._sanitize_output(error)
            
            execution_time = time.time() - start_time
            
            if exit_code == 0:
                return ExecutionResult(
                    success=True,
                    output=output,
                    error=error if error else None,
                    execution_time=round(execution_time, 2)
                )
            else:
                return ExecutionResult(
                    success=False,
                    output=output,
                    error=error or f"Command exited with code {exit_code}",
                    execution_time=round(execution_time, 2)
                )
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=round(execution_time, 2)
            )
    
    # ===== SSH Command Execution =====
    
    def execute_ssh_command(self, host: str, port: int, username: str, 
                           ssh_private_key: str, command: str, 
                           timeout: int = 30) -> ExecutionResult:
        """
        Execute a single command via SSH.
        
        Args:
            host: Server IP address
            port: SSH port
            username: SSH username
            ssh_private_key: SSH private key content (PEM format text)
            command: Command to execute
            timeout: Timeout in seconds
            
        Returns:
            ExecutionResult with output or error
        """
        ssh_client = None
        try:
            ssh_client = self._create_ssh_client(host, port, username, ssh_private_key, timeout)
            result = self._execute_command_on_client(ssh_client, command, timeout)
            self.logger.info(f"SSH command executed on {host}:{port}")
            return result
        except (paramiko.AuthenticationException, paramiko.SSHException, Exception) as e:
            error_msg = f"Authentication failed: {e}" if isinstance(e, paramiko.AuthenticationException) else \
                       f"SSH error: {e}" if isinstance(e, paramiko.SSHException) else str(e)
            self.logger.error(f"SSH error for {host}:{port}: {e}")
            return ExecutionResult(success=False, error=error_msg, execution_time=0.0)
        finally:
            if ssh_client:
                ssh_client.close()
    
    def execute_multiple_actions(self, server_id: int, 
                                 action_ids: List[int],
                                 params: Optional[Dict[str, str]] = None) -> Dict[int, ExecutionResult]:
        """
        Execute multiple actions on a server, reusing SSH connection.
        
        Args:
            server_id: Server ID
            action_ids: List of action IDs to execute
            params: Parameters for template substitution
            
        Returns:
            Dictionary mapping action_id to ExecutionResult
        """
        results = {}
        
        if not action_ids:
            return results
        
        try:
            # Get server info
            server_info = self.db.fetch_one(
                "SELECT id, name, ip_address, ssh_port, ssh_username, ssh_private_key FROM servers WHERE id = %s",
                (server_id,)
            )
            
            if not server_info:
                error_result = ExecutionResult(success=False, error=f"Server {server_id} not found")
                return {action_id: error_result for action_id in action_ids}
            
            # Separate actions by type
            command_actions = []
            http_actions = []
            
            for action_id in action_ids:
                action = self.get_action(action_id)
                if not action:
                    results[action_id] = ExecutionResult(success=False, error=f"Action {action_id} not found")
                    continue
                
                if not action.get('is_active'):
                    results[action_id] = ExecutionResult(success=False, error=f"Action {action_id} is not active")
                    continue
                
                action_type = action.get('action_type')
                if action_type in ('command_get', 'command_execute'):
                    command_actions.append(action)
                elif action_type == 'http':
                    http_actions.append(action)
            
            # Execute HTTP actions
            for action in http_actions:
                try:
                    results[action['id']] = self._execute_http_action(action, params, server_info, action.get('timeout_seconds', 10))
                except Exception as e:
                    results[action['id']] = ExecutionResult(success=False, error=str(e))
            
            # Execute command actions with SSH connection reuse
            if command_actions:
                results.update(self._execute_command_actions_batch(server_info, command_actions, params))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in execute_multiple_actions: {e}")
            error_result = ExecutionResult(success=False, error=str(e))
            return {action_id: results.get(action_id, error_result) for action_id in action_ids}
    
    def _execute_command_actions_batch(self, server_info: Dict[str, Any], 
                                      actions: List[Dict[str, Any]], 
                                      params: Optional[Dict[str, str]]) -> Dict[int, ExecutionResult]:
        """Execute multiple command actions using a single SSH connection."""
        results = {}
        ssh_client = None
        
        try:
            ssh_client = self._create_ssh_client(
                host=server_info['ip_address'],
                port=server_info['ssh_port'],
                username=server_info['ssh_username'],
                ssh_private_key=server_info['ssh_private_key'],
                timeout=30
            )
            
            self.logger.info(f"Reusing SSH connection for {len(actions)} actions on server {server_info['id']}")
            
            for action in actions:
                try:
                    command_template = action.get('command_template', '')
                    if not command_template:
                        results[action['id']] = ExecutionResult(success=False, error="Command template is empty")
                        continue
                    
                    # Substitute parameters
                    try:
                        command = self._substitute_template(command_template, params, server_info)
                    except Exception as e:
                        results[action['id']] = ExecutionResult(success=False, error=f"Template substitution failed: {e}")
                        continue
                    
                    # Execute command
                    timeout = action.get('timeout_seconds', 30)
                    results[action['id']] = self._execute_command_on_client(ssh_client, command, timeout)
                    
                except Exception as e:
                    self.logger.error(f"Error executing action {action['id']}: {e}")
                    results[action['id']] = ExecutionResult(success=False, error=str(e))
        
        except (paramiko.AuthenticationException, paramiko.SSHException, Exception) as e:
            error_msg = f"Authentication failed: {e}" if isinstance(e, paramiko.AuthenticationException) else \
                       f"SSH error: {e}" if isinstance(e, paramiko.SSHException) else str(e)
            self.logger.error(f"SSH connection error for server {server_info['id']}: {e}")
            for action in actions:
                if action['id'] not in results:
                    results[action['id']] = ExecutionResult(success=False, error=error_msg)
        finally:
            if ssh_client:
                ssh_client.close()
        
        return results
    
    # ===== HTTP Request Execution =====
    
    def execute_http_request(self, method: str, url: str, 
                            headers: Optional[Dict[str, str]] = None,
                            body: Optional[str] = None,
                            parameters: Optional[Dict[str, Any]] = None,
                            timeout: int = 10) -> ExecutionResult:
        """
        Execute an HTTP request.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            url: Target URL
            headers: HTTP headers
            body: Request body (for POST/PUT/PATCH)
            parameters: URL parameters
            timeout: Timeout in seconds
            
        Returns:
            ExecutionResult with response or error
        """
        import time
        start_time = time.time()
        
        try:
            # Prepare request
            method = method.upper()
            headers = headers or {}
            params = parameters or {}
            
            # Parse body if JSON string
            data = None
            json_data = None
            if body:
                try:
                    json_data = json.loads(body) if isinstance(body, str) else body
                except:
                    data = body
            
            # Execute request
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                data=data,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # Sanitize response text - reduce multiple whitespaces
            response_text = self._sanitize_output(response.text)
            
            # Check response
            if response.ok:
                self.logger.info(f"HTTP {method} request to {url} succeeded with status {response.status_code}")
                return ExecutionResult(
                    success=True,
                    output=response_text,
                    execution_time=round(execution_time, 2),
                    status_code=response.status_code
                )
            else:
                self.logger.warning(f"HTTP {method} request to {url} failed with status {response.status_code}")
                return ExecutionResult(
                    success=False,
                    output=response_text,
                    error=f"HTTP {response.status_code}: {response.reason}",
                    execution_time=round(execution_time, 2),
                    status_code=response.status_code
                )
                
        except requests.exceptions.Timeout as e:
            execution_time = time.time() - start_time
            self.logger.error(f"HTTP request to {url} timed out: {e}")
            return ExecutionResult(
                success=False,
                error=f"Request timeout: {str(e)}",
                execution_time=round(execution_time, 2)
            )
        except requests.exceptions.RequestException as e:
            execution_time = time.time() - start_time
            self.logger.error(f"HTTP request to {url} failed: {e}")
            return ExecutionResult(
                success=False,
                error=f"Request error: {str(e)}",
                execution_time=round(execution_time, 2)
            )
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Error executing HTTP request to {url}: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=round(execution_time, 2)
            )
    
    # ===== Action Execution =====
    
    def execute_action(self, action_id: int, server_id: int,
                      params: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """
        Execute a single action on a server.
        
        Args:
            action_id: Action ID to execute
            server_id: Server ID
            params: Parameters for template substitution
            
        Returns:
            ExecutionResult with execution details
        """
        # Use execute_multiple_actions for consistency and code reuse
        results = self.execute_multiple_actions(server_id, [action_id], params)
        return results.get(action_id, ExecutionResult(success=False, error="No result returned"))
    
    def execute_action_by_name(self, action_name: str, server_id: int,
                              params: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """
        Execute an action by name on a server.
        
        Args:
            action_name: Action name to execute
            server_id: Server ID
            params: Parameters for template substitution
            
        Returns:
            ExecutionResult with execution details
        """
        action = self.get_action_by_name(action_name)
        if not action:
            return ExecutionResult(success=False, error=f"Action '{action_name}' not found")
        
        return self.execute_action(action['id'], server_id, params)
    
    def _execute_http_action(self, action: Dict[str, Any],
                            params: Optional[Dict[str, str]],
                            server_info: Optional[Dict[str, Any]],
                            timeout: int) -> ExecutionResult:
        """Execute an HTTP action."""
        try:
            method = action.get('http_method')
            url = action.get('http_url')
            headers = action.get('http_headers', {})
            body = action.get('http_body')
            parameters = action.get('parameters', {})
            
            if not method or not url:
                return ExecutionResult(success=False, error="Missing HTTP method or URL")
            
            # Substitute parameters in URL and body
            url = self._substitute_template(url, params, server_info)
            if body:
                body = self._substitute_template(body, params, server_info)
            
            # Execute HTTP request
            return self.execute_http_request(method, url, headers, body, parameters, timeout)
            
        except Exception as e:
            return ExecutionResult(success=False, error=f"HTTP execution error: {e}")
