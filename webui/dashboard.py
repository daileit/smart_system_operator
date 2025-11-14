"""
Dashboard page for Smart System Operator.
Detailed dashboard view with system monitoring.
"""

from nicegui import ui
from .shared import APP_TITLE, APP_LOGO_PATH, user_session


@ui.page('/dashboard')
def dashboard_page():
    """Dashboard detail page."""
    ui.page_title(APP_TITLE)
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    page_id = ui.context.client.page.path.lstrip('/')
    
    if not user_session.get('authenticated'):
        ui.navigate.to('/login')
        ui.notify('Unauthorized! Please log in to access the dashboard', type='warning')
        return
    
    username = user_session.get('username')
    user_context = user_session.get('auth_user')    

    if not user_context['permissions'].get(f'{page_id}', False):
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
