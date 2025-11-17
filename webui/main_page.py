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
            # System status indicator
            status_color = 'positive' if system_status['is_alive'] else 'negative'
            status_text = 'Operational' if system_status['is_alive'] else 'Offline'
            ui.badge(status_text, color=status_color)
            
            with ui.button(icon='account_circle').props('flat round color=white'):
                with ui.menu():
                    ui.menu_item(f'{full_name}', lambda: None).props('disable')
                    ui.menu_item(f'Role: {role_names}', lambda: None).props('disable')
                    ui.separator()
                    ui.menu_item('Settings', lambda: ui.navigate.to('/settings'))
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
                {'id': 'servers', 'icon': 'dns', 'label': 'Servers', 'path': '/servers'},
                {'id': 'users', 'icon': 'people', 'label': 'Users', 'path': '/users'},
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
            
            # System Status in drawer
            ui.label('System Status').classes('text-caption text-grey-6 mb-2')
            with ui.card().classes('w-full bg-white'):
                with ui.column().classes('gap-2 p-2'):
                    with ui.row().classes('items-center gap-2'):
                        db_icon = 'check_circle' if system_status['is_database_connected'] else 'cancel'
                        db_color = 'positive' if system_status['is_database_connected'] else 'negative'
                        ui.icon(db_icon, color=db_color, size='xs')
                        ui.label('Database').classes('text-caption')
                    with ui.row().classes('items-center gap-2'):
                        redis_icon = 'check_circle' if system_status['is_redis_connected'] else 'cancel'
                        redis_color = 'positive' if system_status['is_redis_connected'] else 'negative'
                        ui.icon(redis_icon, color=redis_color, size='xs')
                        ui.label('Redis').classes('text-caption')
                    with ui.row().classes('items-center gap-2'):
                        ai_icon = 'check_circle' if system_status['is_openai_connected'] else 'cancel'
                        ai_color = 'positive' if system_status['is_openai_connected'] else 'negative'
                        ui.icon(ai_icon, color=ai_color, size='xs')
                        ui.label('AI Engine').classes('text-caption')
            
            ui.separator().classes('my-4')
            
            # User info in drawer
            ui.label('User Info').classes('text-caption text-grey-6 mb-2')
            with ui.card().classes('w-full bg-white'):
                with ui.column().classes('gap-1 p-2'):
                    ui.label(full_name).classes('text-body2 font-bold')
                    ui.label(username).classes('text-caption text-grey-7')
                    ui.label(role_names).classes('text-caption text-primary')
    
    # Main content area
    with ui.column().classes('w-full p-6 gap-4'):
        # Welcome section
        with ui.card().classes('w-full bg-primary text-white'):
            with ui.column().classes('p-4 gap-2'):
                ui.label(f'Welcome back, {full_name}!').classes('text-h4 font-bold')
                ui.label(f'Your intelligent operations command center').classes('text-body1')
                ui.label(f'Role: {role_names}').classes('text-caption')
        
        # System Health Overview
        with ui.card().classes('w-full'):
            ui.label('System Health').classes('text-h5 font-bold mb-4')
            
            with ui.row().classes('w-full gap-4 flex-wrap'):
                # Database status
                with ui.card().classes('flex-1').style('min-width: 200px;'):
                    with ui.column().classes('gap-2 p-4'):
                        with ui.row().classes('items-center gap-3'):
                            db_color = 'positive' if system_status['is_database_connected'] else 'negative'
                            ui.icon('storage', color=db_color).classes('text-5xl')
                            with ui.column():
                                ui.label('Database').classes('text-subtitle2 text-grey-7')
                                status_text = 'Connected' if system_status['is_database_connected'] else 'Disconnected'
                                ui.label(status_text).classes(f'text-h6 font-bold text-{db_color}')
                
                # Redis status
                with ui.card().classes('flex-1').style('min-width: 200px;'):
                    with ui.column().classes('gap-2 p-4'):
                        with ui.row().classes('items-center gap-3'):
                            redis_color = 'positive' if system_status['is_redis_connected'] else 'negative'
                            ui.icon('cached', color=redis_color).classes('text-5xl')
                            with ui.column():
                                ui.label('Redis Cache').classes('text-subtitle2 text-grey-7')
                                status_text = 'Active' if system_status['is_redis_connected'] else 'Inactive'
                                ui.label(status_text).classes(f'text-h6 font-bold text-{redis_color}')
                
                # AI status
                with ui.card().classes('flex-1').style('min-width: 200px;'):
                    with ui.column().classes('gap-2 p-4'):
                        with ui.row().classes('items-center gap-3'):
                            ai_color = 'positive' if system_status['is_openai_connected'] else 'negative'
                            ui.icon('psychology', color=ai_color).classes('text-5xl')
                            with ui.column():
                                ui.label('AI Engine').classes('text-subtitle2 text-grey-7')
                                status_text = 'Ready' if system_status['is_openai_connected'] else 'Offline'
                                ui.label(status_text).classes(f'text-h6 font-bold text-{ai_color}')
                
                # System status
                with ui.card().classes('flex-1').style('min-width: 200px;'):
                    with ui.column().classes('gap-2 p-4'):
                        with ui.row().classes('items-center gap-3'):
                            sys_color = 'positive' if system_status['is_alive'] else 'negative'
                            ui.icon('verified', color=sys_color).classes('text-5xl')
                            with ui.column():
                                ui.label('System').classes('text-subtitle2 text-grey-7')
                                status_text = 'Operational' if system_status['is_alive'] else 'Down'
                                ui.label(status_text).classes(f'text-h6 font-bold text-{sys_color}')
        
        # Quick Access
        with ui.card().classes('w-full'):
            ui.label('Quick Access').classes('text-h5 font-bold mb-4')
            
            with ui.row().classes('w-full gap-4 flex-wrap'):
                if permissions.get('dashboard', False):
                    with ui.card().classes('flex-1 cursor-pointer hover:shadow-lg transition-shadow').style('min-width: 250px;').on('click', lambda: ui.navigate.to('/dashboard')):
                        with ui.column().classes('gap-2 p-4'):
                            ui.icon('dashboard', color='primary').classes('text-5xl')
                            ui.label('Live Dashboard').classes('text-h6 font-bold')
                            ui.label('Real-time server metrics with AI-powered insights').classes('text-body2 text-grey-7')
                            with ui.row().classes('gap-2 mt-2'):
                                ui.badge('Real-time', color='primary')
                                ui.badge('AI Analysis', color='secondary')
                
                if permissions.get('servers', False):
                    with ui.card().classes('flex-1 cursor-pointer hover:shadow-lg transition-shadow').style('min-width: 250px;').on('click', lambda: ui.navigate.to('/servers')):
                        with ui.column().classes('gap-2 p-4'):
                            ui.icon('dns', color='secondary').classes('text-5xl')
                            ui.label('Server Management').classes('text-h6 font-bold')
                            ui.label('Manage servers, configure SSH, and control automation').classes('text-body2 text-grey-7')
                            with ui.row().classes('gap-2 mt-2'):
                                ui.badge('SSH', color='secondary')
                                ui.badge('Automation', color='primary')
                
                if permissions.get('users', False):
                    with ui.card().classes('flex-1 cursor-pointer hover:shadow-lg transition-shadow').style('min-width: 250px;').on('click', lambda: ui.navigate.to('/users')):
                        with ui.column().classes('gap-2 p-4'):
                            ui.icon('people', color='primary').classes('text-5xl')
                            ui.label('User Management').classes('text-h6 font-bold')
                            ui.label('Manage users, roles, and permissions').classes('text-body2 text-grey-7')
                            with ui.row().classes('gap-2 mt-2'):
                                ui.badge('RBAC', color='primary')
                                ui.badge('Security', color='secondary')
                
                if permissions.get('reports', False):
                    with ui.card().classes('flex-1 cursor-pointer hover:shadow-lg transition-shadow').style('min-width: 250px;').on('click', lambda: ui.navigate.to('/reports')):
                        with ui.column().classes('gap-2 p-4'):
                            ui.icon('assessment', color='secondary').classes('text-5xl')
                            ui.label('Reports & Analytics').classes('text-h6 font-bold')
                            ui.label('View execution logs and performance analytics').classes('text-body2 text-grey-7')
                            with ui.row().classes('gap-2 mt-2'):
                                ui.badge('Logs', color='secondary')
                                ui.badge('Analytics', color='primary')
        
        # How It Works
        with ui.card().classes('w-full'):
            ui.label('How Smart System Operator Works').classes('text-h5 font-bold mb-4')
            
            with ui.row().classes('w-full gap-4 flex-wrap'):
                with ui.card().classes('flex-1 bg-grey-1').style('min-width: 200px;'):
                    with ui.column().classes('gap-2 p-4 items-center'):
                        ui.badge('1', color='primary').classes('text-h6')
                        ui.icon('speed', color='primary').classes('text-4xl')
                        ui.label('Monitor').classes('text-subtitle1 font-bold')
                        ui.label(f'Collect CPU & RAM metrics every {app_config.get("APP_CRAWLER_DELAY", "60s")}').classes('text-caption text-grey-7 text-center')
                
                with ui.card().classes('flex-1 bg-grey-1').style('min-width: 200px;'):
                    with ui.column().classes('gap-2 p-4 items-center'):
                        ui.badge('2', color='primary').classes('text-h6')
                        ui.icon('smart_toy', color='secondary').classes('text-4xl')
                        ui.label('Analyze').classes('text-subtitle1 font-bold')
                        ui.label(f'AI analyzes with historical context every {app_config.get("APP_MODEL_DELAY", "300s")}').classes('text-caption text-grey-7 text-center')
                
                with ui.card().classes('flex-1 bg-grey-1').style('min-width: 200px;'):
                    with ui.column().classes('gap-2 p-4 items-center'):
                        ui.badge('3', color='primary').classes('text-h6')
                        ui.icon('lightbulb', color='warning').classes('text-4xl')
                        ui.label('Recommend').classes('text-subtitle1 font-bold')
                        ui.label('Get intelligent action recommendations').classes('text-caption text-grey-7 text-center')
                
                with ui.card().classes('flex-1 bg-grey-1').style('min-width: 200px;'):
                    with ui.column().classes('gap-2 p-4 items-center'):
                        ui.badge('4', color='primary').classes('text-h6')
                        ui.icon('play_arrow', color='positive').classes('text-4xl')
                        ui.label('Execute').classes('text-subtitle1 font-bold')
                        ui.label('Low-risk actions auto-execute automatically').classes('text-caption text-grey-7 text-center')
        
        # Platform Info
        with ui.row().classes('w-full gap-4 flex-wrap'):
            # Technical Stack
            with ui.card().classes('flex-1').style('min-width: 300px;'):
                with ui.column().classes('gap-3 p-4'):
                    ui.label('Technical Stack').classes('text-h6 font-bold mb-2')
                    
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('storage', size='sm', color='primary')
                        ui.label('MySQL with utf8mb4').classes('text-body2')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('cached', size='sm', color='negative')
                        ui.label('Redis Cache (24h TTL)').classes('text-body2')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('psychology', size='sm', color='positive')
                        ui.label('OpenAI Compatible').classes('text-body2')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('security', size='sm', color='secondary')
                        ui.label('SSH via Paramiko').classes('text-body2')
            
            # System Info
            with ui.card().classes('flex-1').style('min-width: 300px;'):
                with ui.column().classes('gap-3 p-4'):
                    ui.label('System Information').classes('text-h6 font-bold mb-2')
                    
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('tag', size='sm', color='primary')
                        ui.label(f'Version: {app_config.get("APP_VERSION", "1.0.0")}').classes('text-body2')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('schedule', size='sm', color='primary')
                        ui.label(f'Deployed: {app_config.get("APP_DEPLOY_TIME", "N/A")}').classes('text-body2')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('bug_report', size='sm', color='primary')
                        ui.label(f'Log Level: {app_config.get("APP_LOG_LEVEL", "INFO")}').classes('text-body2')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('schedule', size='sm', color='primary')
                        ui.label(f'Cron Interval: {app_config.get("APP_CRON_INTERVAL", "60s")}').classes('text-body2')
            
            # Your Access
            with ui.card().classes('flex-1').style('min-width: 300px;'):
                with ui.column().classes('gap-3 p-4'):
                    ui.label('Your Access').classes('text-h6 font-bold mb-2')
                    
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('verified_user', size='sm', color='positive')
                        ui.label(f'Permissions: {sum(permissions.values())} pages').classes('text-body2')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('shield', size='sm', color='primary')
                        ui.label(f'Roles: {len(roles)} active').classes('text-body2')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('account_circle', size='sm', color='secondary')
                        ui.label(f'User: {username}').classes('text-body2')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('person', size='sm', color='primary')
                        ui.label(f'Full Name: {full_name}').classes('text-body2')
    