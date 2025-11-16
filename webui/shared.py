"""
Shared resources for WebUI pages.
Contains common variables, session management, and utility functions.
"""

import config as env_config
import init as app_init
from redis_cache import RedisClient
from openai_client import OpenAIClient

# Configuration
app_config = env_config.Config(group="APP")

# Application constants
APP_TITLE = "Smart System Operator"
APP_LOGO_PATH = '/assets/img/application-logo.png'

# Session management (shared across all pages)
user_session = {}

# Database client
db_client = app_init.check_database_connection()

# Redis client (initialized in redis_cache module)
redis_client = RedisClient() if app_init.check_redis_connection() else None

# OpenAI client (initialized in openai_client module)
try:
    openai_client = OpenAIClient() if app_init.check_openai_connection() else None
except:
    openai_client = None

# System status
system_status = {
    "is_database_connected": db_client is not None,
    "is_redis_connected": redis_client is not None,
    "is_openai_connected": openai_client is not None,
    "is_alive": db_client is not None,
    "first_run": app_init.check_database_setup(db_client) == False if db_client else True
}
