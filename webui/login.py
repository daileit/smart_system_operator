"""
Login page for Smart System Operator.
Handles user authentication and first-run initialization.
"""

from nicegui import ui
import jsonlog
import authen
import init as app_init
from .shared import (
    app_config, APP_TITLE, APP_LOGO_PATH, 
    user_session, db_client, system_status
)

logger = jsonlog.setup_logger("login")


def init_data():
    """Initialize application data on first run"""
    global system_status
    if not system_status["is_database_connected"]:
        system_status["is_alive"] = False
        logger.error("Cannot initialize application data: Database is not connected.")
        return
    if system_status["first_run"]:
        logger.info("Initializing application data...")
        try:
            app_init.initialize_database(db_client, init_secret=app_config.get("APP_INIT_SECRET"))    
            system_status["first_run"] = False
            logger.info("Application initialization complete")
            system_status["is_alive"] = True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
    else: 
        system_status["is_alive"] = True


@ui.page('/login')
def login_page():
    """Login page with authentication."""
    ui.page_title(APP_TITLE)
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    
    if system_status["first_run"]:
        init_data()
        ui.notify('Application initialized successfully', type='positive')
    
    def handle_login():
        username = username_input.value
        password = password_input.value
        
        if not username or not password:
            ui.notify('Please enter both username and password', type='warning')
            return
        
        # Authenticate user and get AuthUser object
        auth_user, message = authen.authenticate_user(username, password, db_client)
        
        if auth_user:
            user_session['authenticated'] = True
            user_session['auth_user'] = auth_user.to_dict()
            user_session['username'] = auth_user.username
            ui.notify(f'Welcome, {auth_user.full_name}!', type='positive')
            ui.navigate.to('/')
        else:
            ui.notify(f'Invalid credentials: {message}', type='negative')
    
    with ui.column().classes('absolute-center items-center'):
        with ui.card().classes('w-128 p-8'):
            # Logo and App Info
            with ui.column().classes('w-full items-center mb-6'):
                ui.image(APP_LOGO_PATH).classes('w-24 h-24 mb-3')
                ui.label(APP_TITLE).classes('text-h4 text-center font-bold text-primary')
                ui.label(f'Version {app_config.get("APP_VERSION")}. Released: {app_config.get("APP_DEPLOY_TIME")}').classes('text-caption text-center text-grey-6')
            
            ui.separator().classes('mb-4')
                        
            with ui.column().classes('w-full gap-4'):
                username_input = ui.input('Username', placeholder='Enter your username').classes('w-full').props('outlined')
                password_input = ui.input('Password', placeholder='Enter your password', password=True, password_toggle_button=True).classes('w-full').props('outlined')
                
                with ui.row().classes('w-full gap-2 mt-4'):
                    ui.button('Login', icon='login', on_click=handle_login).classes('flex-1').props('color=primary')
                    ui.button('Clear', icon='clear', on_click=lambda: (username_input.set_value(''), password_input.set_value(''))).classes('flex-1').props('outline')
