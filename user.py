import jsonlog
import database as db
import config as env_config
import bcrypt
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

logger = jsonlog.setup_logger("user")

@dataclass
class User:
    """User data model."""
    user_id: Optional[int] = None
    username: str = ""
    email: str = ""
    password_hash: str = ""
    full_name: Optional[str] = None
    status: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    roles: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert User to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'roles': self.roles or []
        }

class UserManager:
    """User management with CRUD operations."""
    
    def __init__(self, mysql_client: db.MySQLClient):
        self.db = mysql_client
        self.logger = logger
    
    def create_user(self, username: str, email: str, password: str, full_name: Optional[str] = None, 
                   status: int = 1, role_ids: Optional[List[int]] = None) -> Optional[int]:
        """
        Create a new user.
        
        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password (will be hashed)
            full_name: User's full name
            status: User status (0: inactive, 1: active)
            role_ids: List of role IDs to assign to the user
            
        Returns:
            User ID if successful, None otherwise
        """
        try:
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Insert user
            query = """
                INSERT INTO users (username, email, password_hash, full_name, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            affected_rows, user_id = self.db.execute_update(
                query, (username, email, password_hash, full_name, status)
            )
            
            if affected_rows > 0 and user_id:
                self.logger.info(f"User created successfully: {username} (ID: {user_id})")
                
                # Assign roles if provided
                if role_ids:
                    self.assign_roles(user_id, role_ids)
                
                return user_id
            else:
                self.logger.error(f"Failed to create user: {username}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating user {username}: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID with roles.
        
        Args:
            user_id: User ID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            query = """
                SELECT user_id, username, email, password_hash, full_name, status, created_at, updated_at
                FROM users
                WHERE user_id = %s
            """
            result = self.db.fetch_one(query, (user_id,))
            
            if not result:
                return None
            
            # Get user roles
            roles = self._get_user_roles(user_id)
            
            user = User(
                user_id=result['user_id'],
                username=result['username'],
                email=result['email'],
                password_hash=result['password_hash'],
                full_name=result['full_name'],
                status=result['status'],
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                roles=roles
            )
            
            return user
            
        except Exception as e:
            self.logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username with roles.
        
        Args:
            username: Username
            
        Returns:
            User object if found, None otherwise
        """
        try:
            query = """
                SELECT user_id, username, email, password_hash, full_name, status, created_at, updated_at
                FROM users
                WHERE username = %s
            """
            result = self.db.fetch_one(query, (username,))
            
            if not result:
                return None
            
            # Get user roles
            roles = self._get_user_roles(result['user_id'])
            
            user = User(
                user_id=result['user_id'],
                username=result['username'],
                email=result['email'],
                password_hash=result['password_hash'],
                full_name=result['full_name'],
                status=result['status'],
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                roles=roles
            )
            
            return user
            
        except Exception as e:
            self.logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    def get_all_users(self, status: Optional[int] = None, limit: int = 100, offset: int = 0) -> List[User]:
        """
        Get all users with optional filtering.
        
        Args:
            status: Filter by status (None for all)
            limit: Maximum number of users to return
            offset: Offset for pagination
            
        Returns:
            List of User objects
        """
        try:
            if status is not None:
                query = """
                    SELECT user_id, username, email, password_hash, full_name, status, created_at, updated_at
                    FROM users
                    WHERE status = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                results = self.db.execute_query(query, (status, limit, offset))
            else:
                query = """
                    SELECT user_id, username, email, password_hash, full_name, status, created_at, updated_at
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                results = self.db.execute_query(query, (limit, offset))
            
            users = []
            for result in results:
                roles = self._get_user_roles(result['user_id'])
                user = User(
                    user_id=result['user_id'],
                    username=result['username'],
                    email=result['email'],
                    password_hash=result['password_hash'],
                    full_name=result['full_name'],
                    status=result['status'],
                    created_at=result['created_at'],
                    updated_at=result['updated_at'],
                    roles=roles
                )
                users.append(user)
            
            return users
            
        except Exception as e:
            self.logger.error(f"Error getting all users: {e}")
            return []
    
    def update_user(self, user_id: int, username: Optional[str] = None, email: Optional[str] = None,
                   full_name: Optional[str] = None, status: Optional[int] = None) -> bool:
        """
        Update user information.
        
        Args:
            user_id: User ID
            username: New username (optional)
            email: New email (optional)
            full_name: New full name (optional)
            status: New status (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if this is the sysadmin user - if so, prevent certain updates
            current_user = self.get_user_by_id(user_id)
            if current_user and current_user.username == 'sysadmin':
                # Only allow updating full_name for sysadmin
                if username is not None or email is not None or status is not None:
                    self.logger.warning(f"Attempted to modify protected fields for sysadmin user")
                    # Still allow full_name update
                    if full_name is not None:
                        query = "UPDATE users SET full_name = %s WHERE user_id = %s"
                        affected_rows, _ = self.db.execute_update(query, (full_name, user_id))
                        if affected_rows > 0:
                            self.logger.info(f"Sysadmin full_name updated successfully")
                            return True
                    return False
            
            updates = []
            params = []
            
            if username is not None:
                updates.append("username = %s")
                params.append(username)
            if email is not None:
                updates.append("email = %s")
                params.append(email)
            if full_name is not None:
                updates.append("full_name = %s")
                params.append(full_name)
            if status is not None:
                updates.append("status = %s")
                params.append(status)
          
            if not updates:
                self.logger.warning(f"No updates provided for user {user_id}")
                return False
            
            updates.append("updated_at = NOW()")
            
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s"
            params.append(user_id)
            
            affected_rows, _ = self.db.execute_update(query, tuple(params))
            
            if affected_rows > 0:
                self.logger.info(f"User {user_id} updated successfully")
                return True
            else:
                self.logger.warning(f"No user found to update with ID {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """
        Update user password.
        
        Args:
            user_id: User ID
            new_password: New plain text password (will be hashed)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            query = "UPDATE users SET password_hash = %s WHERE user_id = %s"
            affected_rows, _ = self.db.execute_update(query, (password_hash, user_id))
            
            if affected_rows > 0:
                self.logger.info(f"Password updated for user {user_id}")
                return True
            else:
                self.logger.warning(f"No user found to update password with ID {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating password for user {user_id}: {e}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user (hard delete).
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prevent deletion of sysadmin user
            user = self.get_user_by_id(user_id)
            if user and user.username == 'sysadmin':
                self.logger.warning("Attempted to delete sysadmin user - operation blocked")
                return False
            
            query = "DELETE FROM users WHERE user_id = %s"
            affected_rows, _ = self.db.execute_update(query, (user_id,))
            
            if affected_rows > 0:
                self.logger.info(f"User {user_id} deleted successfully")
                return True
            else:
                self.logger.warning(f"No user found to delete with ID {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting user {user_id}: {e}")
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate a user (soft delete).
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        return self.update_user(user_id, status=0)
    
    def activate_user(self, user_id: int) -> bool:
        """
        Activate a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        return self.update_user(user_id, status=1)
    
    def assign_roles(self, user_id: int, role_ids: List[int]) -> bool:
        """
        Assign roles to a user.
        
        Args:
            user_id: User ID
            role_ids: List of role IDs to assign
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prevent modifying roles for sysadmin user
            user = self.get_user_by_id(user_id)
            if user and user.username == 'sysadmin':
                self.logger.warning("Attempted to modify roles for sysadmin user - operation blocked")
                return False
            
            if not role_ids:
                return True
            
            # Prepare data for bulk insert
            data = [(user_id, role_id) for role_id in role_ids]
            query = "INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (%s, %s)"
            
            affected_rows = self.db.execute_many(query, data)
            self.logger.info(f"Assigned {affected_rows} roles to user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error assigning roles to user {user_id}: {e}")
            return False
    
    def remove_roles(self, user_id: int, role_ids: List[int]) -> bool:
        """
        Remove roles from a user.
        
        Args:
            user_id: User ID
            role_ids: List of role IDs to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prevent modifying roles for sysadmin user
            user = self.get_user_by_id(user_id)
            if user and user.username == 'sysadmin':
                self.logger.warning("Attempted to remove roles from sysadmin user - operation blocked")
                return False
            
            if not role_ids:
                return True
            
            placeholders = ','.join(['%s'] * len(role_ids))
            query = f"DELETE FROM user_roles WHERE user_id = %s AND role_id IN ({placeholders})"
            params = [user_id] + role_ids
            
            affected_rows, _ = self.db.execute_update(query, tuple(params))
            self.logger.info(f"Removed {affected_rows} roles from user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing roles from user {user_id}: {e}")
            return False
    
    def get_user_count(self, status: Optional[int] = None) -> int:
        """
        Get total user count.
        
        Args:
            status: Filter by status (None for all)
            
        Returns:
            Total number of users
        """
        try:
            if status is not None:
                query = "SELECT COUNT(*) FROM users WHERE status = %s"
                count = self.db.fetch_value(query, (status,))
            else:
                query = "SELECT COUNT(*) FROM users"
                count = self.db.fetch_value(query)
            
            return count or 0
            
        except Exception as e:
            self.logger.error(f"Error getting user count: {e}")
            return 0
    
    def get_all_roles(self) -> List[Dict[str, Any]]:
        """
        Get all available roles from database.
        
        Returns:
            List of role dictionaries with role_id, role_name, and description
        """
        try:
            query = """
                SELECT role_id, role_name, description, created_at
                FROM roles
                ORDER BY role_id
            """
            roles = self.db.execute_query(query)
            return roles
            
        except Exception as e:
            self.logger.error(f"Error getting all roles: {e}")
            return []
    
    def _get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get roles for a user (internal helper method).
        
        Args:
            user_id: User ID
            
        Returns:
            List of role dictionaries
        """
        try:
            query = """
                SELECT r.role_id, r.role_name, r.description
                FROM roles r
                INNER JOIN user_roles ur ON r.role_id = ur.role_id
                WHERE ur.user_id = %s
            """
            roles = self.db.execute_query(query, (user_id,))
            return roles
            
        except Exception as e:
            self.logger.error(f"Error getting roles for user {user_id}: {e}")
            return []
    
    def get_user_permissions(self, user_id: int) -> Dict[str, bool]:
        """
        Get aggregated permissions for a user from all their roles.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of page_id to permission (True/False)
        """
        try:
            query = """
                SELECT DISTINCT rp.page_id, MAX(rp.can_access) as can_access
                FROM role_permissions rp
                INNER JOIN user_roles ur ON rp.role_id = ur.role_id
                WHERE ur.user_id = %s
                GROUP BY rp.page_id
            """
            permissions_result = self.db.execute_query(query, (user_id,))
            
            # Convert permissions to dictionary
            permissions = {perm['page_id']: bool(perm['can_access']) for perm in permissions_result}
            return permissions
            
        except Exception as e:
            self.logger.error(f"Error getting permissions for user {user_id}: {e}")
            return {}

