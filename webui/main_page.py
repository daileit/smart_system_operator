"""
Main page for Smart System Operator.
Modern SaaS-style dashboard with feature highlights and navigation.
"""

from nicegui import ui
from .shared import (
    app_config, APP_TITLE, APP_LOGO_PATH, 
    user_session, system_status
)


@ui.page('/')
def main_page():
    """Modern SaaS-style main dashboard page."""
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

    # Modern Header with gradient
    with ui.header().classes('items-center justify-between').style(
        'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem 2rem;'
    ):
        with ui.row().classes('items-center gap-4'):
            ui.image(APP_LOGO_PATH).classes('w-12 h-12 rounded-lg shadow-lg')
            with ui.column().classes('gap-0'):
                ui.label(APP_TITLE).classes('text-h5 font-bold text-white')
                ui.label('AI-Powered Infrastructure Management').classes('text-caption text-white opacity-80')
        
        with ui.row().classes('items-center gap-4'):
            # System status indicator
            status_color = 'green' if system_status['is_alive'] else 'red'
            status_icon = 'check_circle' if system_status['is_alive'] else 'error'
            ui.icon(status_icon, size='sm').classes(f'text-{status_color} pulse')
            
            with ui.button(icon='account_circle').props('flat round color=white').classes('text-white'):
                with ui.menu():
                    ui.menu_item(f'👤 {full_name}', lambda: None).props('disable')
                    ui.menu_item(f'🎭 {role_names}', lambda: None).props('disable')
                    ui.separator()
                    ui.menu_item('⚙️ Settings', lambda: ui.notify('Settings clicked'))
                    ui.menu_item('🚪 Logout', lambda: (user_session.clear(), ui.navigate.to('/login')))
    
    # Main content with full-width layout
    with ui.column().classes('w-full').style('background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%); min-height: calc(100vh - 80px);'):
        
        # Hero Section
        with ui.row().classes('w-full justify-center').style('background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 4rem 2rem;'):
            with ui.column().classes('items-center gap-4 max-w-4xl'):
                ui.label(f'Welcome back, {full_name}! 👋').classes('text-h3 font-bold text-white text-center')
                ui.label('Your intelligent operations command center is ready').classes('text-h6 text-white opacity-90 text-center')
                
                # Quick stats badges
                with ui.row().classes('gap-4 mt-4 flex-wrap justify-center'):
                    with ui.card().classes('p-4 bg-white bg-opacity-20 backdrop-blur border-0').style('min-width: 150px;'):
                        with ui.column().classes('items-center gap-1'):
                            ui.icon('smart_toy', size='lg').classes('text-white')
                            ui.label('AI Powered').classes('text-caption text-white font-bold')
                            ui.label('GPT-4').classes('text-body2 text-white')
                    
                    with ui.card().classes('p-4 bg-white bg-opacity-20 backdrop-blur border-0').style('min-width: 150px;'):
                        with ui.column().classes('items-center gap-1'):
                            ui.icon('speed', size='lg').classes('text-white')
                            ui.label('Real-time').classes('text-caption text-white font-bold')
                            ui.label('Monitoring').classes('text-body2 text-white')
                    
                    with ui.card().classes('p-4 bg-white bg-opacity-20 backdrop-blur border-0').style('min-width: 150px;'):
                        with ui.column().classes('items-center gap-1'):
                            ui.icon('security', size='lg').classes('text-white')
                            ui.label('Secure').classes('text-caption text-white font-bold')
                            ui.label('SSH Access').classes('text-body2 text-white')
        
        # Main dashboard content
        with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6').style('margin-top: -3rem;'):
            
            # System Health Overview
            with ui.card().classes('w-full shadow-2xl').style('border-radius: 1rem; background: white;'):
                with ui.row().classes('w-full justify-between items-center p-6 border-b-2 border-gray-100'):
                    with ui.column().classes('gap-1'):
                        ui.label('System Health').classes('text-h5 font-bold text-gray-800')
                        ui.label('Real-time infrastructure status').classes('text-body2 text-gray-600')
                    ui.icon('monitor_heart', size='xl').classes('text-blue-500')
                
                with ui.row().classes('w-full gap-4 p-6 flex-wrap'):
                    # Database status
                    db_status = system_status['is_database_connected']
                    with ui.card().classes('flex-1 hover:shadow-xl transition-shadow cursor-pointer').style(
                        f'background: linear-gradient(135deg, {"#d4fc79 0%, #96e6a1" if db_status else "#fc6767 0%, #ec008c"} 100%); border: none; min-width: 200px;'
                    ):
                        with ui.column().classes('gap-2 p-4'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('storage', size='lg').classes('text-white')
                                ui.icon('check_circle' if db_status else 'error', size='sm').classes('text-white')
                            ui.label('Database').classes('text-subtitle2 text-white font-bold')
                            ui.label('Connected' if db_status else 'Disconnected').classes('text-h6 text-white font-bold')
                    
                    # Redis status
                    redis_status = system_status['is_redis_connected']
                    with ui.card().classes('flex-1 hover:shadow-xl transition-shadow cursor-pointer').style(
                        f'background: linear-gradient(135deg, {"#fa709a 0%, #fee140" if redis_status else "#fc6767 0%, #ec008c"} 100%); border: none; min-width: 200px;'
                    ):
                        with ui.column().classes('gap-2 p-4'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('cached', size='lg').classes('text-white')
                                ui.icon('check_circle' if redis_status else 'error', size='sm').classes('text-white')
                            ui.label('Redis Cache').classes('text-subtitle2 text-white font-bold')
                            ui.label('Active' if redis_status else 'Inactive').classes('text-h6 text-white font-bold')
                    
                    # AI status
                    ai_status = system_status['is_openai_connected']
                    with ui.card().classes('flex-1 hover:shadow-xl transition-shadow cursor-pointer').style(
                        f'background: linear-gradient(135deg, {"#a8edea 0%, #fed6e3" if ai_status else "#fc6767 0%, #ec008c"} 100%); border: none; min-width: 200px;'
                    ):
                        with ui.column().classes('gap-2 p-4'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('psychology', size='lg').classes('text-white')
                                ui.icon('check_circle' if ai_status else 'error', size='sm').classes('text-white')
                            ui.label('AI Engine').classes('text-subtitle2 text-white font-bold')
                            ui.label('Ready' if ai_status else 'Offline').classes('text-h6 text-white font-bold')
                    
                    # System status
                    sys_status = system_status['is_alive']
                    with ui.card().classes('flex-1 hover:shadow-xl transition-shadow cursor-pointer').style(
                        f'background: linear-gradient(135deg, {"#667eea 0%, #764ba2" if sys_status else "#fc6767 0%, #ec008c"} 100%); border: none; min-width: 200px;'
                    ):
                        with ui.column().classes('gap-2 p-4'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('verified', size='lg').classes('text-white')
                                ui.icon('check_circle' if sys_status else 'error', size='sm').classes('text-white')
                            ui.label('System').classes('text-subtitle2 text-white font-bold')
                            ui.label('Operational' if sys_status else 'Down').classes('text-h6 text-white font-bold')
            
            # Features & Navigation Grid
            ui.label('🚀 Platform Features').classes('text-h4 font-bold text-gray-800 mt-4')
            ui.label('Explore powerful capabilities at your fingertips').classes('text-body1 text-gray-600 mb-2')
            
            with ui.row().classes('w-full gap-6 flex-wrap'):
                # Dashboard feature
                if permissions.get('dashboard', False):
                    with ui.card().classes('flex-1 hover:shadow-2xl transition-all cursor-pointer').style(
                        'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; min-width: 300px; max-width: 400px;'
                    ).on('click', lambda: ui.navigate.to('/dashboard')):
                        with ui.column().classes('gap-3 p-6'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('dashboard', size='xl').classes('text-white')
                                ui.icon('arrow_forward', size='sm').classes('text-white opacity-70')
                            ui.label('Live Dashboard').classes('text-h5 text-white font-bold')
                            ui.label('Real-time server metrics with AI-powered insights. Monitor CPU, memory, processes, and get intelligent recommendations.').classes('text-body2 text-white opacity-90')
                            with ui.row().classes('gap-2 mt-2 flex-wrap'):
                                ui.badge('Real-time', color='white').classes('text-purple-600')
                                ui.badge('AI Analysis', color='white').classes('text-purple-600')
                                ui.badge('Auto-refresh', color='white').classes('text-purple-600')
                else:
                    with ui.card().classes('flex-1 opacity-50').style(
                        'background: linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%); border: none; min-width: 300px; max-width: 400px;'
                    ):
                        with ui.column().classes('gap-3 p-6'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('dashboard', size='xl').classes('text-white')
                                ui.icon('lock', size='sm').classes('text-white')
                            ui.label('Live Dashboard').classes('text-h5 text-white font-bold')
                            ui.label('Access restricted - Contact administrator').classes('text-body2 text-white opacity-70')
                
                # Servers feature
                if permissions.get('servers', False):
                    with ui.card().classes('flex-1 hover:shadow-2xl transition-all cursor-pointer').style(
                        'background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border: none; min-width: 300px; max-width: 400px;'
                    ).on('click', lambda: ui.navigate.to('/servers')):
                        with ui.column().classes('gap-3 p-6'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('dns', size='xl').classes('text-white')
                                ui.icon('arrow_forward', size='sm').classes('text-white opacity-70')
                            ui.label('Server Management').classes('text-h5 text-white font-bold')
                            ui.label('Manage your server infrastructure. Add servers, configure SSH access, assign actions, and control automation settings.').classes('text-body2 text-white opacity-90')
                            with ui.row().classes('gap-2 mt-2 flex-wrap'):
                                ui.badge('SSH', color='white').classes('text-pink-600')
                                ui.badge('Actions', color='white').classes('text-pink-600')
                                ui.badge('Automation', color='white').classes('text-pink-600')
                else:
                    with ui.card().classes('flex-1 opacity-50').style(
                        'background: linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%); border: none; min-width: 300px; max-width: 400px;'
                    ):
                        with ui.column().classes('gap-3 p-6'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('dns', size='xl').classes('text-white')
                                ui.icon('lock', size='sm').classes('text-white')
                            ui.label('Server Management').classes('text-h5 text-white font-bold')
                            ui.label('Access restricted - Contact administrator').classes('text-body2 text-white opacity-70')
                
                # Users feature
                if permissions.get('users', False):
                    with ui.card().classes('flex-1 hover:shadow-2xl transition-all cursor-pointer').style(
                        'background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); border: none; min-width: 300px; max-width: 400px;'
                    ).on('click', lambda: ui.navigate.to('/users')):
                        with ui.column().classes('gap-3 p-6'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('people', size='xl').classes('text-white')
                                ui.icon('arrow_forward', size='sm').classes('text-white opacity-70')
                            ui.label('User Management').classes('text-h5 text-white font-bold')
                            ui.label('Manage users, roles, and permissions. Control access to platform features with granular permission system.').classes('text-body2 text-white opacity-90')
                            with ui.row().classes('gap-2 mt-2 flex-wrap'):
                                ui.badge('RBAC', color='white').classes('text-blue-600')
                                ui.badge('Permissions', color='white').classes('text-blue-600')
                                ui.badge('Security', color='white').classes('text-blue-600')
                else:
                    with ui.card().classes('flex-1 opacity-50').style(
                        'background: linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%); border: none; min-width: 300px; max-width: 400px;'
                    ):
                        with ui.column().classes('gap-3 p-6'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('people', size='xl').classes('text-white')
                                ui.icon('lock', size='sm').classes('text-white')
                            ui.label('User Management').classes('text-h5 text-white font-bold')
                            ui.label('Access restricted - Contact administrator').classes('text-body2 text-white opacity-70')
                
                # Reports feature
                if permissions.get('reports', False):
                    with ui.card().classes('flex-1 hover:shadow-2xl transition-all cursor-pointer').style(
                        'background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); border: none; min-width: 300px; max-width: 400px;'
                    ).on('click', lambda: ui.navigate.to('/reports')):
                        with ui.column().classes('gap-3 p-6'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('assessment', size='xl').classes('text-white')
                                ui.icon('arrow_forward', size='sm').classes('text-white opacity-70')
                            ui.label('Reports & Analytics').classes('text-h5 text-white font-bold')
                            ui.label('View detailed reports, execution logs, and performance analytics. Track AI recommendations and system health trends.').classes('text-body2 text-white opacity-90')
                            with ui.row().classes('gap-2 mt-2 flex-wrap'):
                                ui.badge('Logs', color='white').classes('text-orange-600')
                                ui.badge('Analytics', color='white').classes('text-orange-600')
                                ui.badge('Export', color='white').classes('text-orange-600')
                else:
                    with ui.card().classes('flex-1 opacity-50').style(
                        'background: linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%); border: none; min-width: 300px; max-width: 400px;'
                    ):
                        with ui.column().classes('gap-3 p-6'):
                            with ui.row().classes('items-center justify-between w-full'):
                                ui.icon('assessment', size='xl').classes('text-white')
                                ui.icon('lock', size='sm').classes('text-white')
                            ui.label('Reports & Analytics').classes('text-h5 text-white font-bold')
                            ui.label('Access restricted - Contact administrator').classes('text-body2 text-white opacity-70')
            
            # How It Works Section
            with ui.card().classes('w-full shadow-xl mt-6').style('border-radius: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none;'):
                with ui.column().classes('gap-6 p-8'):
                    with ui.column().classes('items-center gap-2 mb-4'):
                        ui.label('⚡ How Smart System Operator Works').classes('text-h4 font-bold text-white text-center')
                        ui.label('Intelligent automation in 4 simple steps').classes('text-body1 text-white opacity-90 text-center')
                    
                    with ui.row().classes('w-full gap-6 flex-wrap justify-center'):
                        # Step 1
                        with ui.card().classes('flex-1 bg-white bg-opacity-10 backdrop-blur border-0').style('min-width: 200px; max-width: 250px;'):
                            with ui.column().classes('gap-3 p-4 items-center'):
                                with ui.card().classes('w-16 h-16 bg-white flex items-center justify-center').style('border-radius: 50%;'):
                                    ui.label('1').classes('text-h4 font-bold text-purple-600')
                                ui.icon('speed', size='xl').classes('text-white')
                                ui.label('Monitor').classes('text-h6 text-white font-bold text-center')
                                ui.label('Cron jobs collect real-time server metrics every 60s').classes('text-caption text-white opacity-80 text-center')
                        
                        # Step 2
                        with ui.card().classes('flex-1 bg-white bg-opacity-10 backdrop-blur border-0').style('min-width: 200px; max-width: 250px;'):
                            with ui.column().classes('gap-3 p-4 items-center'):
                                with ui.card().classes('w-16 h-16 bg-white flex items-center justify-center').style('border-radius: 50%;'):
                                    ui.label('2').classes('text-h4 font-bold text-purple-600')
                                ui.icon('smart_toy', size='xl').classes('text-white')
                                ui.label('Analyze').classes('text-h6 text-white font-bold text-center')
                                ui.label('AI analyzes metrics with historical context every 300s').classes('text-caption text-white opacity-80 text-center')
                        
                        # Step 3
                        with ui.card().classes('flex-1 bg-white bg-opacity-10 backdrop-blur border-0').style('min-width: 200px; max-width: 250px;'):
                            with ui.column().classes('gap-3 p-4 items-center'):
                                with ui.card().classes('w-16 h-16 bg-white flex items-center justify-center').style('border-radius: 50%;'):
                                    ui.label('3').classes('text-h4 font-bold text-purple-600')
                                ui.icon('lightbulb', size='xl').classes('text-white')
                                ui.label('Recommend').classes('text-h6 text-white font-bold text-center')
                                ui.label('Get intelligent action recommendations with reasoning').classes('text-caption text-white opacity-80 text-center')
                        
                        # Step 4
                        with ui.card().classes('flex-1 bg-white bg-opacity-10 backdrop-blur border-0').style('min-width: 200px; max-width: 250px;'):
                            with ui.column().classes('gap-3 p-4 items-center'):
                                with ui.card().classes('w-16 h-16 bg-white flex items-center justify-center').style('border-radius: 50%;'):
                                    ui.label('4').classes('text-h4 font-bold text-purple-600')
                                ui.icon('play_arrow', size='xl').classes('text-white')
                                ui.label('Execute').classes('text-h6 text-white font-bold text-center')
                                ui.label('Low-risk actions auto-execute, others await approval').classes('text-caption text-white opacity-80 text-center')
            
            # Platform Info Section
            with ui.row().classes('w-full gap-6 mt-6 flex-wrap'):
                # Technical Stack
                with ui.card().classes('flex-1 shadow-lg').style('border-radius: 1rem; min-width: 300px;'):
                    with ui.column().classes('gap-4 p-6'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('code', size='lg').classes('text-indigo-600')
                            ui.label('Technical Stack').classes('text-h6 font-bold text-gray-800')
                        
                        with ui.column().classes('gap-2'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('storage', size='sm').classes('text-blue-500')
                                ui.label('Database: MySQL with utf8mb4').classes('text-body2 text-gray-700')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('cached', size='sm').classes('text-red-500')
                                ui.label('Cache: Redis (24h TTL)').classes('text-body2 text-gray-700')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('psychology', size='sm').classes('text-green-500')
                                ui.label('AI: OpenAI GPT-4').classes('text-body2 text-gray-700')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('security', size='sm').classes('text-purple-500')
                                ui.label('SSH: Paramiko library').classes('text-body2 text-gray-700')
                
                # System Info
                with ui.card().classes('flex-1 shadow-lg').style('border-radius: 1rem; min-width: 300px;'):
                    with ui.column().classes('gap-4 p-6'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('info', size='lg').classes('text-blue-600')
                            ui.label('System Information').classes('text-h6 font-bold text-gray-800')
                        
                        with ui.column().classes('gap-2'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('tag', size='sm').classes('text-gray-600')
                                ui.label(f'Version: {app_config.get("APP_VERSION", "1.0.0")}').classes('text-body2 text-gray-700')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('schedule', size='sm').classes('text-gray-600')
                                ui.label(f'Deployed: {app_config.get("APP_DEPLOY_TIME", "N/A")}').classes('text-body2 text-gray-700')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('bug_report', size='sm').classes('text-gray-600')
                                ui.label(f'Log Level: {app_config.get("APP_LOG_LEVEL", "INFO")}').classes('text-body2 text-gray-700')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('person', size='sm').classes('text-gray-600')
                                ui.label(f'Your Role: {role_names}').classes('text-body2 text-gray-700')
                
                # Quick Stats
                with ui.card().classes('flex-1 shadow-lg').style('border-radius: 1rem; min-width: 300px;'):
                    with ui.column().classes('gap-4 p-6'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('insights', size='lg').classes('text-green-600')
                            ui.label('Your Access').classes('text-h6 font-bold text-gray-800')
                        
                        with ui.column().classes('gap-2'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('verified_user', size='sm').classes('text-green-600')
                                ui.label(f'Permissions: {sum(permissions.values())} pages').classes('text-body2 text-gray-700')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('shield', size='sm').classes('text-blue-600')
                                ui.label(f'Roles: {len(roles)} active').classes('text-body2 text-gray-700')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('account_circle', size='sm').classes('text-purple-600')
                                ui.label(f'User: {username}').classes('text-body2 text-gray-700')
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('badge', size='sm').classes('text-orange-600')
                                ui.label(f'Name: {full_name}').classes('text-body2 text-gray-700')
        
        # Footer
        with ui.row().classes('w-full justify-center p-8 mt-6'):
            with ui.column().classes('items-center gap-2'):
                ui.label(f'{APP_TITLE} © 2025').classes('text-body2 text-gray-600')
                ui.label('Powered by AI • Built with ❤️').classes('text-caption text-gray-500')
