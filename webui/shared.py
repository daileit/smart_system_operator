"""
Shared resources for WebUI pages.
Contains common variables, session management, and utility functions.
"""

import config as env_config
import init as app_init

# Configuration
app_config = env_config.Config(group="APP")

# Application constants
APP_TITLE = "Smart System Operator"
APP_LOGO_PATH = '/assets/img/application-logo.png'

# Session management (shared across all pages)
user_session = {}

# Database client
db_client = app_init.check_database_connection()

# System status
system_status = {
    "is_database_connected": False if db_client is None else True,
    "is_alive": False if db_client is None else True,
    "first_run": app_init.check_database_setup(db_client) == False
}
