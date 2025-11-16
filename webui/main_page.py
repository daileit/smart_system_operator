"""
Main page for Smart System Operator.
Dashboard home page with navigation and quick stats.
"""

from nicegui import ui
from .shared import (
    app_config, APP_TITLE, APP_LOGO_PATH, 
    user_session, system_status
)


@ui.page('/')
def main_page():
    """Main dashboard page."""
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
                {'id': 'servers', 'icon': 'dns', 'label': 'Servers', 'path': '/servers'},
                {'id': 'reports', 'icon': 'assessment', 'label': 'Reports', 'path': '/reports'},
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
                if permissions.get('servers', False):
                    with ui.button('Servers', icon='dns', on_click=lambda: ui.navigate.to('/servers')).props('outline color=secondary'):
                        pass
                if permissions.get('users', False):
                    with ui.button('Manage Users', icon='people', on_click=lambda: ui.navigate.to('/users')).props('color=secondary'):
                        pass
                if permissions.get('reports', False):
                    with ui.button('View Reports', icon='assessment', on_click=lambda: ui.navigate.to('/reports')).props('outline color=primary'):
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
