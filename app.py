from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from nicegui import ui
import jsonlog
import uvicorn
import config as env_config
import init as app_init
import authen
import user as user_module

app_config = env_config.Config(group="APP")

logger = jsonlog.setup_logger("app")
app = FastAPI()

# Mount static files
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# FastAPI routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/data")
async def get_data():
    return {"message": "Hello from API"}

# Session management
user_session = {}
db_client = app_init.check_database_connection()

system_status = {
    "is_database_connected": False if db_client is None else True,
    "is_alive": False if db_client is None else True,
    "first_run": app_init.check_database_setup(db_client) == False
}

APP_TITLE = "Smart System Operator"
APP_LOGO_PATH = '/assets/img/application-logo.png'

def init_data():
    global system_status
    """Initialize application data on first run"""
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

# NiceGUI interface
@ui.page('/login')
def login_page():
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
        auth_user = authen.authenticate_user(username, password, db_client)
        
        if auth_user:
            user_session['authenticated'] = True
            user_session['auth_user'] = auth_user.to_dict()
            user_session['username'] = auth_user.username
            ui.notify(f'Welcome, {auth_user.full_name}!', type='positive')
            ui.navigate.to('/')
        else:
            ui.notify('Invalid credentials', type='negative')
    
    with ui.column().classes('absolute-center items-center'):
        with ui.card().classes('w-96 p-8'):
            # Logo and App Info
            with ui.column().classes('w-full items-center mb-6'):
                ui.image(APP_LOGO_PATH).classes('w-24 h-24 mb-3')
                ui.label(APP_TITLE).classes('text-h4 text-center font-bold')
                ui.label(f'Version {app_config.get("APP_VERSION")}. Released: {app_config.get("APP_DEPLOY_TIME")}').classes('text-caption text-center text-grey-6')
            
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
    auth_user = user_session.get('auth_user', {})
    full_name = auth_user.get('full_name', username)
    permissions = auth_user.get('permissions', {})
    roles = auth_user.get('roles', [])
    role_names = ', '.join([role['role_name'] for role in roles])
    
    # Header
    with ui.header().classes('items-center justify-between bg-primary text-white'):
        with ui.row().classes('items-center gap-4'):
            ui.image(APP_LOGO_PATH).classes('w-10 h-10')
            ui.label(APP_TITLE).classes('text-h5 font-bold')
        
        with ui.row().classes('items-center gap-4'):
            with ui.button(icon='account_circle').props('flat round color=white'):
                with ui.menu():
                    ui.menu_item(f'{full_name}', lambda: None).props('disable')
                    ui.separator()
                    ui.menu_item('Profile', lambda: ui.notify('Profile clicked'))
                    ui.menu_item('Settings', lambda: ui.notify('Settings clicked'))
                    ui.separator()
                    ui.menu_item('Logout', lambda: (user_session.clear(), ui.navigate.to('/login')))
    
    # Main layout with drawer
    with ui.left_drawer(fixed=True).classes('bg-grey-1').props('bordered width=250'):
        with ui.column().classes('w-full gap-2 p-4'):
            ui.label('Navigation').classes('text-h6 font-bold text-grey-8 mb-2')
            ui.separator()
            
            # Navigation items based on permissions
            nav_items = [
                {'id': 'dashboard', 'icon': 'dashboard', 'label': 'Dashboard', 'path': '/dashboard'},
                {'id': 'users', 'icon': 'people', 'label': 'Users', 'path': '/users'},
                {'id': 'reports', 'icon': 'assessment', 'label': 'Reports', 'path': '/reports'},
                {'id': 'analytics', 'icon': 'analytics', 'label': 'Analytics', 'path': '/analytics'},
                {'id': 'settings', 'icon': 'settings', 'label': 'Settings', 'path': '/settings'},
            ]
            
            for item in nav_items:
                if permissions.get(item['id'], False):
                    with ui.button(icon=item['icon'], on_click=lambda path=item['path']: ui.navigate.to(path)).props('flat align=left').classes('w-full justify-start'):
                        ui.label(item['label'])
                else:
                    with ui.button(icon=item['icon']).props('flat align=left disable').classes('w-full justify-start opacity-40'):
                        ui.label(item['label'])
            
            ui.separator().classes('my-4')
            
            # User info in drawer
            with ui.card().classes('w-full bg-white'):
                ui.label('User Info').classes('text-caption text-grey-6')
                ui.label(username).classes('text-body2 font-bold')
                ui.label(role_names).classes('text-caption text-primary')
    
    # Main content area
    with ui.column().classes('w-full p-6 gap-4'):
        # Welcome section
        with ui.card().classes('w-full'):
            ui.label(f'Welcome back, {full_name}!').classes('text-h4 font-bold mb-2')
            ui.label(f'Role: {role_names}').classes('text-body1 text-grey-7')
            ui.label(f'System Status: {"Operational" if system_status["is_alive"] else "Offline"}').classes('text-body2')
        
        # Quick stats
        with ui.row().classes('w-full gap-4'):
            with ui.card().classes('flex-1'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('check_circle', color='positive').classes('text-5xl')
                    with ui.column():
                        ui.label('System Status').classes('text-caption text-grey-6')
                        ui.label('Healthy').classes('text-h6 font-bold text-positive')
            
            with ui.card().classes('flex-1'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('security', color='primary').classes('text-5xl')
                    with ui.column():
                        ui.label('Access Level').classes('text-caption text-grey-6')
                        ui.label(role_names).classes('text-h6 font-bold')
            
            with ui.card().classes('flex-1'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('verified_user', color='secondary').classes('text-5xl')
                    with ui.column():
                        ui.label('Permissions').classes('text-caption text-grey-6')
                        ui.label(f'{sum(permissions.values())} Pages').classes('text-h6 font-bold')
        
        # Quick actions
        with ui.card().classes('w-full'):
            ui.label('Quick Actions').classes('text-h6 font-bold mb-4')
            with ui.row().classes('gap-3 flex-wrap'):
                if permissions.get('dashboard', False):
                    with ui.button('Dashboard', icon='dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('color=primary'):
                        pass
                if permissions.get('users', False):
                    with ui.button('Manage Users', icon='people', on_click=lambda: ui.navigate.to('/users')).props('color=secondary'):
                        pass
                if permissions.get('reports', False):
                    with ui.button('View Reports', icon='assessment', on_click=lambda: ui.navigate.to('/reports')).props('outline color=primary'):
                        pass
                if permissions.get('analytics', False):
                    with ui.button('Analytics', icon='analytics', on_click=lambda: ui.navigate.to('/analytics')).props('outline color=secondary'):
                        pass
        
        # System information
        with ui.card().classes('w-full'):
            ui.label('System Information').classes('text-h6 font-bold mb-3')
            with ui.column().classes('gap-2'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('info', color='primary')
                    ui.label(f'Version: {app_config.get("APP_VERSION")}').classes('text-body2')
                with ui.row().classes('items-center gap-2'):
                    ui.icon('schedule', color='primary')
                    ui.label(f'Deployed: {app_config.get("APP_DEPLOY_TIME")}').classes('text-body2')
                with ui.row().classes('items-center gap-2'):
                    ui.icon('bug_report', color='primary')
                    ui.label(f'Log Level: {app_config.get("APP_LOG_LEVEL")}').classes('text-body2')
    
@ui.page('/dashboard')
def dashboard():
    ui.page_title(APP_TITLE)
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    page_id = ui.context.client.page.path.lstrip('/')
    
    if not user_session.get('authenticated') :
        ui.navigate.to('/login')
        ui.notify('Unauthorized!Please log in to access the dashboard', type='warning')
        # Simple authentication (replace with actual authentication logic)
        return
    
    username = user_session.get('username')
    user_context = user_session.get('auth_user')    

    if not user_context['permissions'][f'{page_id}']:
        ui.navigate.to('/')
        ui.notify('Unauthorized!', type='warning')
        return  
    
    with ui.column().classes('w-full p-4'):
        with ui.row().classes('w-full justify-between items-center mb-4'):
            ui.label('Dashboard').classes('text-h3')
            ui.button('Logout', on_click=lambda: (user_session.clear(), ui.navigate.to('/login'))).props('outline')
        
        with ui.card().classes('p-4'):
            ui.label(f'Welcome to the dashboard, {username}!').classes('text-h6')
            ui.label(f'Here you can monitor system status and perform administrative tasks. Your permissions are {user_context["permissions"]}').classes('text-body1 mb-4')
            
        with ui.row().classes('gap-4 mt-4'):
            ui.button('Back to Home', on_click=lambda: ui.navigate.to('/')).props('outline')

@ui.page('/users')
def users_page():
    ui.page_title(APP_TITLE)
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    page_id = 'users'
    
    if not user_session.get('authenticated'):
        ui.navigate.to('/login')
        ui.notify('Please log in to access this page', type='warning')
        return
    
    username = user_session.get('username')
    auth_user = user_session.get('auth_user', {})
    permissions = auth_user.get('permissions', {})
    
    if not permissions.get(page_id, False):
        ui.navigate.to('/')
        ui.notify('Unauthorized! You do not have permission to access this page.', type='warning')
        return
    
    # Initialize UserManager
    user_manager = user_module.UserManager(db_client)
    
    # Header
    with ui.header().classes('items-center justify-between bg-primary text-white'):
        with ui.row().classes('items-center gap-4'):
            ui.image(APP_LOGO_PATH).classes('w-10 h-10')
            ui.label(APP_TITLE).classes('text-h5 font-bold')
        
        with ui.row().classes('items-center gap-4'):
            with ui.button(icon='account_circle').props('flat round color=white'):
                with ui.menu():
                    ui.menu_item(f'{username}', lambda: None).props('disable')
                    ui.separator()
                    ui.menu_item('Home', lambda: ui.navigate.to('/'))
                    ui.menu_item('Logout', lambda: (user_session.clear(), ui.navigate.to('/login')))
    
    # State management
    users_list = []
    selected_user_id = None
    
    def refresh_users():
        nonlocal users_list
        users_list = user_manager.get_all_users()
        users_table.update()
    
    def show_create_dialog():
        with ui.dialog() as create_dialog, ui.card().classes('w-96'):
            ui.label('Create New User').classes('text-h6 font-bold mb-4')
            
            username_input = ui.input('Username', placeholder='Enter username').classes('w-full').props('outlined')
            email_input = ui.input('Email', placeholder='Enter email').classes('w-full').props('outlined')
            full_name_input = ui.input('Full Name', placeholder='Enter full name').classes('w-full').props('outlined')
            password_input = ui.input('Password', placeholder='Enter password', password=True).classes('w-full').props('outlined')
            
            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('Create', on_click=lambda: handle_create()).props('color=primary')
                ui.button('Cancel', on_click=create_dialog.close).props('outline')
            
            def handle_create():
                if not username_input.value or not email_input.value or not password_input.value:
                    ui.notify('Please fill in all required fields', type='warning')
                    return
                
                user_id = user_manager.create_user(
                    username=username_input.value,
                    email=email_input.value,
                    password=password_input.value,
                    full_name=full_name_input.value or None,
                    status=1,
                    role_ids=[2]  # Default to 'user' role
                )
                
                if user_id:
                    ui.notify(f'User created successfully!', type='positive')
                    create_dialog.close()
                    refresh_users()
                else:
                    ui.notify('Failed to create user', type='negative')
        
        create_dialog.open()
    
    def show_edit_dialog(user_obj):
        with ui.dialog() as edit_dialog, ui.card().classes('w-96'):
            ui.label(f'Edit User: {user_obj.username}').classes('text-h6 font-bold mb-4')
            
            username_input = ui.input('Username', value=user_obj.username).classes('w-full').props('outlined')
            email_input = ui.input('Email', value=user_obj.email).classes('w-full').props('outlined')
            full_name_input = ui.input('Full Name', value=user_obj.full_name or '').classes('w-full').props('outlined')
            status_select = ui.select(
                {1: 'Active', 0: 'Inactive'},
                value=user_obj.status,
                label='Status'
            ).classes('w-full').props('outlined')
            
            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('Update', on_click=lambda: handle_update()).props('color=primary')
                ui.button('Cancel', on_click=edit_dialog.close).props('outline')
            
            def handle_update():
                success = user_manager.update_user(
                    user_id=user_obj.user_id,
                    username=username_input.value,
                    email=email_input.value,
                    full_name=full_name_input.value or None,
                    status=status_select.value
                )
                
                if success:
                    ui.notify('User updated successfully!', type='positive')
                    edit_dialog.close()
                    refresh_users()
                else:
                    ui.notify('Failed to update user', type='negative')
        
        edit_dialog.open()
    
    def show_password_dialog(user_obj):
        with ui.dialog() as password_dialog, ui.card().classes('w-96'):
            ui.label(f'Change Password: {user_obj.username}').classes('text-h6 font-bold mb-4')
            
            new_password_input = ui.input('New Password', password=True).classes('w-full').props('outlined')
            confirm_password_input = ui.input('Confirm Password', password=True).classes('w-full').props('outlined')
            
            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('Change', on_click=lambda: handle_change_password()).props('color=primary')
                ui.button('Cancel', on_click=password_dialog.close).props('outline')
            
            def handle_change_password():
                if not new_password_input.value or not confirm_password_input.value:
                    ui.notify('Please enter password in both fields', type='warning')
                    return
                
                if new_password_input.value != confirm_password_input.value:
                    ui.notify('Passwords do not match', type='negative')
                    return
                
                success = user_manager.update_password(user_obj.user_id, new_password_input.value)
                
                if success:
                    ui.notify('Password changed successfully!', type='positive')
                    password_dialog.close()
                else:
                    ui.notify('Failed to change password', type='negative')
        
        password_dialog.open()
    
    def confirm_delete(user_obj):
        with ui.dialog() as delete_dialog, ui.card():
            ui.label(f'Delete User: {user_obj.username}?').classes('text-h6 font-bold mb-4')
            ui.label('This action cannot be undone.').classes('text-body2 text-red mb-4')
            
            with ui.row().classes('gap-2'):
                ui.button('Delete', on_click=lambda: handle_delete(user_obj.user_id, delete_dialog)).props('color=negative')
                ui.button('Cancel', on_click=delete_dialog.close).props('outline')
        
        delete_dialog.open()
    
    def handle_delete(user_id, dialog):
        success = user_manager.delete_user(user_id)
        if success:
            ui.notify('User deleted successfully!', type='positive')
            dialog.close()
            refresh_users()
        else:
            ui.notify('Failed to delete user', type='negative')
    
    # Main content
    with ui.column().classes('w-full p-6 gap-4'):
        # Header section
        with ui.row().classes('w-full justify-between items-center'):
            with ui.column().classes('gap-1'):
                ui.label('User Management').classes('text-h4 font-bold')
                ui.label(f'Total Users: {user_manager.get_user_count()}').classes('text-body2 text-grey-7')
            
            with ui.row().classes('gap-2'):
                ui.button('Refresh', icon='refresh', on_click=refresh_users).props('outline color=primary')
                ui.button('Create User', icon='person_add', on_click=show_create_dialog).props('color=primary')
        
        # Users table
        with ui.card().classes('w-full'):
            users_list = user_manager.get_all_users()
            
            columns = [
                {'name': 'user_id', 'label': 'ID', 'field': 'user_id', 'sortable': True, 'align': 'left'},
                {'name': 'username', 'label': 'Username', 'field': 'username', 'sortable': True, 'align': 'left'},
                {'name': 'email', 'label': 'Email', 'field': 'email', 'sortable': True, 'align': 'left'},
                {'name': 'full_name', 'label': 'Full Name', 'field': 'full_name', 'sortable': True, 'align': 'left'},
                {'name': 'roles', 'label': 'Roles', 'field': 'roles', 'align': 'left'},
                {'name': 'status', 'label': 'Status', 'field': 'status', 'sortable': True, 'align': 'center'},
                {'name': 'created_at', 'label': 'Created At', 'field': 'created_at', 'sortable': True, 'align': 'left'},
                {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
            ]
            
            def get_rows():
                rows = []
                for user in users_list:
                    roles_text = ', '.join([role['role_name'] for role in (user.roles or [])])
                    status_text = 'Active' if user.status == 1 else 'Inactive'
                    created_text = user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else 'N/A'
                    
                    rows.append({
                        'user_id': user.user_id,
                        'username': user.username,
                        'email': user.email,
                        'full_name': user.full_name or '-',
                        'roles': roles_text or 'No roles',
                        'status': status_text,
                        'created_at': created_text,
                        'user_obj': user
                    })
                return rows
            
            users_table = ui.table(
                columns=columns,
                rows=get_rows(),
                row_key='user_id',
                pagination={'rowsPerPage': 10, 'sortBy': 'user_id', 'descending': True}
            ).classes('w-full')
            
            # Add action buttons in table
            users_table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn flat dense round icon="edit" color="primary" size="sm" @click="$parent.$emit('edit', props.row)">
                        <q-tooltip>Edit User</q-tooltip>
                    </q-btn>
                    <q-btn flat dense round icon="lock" color="secondary" size="sm" @click="$parent.$emit('password', props.row)">
                        <q-tooltip>Change Password</q-tooltip>
                    </q-btn>
                    <q-btn flat dense round icon="delete" color="negative" size="sm" @click="$parent.$emit('delete', props.row)">
                        <q-tooltip>Delete User</q-tooltip>
                    </q-btn>
                </q-td>
            ''')
            
            # Handle table events
            users_table.on('edit', lambda e: show_edit_dialog(e.args['user_obj']))
            users_table.on('password', lambda e: show_password_dialog(e.args['user_obj']))
            users_table.on('delete', lambda e: confirm_delete(e.args['user_obj']))


# Mount NiceGUI on FastAPI
ui.run_with(
    app,
    mount_path='/',
    storage_secret= app_config.get("APP_INIT_SECRET")
)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=int(app_config.get("APP_PORT")))