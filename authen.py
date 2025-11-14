import jsonlog
import database as db
import config as env_config
import bcrypt
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

logger = jsonlog.setup_logger("authen")

@dataclass
class AuthUser:
    """Authenticated user information with roles and permissions."""
    user_id: int
    username: str
    email: str
    full_name: str
    status: int
    roles: List[Dict[str, Any]]
    permissions: Dict[str, bool]
    
    def has_permission(self, page_id: str) -> bool:
        """Check if user has access to a specific page."""
        return self.permissions.get(page_id, False)
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(role['role_name'] == role_name for role in self.roles)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AuthUser to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'status': self.status,
            'roles': self.roles,
            'permissions': self.permissions
        }

def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def authenticate_user(username: str, password: str, mysql_client: db.MySQLClient) -> Optional[AuthUser]:
    """
    Authenticate a user by username and password.
    Returns AuthUser object with roles and permissions if successful, None otherwise.
    """
    try:
        # Get user information
        user_query = """
            SELECT user_id, username, email, password_hash, full_name, status 
            FROM users 
            WHERE username = %s AND status = 1
        """
        user_result = mysql_client.fetch_one(user_query, (username,))
        
        if not user_result:
            logger.warning(f"Authentication failed: User '{username}' not found or inactive.")
            return None
        
        # Verify password
        stored_hash = user_result['password_hash']
        if not verify_password(password, stored_hash):
            logger.warning(f"Authentication failed: Incorrect password for user '{username}'.")
            return None
        
        user_id = user_result['user_id']
        
        # Get user roles
        roles_query = """
            SELECT r.role_id, r.role_name, r.description
            FROM roles r
            INNER JOIN user_roles ur ON r.role_id = ur.role_id
            WHERE ur.user_id = %s
        """
        roles = mysql_client.execute_query(roles_query, (user_id,))
        
        # Get user permissions (aggregated from all roles)
        permissions_query = """
            SELECT DISTINCT rp.page_id, MAX(rp.can_access) as can_access
            FROM role_permissions rp
            INNER JOIN user_roles ur ON rp.role_id = ur.role_id
            WHERE ur.user_id = %s
            GROUP BY rp.page_id
        """
        permissions_result = mysql_client.execute_query(permissions_query, (user_id,))
        
        # Convert permissions to dictionary
        permissions = {perm['page_id']: bool(perm['can_access']) for perm in permissions_result}
        
        # Create AuthUser object
        auth_user = AuthUser(
            user_id=user_result['user_id'],
            username=user_result['username'],
            email=user_result['email'],
            full_name=user_result['full_name'],
            status=user_result['status'],
            roles=roles,
            permissions=permissions
        )
        
        logger.info(f"User '{username}' authenticated successfully with {len(roles)} role(s).")
        return auth_user
        
    except Exception as e:
        logger.error(f"Authentication error for user '{username}': {e}")
        return None