from fastapi import FastAPI
from nicegui import ui
import jsonlog
import uvicorn
import config as env_config

app_config = env_config.Config(group="APP")

logger = jsonlog.setup_logger("app")
app = FastAPI()

# FastAPI routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/data")
async def get_data():
    return {"message": "Hello from API"}

# Session management
user_session = {}
is_first_run = True  # Set to False after initialization

APP_TITLE = "Smart System Operator"
APP_LOGO_PATH = './assets/img/application-logo.png'

def init_data():
    """Initialize application data on first run"""
    global is_first_run
    logger.info("Initializing application data...")
    # Add your initialization logic here
    # e.g., create default admin user, setup database tables, etc.
    is_first_run = False
    logger.info("Application initialization complete")

# NiceGUI interface
@ui.page('/login')
def login_page():
    ui.page_title(APP_TITLE)
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    
    if is_first_run:
        init_data()
        ui.notify('Application initialized successfully', type='positive')
    
    def handle_login():
        username = username_input.value
        password = password_input.value
        
        if not username or not password:
            ui.notify('Please enter both username and password', type='warning')
            return
        
        if username=='admin' and password== app_config.get("APP_INIT_SECRET"):
            user_session['authenticated'] = True
            user_session['username'] = username
            ui.notify(f'Welcome, {username}!', type='positive')
            ui.navigate.to('/')
        else:
            ui.notify('Invalid credentials', type='negative')
    
    with ui.column().classes('absolute-center items-center'):
        with ui.card().classes('w-96 p-8'):
            # Logo and App Info
            with ui.column().classes('w-full items-center mb-6'):
                ui.image(APP_LOGO_PATH).classes('w-24 h-24 mb-3')
                ui.label(APP_TITLE).classes('text-h4 text-center font-bold')
                ui.label(f'Version {app_config.get("APP_VERSION")}').classes('text-caption text-center text-grey-6')
            
            ui.separator().classes('mb-4')
            
            ui.label('Login').classes('text-h5 text-center mb-4')
            
            with ui.column().classes('w-full gap-4'):
                username_input = ui.input('Username', placeholder='Enter your username').classes('w-full').props('outlined')
                password_input = ui.input('Password', placeholder='Enter your password', password=True, password_toggle_button=True).classes('w-full').props('outlined')
                
                with ui.row().classes('w-full gap-2 mt-4'):
                    ui.button('Login', on_click=handle_login).classes('flex-1').props('color=primary')
                    ui.button('Clear', on_click=lambda: (username_input.set_value(''), password_input.set_value(''))).classes('flex-1').props('outline')

@ui.page('/')
def main_page():
    ui.page_title(APP_TITLE)
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    
    if not user_session.get('authenticated'):
        ui.navigate.to('/login')
        return
    
    username = user_session.get('username', 'User')
    
    with ui.column().classes('w-full p-4'):
        with ui.row().classes('w-full justify-between items-center mb-4'):
            ui.label('Web Application').classes('text-h3')
            ui.button('Logout', on_click=lambda: (user_session.clear(), ui.navigate.to('/login'))).props('outline')
        
        ui.label(f'Welcome, {username}!').classes('text-h5 mb-4')
        ui.label(f'Log Level: {app_config.get("APP_LOG_LEVEL")}').classes('text-body1')
        
        with ui.card().classes('mt-4 p-4'):
            ui.label('Quick Actions').classes('text-h6 mb-2')
            with ui.row().classes('gap-2'):
                ui.button('Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('color=primary')
                ui.button('Test Action', on_click=lambda: ui.notify('Action performed successfully!', type='positive'))
    
@ui.page('/dashboard')
def dashboard():
    ui.page_title(APP_TITLE)
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    
    if not user_session.get('authenticated'):
        ui.navigate.to('/login')
        # Simple authentication (replace with actual authentication logic)
        return
    
    username = user_session.get('username', 'User')
    
    with ui.column().classes('w-full p-4'):
        with ui.row().classes('w-full justify-between items-center mb-4'):
            ui.label('Dashboard').classes('text-h3')
            ui.button('Logout', on_click=lambda: (user_session.clear(), ui.navigate.to('/login'))).props('outline')
        
        with ui.card().classes('p-4'):
            ui.label(f'Welcome to the dashboard, {username}!').classes('text-h6')
            
        with ui.row().classes('gap-4 mt-4'):
            ui.button('Back to Home', on_click=lambda: ui.navigate.to('/')).props('outline')

# Mount NiceGUI on FastAPI
ui.run_with(
    app,
    mount_path='/',
    storage_secret= app_config.get("APP_INIT_SECRET")
)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=int(app_config.get("APP_PORT")))