"""
WebUI module for Smart System Operator.
Contains all page definitions separated into individual modules.
"""

from .login import login_page
from .main import main_page
from .dashboard import dashboard_page
from .users import users_page

__all__ = [
    'login_page',
    'main_page',
    'dashboard_page',
    'users_page',
]
