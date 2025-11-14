import jsonlog
import database as db
import config as env_config
import bcrypt
import user as user_module
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
        # Initialize UserManager
        user_manager = user_module.UserManager(mysql_client)
        
        # Get user by username
        user = user_manager.get_user_by_username(username)
        
        if not user:
            logger.warning(f"Authentication failed: User '{username}' not found.")
            return None
        
        # Check if user is active
        if user.status != 1:
            logger.warning(f"Authentication failed: User '{username}' is inactive.")
            return None
        
        # Verify password
        if not verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: Incorrect password for user '{username}'.")
            return None
        
        # Get user permissions using UserManager
        permissions = user_manager.get_user_permissions(user.user_id)
        
        # Create AuthUser object
        auth_user = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name or user.username,
            status=user.status,
            roles=user.roles or [],
            permissions=permissions
        )
        
        logger.info(f"User '{username}' authenticated successfully with {len(user.roles or [])} role(s).")
        return auth_user
        
    except Exception as e:
        logger.error(f"Authentication error for user '{username}': {e}")
        return None