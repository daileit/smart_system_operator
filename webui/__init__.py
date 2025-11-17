"""
WebUI module for Smart System Operator.
Contains all page definitions separated into individual modules.
"""

from .login_page import login_page
from .main_page import main_page
from .dashboard_page import dashboard_page
from .users_page import users_page
from .settings_page import settings_page
from .servers_page import servers_page
from .reports_page import reports_page

__all__ = [
    'login_page',
    'main_page',
    'dashboard_page',
    'users_page',
    'settings_page',
    'servers_page',
    'reports_page'
]
