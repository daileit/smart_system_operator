"""
Server management module for Smart System Operator.
Handles CRUD operations for servers and their allowed actions.
"""

import jsonlog
import database as db
from typing import Optional, Dict, List, Any

logger = jsonlog.setup_logger("servers")


class ServerManager:
    """Server management with CRUD operations."""
    
    def __init__(self, db_client: db.DatabaseClient):
        self.db = db_client
        self.logger = logger
    
    def create_server(self, name: str, ip_address: str, username: str, ssh_private_key: str,
                     port: int = 22, description: Optional[str] = None, 
                     created_by: Optional[int] = None,
                     action_ids: Optional[List[int]] = None) -> Optional[int]:
        """
        Create a new server.
        
        Args:
            name: Server name
            ip_address: Server IP address
            username: SSH username
            ssh_private_key: SSH private key content (PEM format)
            port: SSH port (default: 22)
            description: Server description
            created_by: User ID who created the server
            action_ids: List of action IDs to allow for this server
            
        Returns:
            Server ID if successful, None otherwise
        """
        try:
            # Check if server already exists (same IP and port)
            existing = self.db.fetch_one(
                "SELECT id FROM servers WHERE ip_address = %s AND port = %s",
                (ip_address, port)
            )
            if existing:
                self.logger.warning(f"Server with IP {ip_address}:{port} already exists")
                return None
            
            # Insert server
            query = """
                INSERT INTO servers (name, ip_address, port, username, ssh_private_key, 
                                   description, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            server_id = self.db.execute_update(
                query, 
                (name, ip_address, port, username, ssh_private_key, description, created_by)
            )
            
            if server_id and action_ids:
                # Attach allowed actions
                self.attach_actions(server_id, action_ids)
            
            self.logger.info(f"Created server: {name} ({ip_address}:{port}) with ID {server_id}")
            return server_id
            
        except Exception as e:
            self.logger.error(f"Error creating server: {e}")
            return None
    
    def get_server(self, server_id: int, include_actions: bool = False) -> Optional[Dict[str, Any]]:
        try:
            server = self.db.fetch_one(
                """
                SELECT s.name, s.ip_address, s.description, s.created_by, s.created_at,
                FROM servers s
                WHERE s.id = %s
                """,
                (server_id,)
            )
            
            if not server:
                return None
            
            if include_actions:
                server['allowed_actions'] = self.get_server_actions(server_id)
            
            return server
            
        except Exception as e:
            self.logger.error(f"Error getting server {server_id}: {e}")
            return None
    
    def get_all_servers(self, include_actions: bool = False) -> List[Dict[str, Any]]:
        """
        Get all servers.
        
        Args:
            include_actions: Whether to include allowed actions for each server
            
        Returns:
            List of server dictionaries
        """
        try:
            servers = self.db.execute_query(
                """
                SELECT s.*, u.username as creator_username
                FROM servers s
                LEFT JOIN users u ON s.created_by = u.user_id
                ORDER BY s.created_at DESC
                """
            )
            
            if include_actions:
                for server in servers:
                    server['allowed_actions'] = self.get_server_actions(server['id'])
            
            return servers
            
        except Exception as e:
            self.logger.error(f"Error getting all servers: {e}")
            return []
    
    def update_server(self, server_id: int, name: Optional[str] = None, 
                     ip_address: Optional[str] = None, port: Optional[int] = None,
                     username: Optional[str] = None, ssh_private_key: Optional[str] = None,
                     description: Optional[str] = None) -> bool:
        """
        Update server information.
        
        Args:
            server_id: Server ID
            name: New server name
            ip_address: New IP address
            port: New SSH port
            username: New SSH username
            ssh_private_key: New SSH private key content
            description: New description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build dynamic update query
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = %s")
                params.append(name)
            if ip_address is not None:
                updates.append("ip_address = %s")
                params.append(ip_address)
            if port is not None:
                updates.append("port = %s")
                params.append(port)
            if username is not None:
                updates.append("username = %s")
                params.append(username)
            if ssh_private_key is not None:
                updates.append("ssh_private_key = %s")
                params.append(ssh_private_key)
            if description is not None:
                updates.append("description = %s")
                params.append(description)
            
            if not updates:
                self.logger.warning("No fields to update")
                return False
            
            params.append(server_id)
            query = f"UPDATE servers SET {', '.join(updates)} WHERE id = %s"
            
            rows_affected = self.db.execute_update(query, tuple(params))
            
            if rows_affected:
                self.logger.info(f"Updated server {server_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating server {server_id}: {e}")
            return False
    
    def delete_server(self, server_id: int) -> bool:
        """
        Delete a server and its associated data.
        
        Args:
            server_id: Server ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rows_affected = self.db.execute_update(
                "DELETE FROM servers WHERE id = %s",
                (server_id,)
            )
            
            if rows_affected:
                self.logger.info(f"Deleted server {server_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting server {server_id}: {e}")
            return False
    
    # ===== Server-Action Association =====
    
    def attach_actions(self, server_id: int, 
                      action_ids: Optional[List[int]] = None,
                      actions_config: Optional[List[Dict[str, Any]]] = None,
                      automatic: bool = False) -> bool:
        """
        Attach multiple actions to a server.
        
        Args:
            server_id: Server ID
            action_ids: List of action IDs (all with same automatic flag)
            actions_config: List of dicts with 'action_id' and 'automatic' keys
                           Example: [{'action_id': 1, 'automatic': True}, ...]
            automatic: Default automatic flag when using action_ids
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build values based on input type
            if actions_config:
                values = [(server_id, cfg['action_id'], cfg.get('automatic', False)) 
                         for cfg in actions_config]
                query = """
                    INSERT INTO server_allowed_actions (server_id, action_id, automatic)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE automatic = VALUES(automatic)
                """
            elif action_ids:
                values = [(server_id, action_id, automatic) for action_id in action_ids]
                query = """
                    INSERT IGNORE INTO server_allowed_actions (server_id, action_id, automatic)
                    VALUES (%s, %s, %s)
                """
            else:
                return True
            
            rows_affected = self.db.execute_many(query, values)
            self.logger.info(f"Attached {rows_affected} actions to server {server_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error attaching actions to server {server_id}: {e}")
            return False
    
    def detach_action(self, server_id: int, action_id: int) -> bool:
        """
        Detach an action from a server.
        
        Args:
            server_id: Server ID
            action_id: Action ID to detach
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rows_affected = self.db.execute_update(
                "DELETE FROM server_allowed_actions WHERE server_id = %s AND action_id = %s",
                (server_id, action_id)
            )
            
            if rows_affected:
                self.logger.info(f"Detached action {action_id} from server {server_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error detaching action from server: {e}")
            return False
    
    def detach_all_actions(self, server_id: int) -> bool:
        """
        Detach all actions from a server.
        
        Args:
            server_id: Server ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rows_affected = self.db.execute_update(
                "DELETE FROM server_allowed_actions WHERE server_id = %s",
                (server_id,)
            )
            
            self.logger.info(f"Detached all actions from server {server_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error detaching all actions from server: {e}")
            return False
    
    def get_server_actions(self, server_id: int, 
                          automatic_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all actions allowed for a server.
        
        Args:
            server_id: Server ID
            automatic_only: Only return automatic actions
            
        Returns:
            List of action dictionaries with automatic flag
        """
        try:
            query = """
                SELECT a.*, cc.command_template, cc.timeout_seconds, 
                       saa.automatic, saa.created_at as attached_at
                FROM server_allowed_actions saa
                JOIN actions a ON saa.action_id = a.id
                LEFT JOIN command_configs cc ON a.id = cc.action_id
                WHERE saa.server_id = %s
            """
            
            if automatic_only:
                query += " AND saa.automatic = 1"
            
            query += " ORDER BY a.action_type, a.action_name"
            
            actions = self.db.execute_query(query, (server_id,))
            return actions
            
        except Exception as e:
            self.logger.error(f"Error getting server actions: {e}")
            return []
    
    def set_action_automatic(self, server_id: int, action_id: int, 
                           automatic: bool) -> bool:
        """
        Set whether an action should auto-execute or be advisory only.
        
        Args:
            server_id: Server ID
            action_id: Action ID
            automatic: True for auto-execute, False for advisory only
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rows_affected = self.db.execute_update(
                """
                UPDATE server_allowed_actions 
                SET automatic = %s 
                WHERE server_id = %s AND action_id = %s
                """,
                (automatic, server_id, action_id)
            )
            
            if rows_affected:
                mode = "automatic" if automatic else "advisory"
                self.logger.info(f"Set action {action_id} to {mode} mode for server {server_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error setting action automatic flag: {e}")
            return False
    
    def get_servers_with_action(self, action_id: int, 
                               automatic_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all servers that have a specific action allowed.
        
        Args:
            action_id: Action ID
            automatic_only: Only return servers with automatic mode enabled
            
        Returns:
            List of server dictionaries with automatic flag
        """
        try:
            query = """
                SELECT s.*, saa.automatic, saa.created_at as attached_at
                FROM server_allowed_actions saa
                JOIN servers s ON saa.server_id = s.id
                WHERE saa.action_id = %s
            """
            
            if automatic_only:
                query += " AND saa.automatic = 1"
            
            query += " ORDER BY s.name"
            
            servers = self.db.execute_query(query, (action_id,))
            return servers
            
        except Exception as e:
            self.logger.error(f"Error getting servers with action: {e}")
            return []
    
    def is_action_automatic(self, server_id: int, action_id: int) -> bool:
        """
        Check if action is configured for automatic execution on a server.
        
        Args:
            server_id: Server ID
            action_id: Action ID
            
        Returns:
            True if automatic, False otherwise
        """
        try:
            result = self.db.fetch_one(
                "SELECT automatic FROM server_allowed_actions WHERE server_id = %s AND action_id = %s",
                (server_id, action_id)
            )
            return result['automatic'] if result else False
        except Exception as e:
            self.logger.error(f"Error checking automatic flag: {e}")
            return False

