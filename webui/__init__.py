"""
WebUI module for Smart System Operator.
Contains all page definitions separated into individual modules.
"""

from .login_page import login_page
from .main_page import main_page
from .dashboard_page import dashboard_page
from .users_page import users_page

__all__ = [
    'login',
    'main_page',
    'dashboard_page',
    'users_page',
]
