"""
Settings management page for Smart System Operator.
Provides interface for managing application settings.
"""

from nicegui import ui
import jsonlog
from settings import SettingsManager
from .shared import APP_TITLE, APP_LOGO_PATH, user_session, db_client

logger = jsonlog.setup_logger("settings_page")


@ui.page('/settings')
def settings_page():
    """Settings management page."""
    ui.page_title(APP_TITLE)
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    page_id = 'settings'
    
    # Authentication check
    if not user_session.get('authenticated'):
        ui.navigate.to('/login')
        ui.notify('Please log in to access this page', type='warning')
        return
    
    username = user_session.get('username')
    auth_user = user_session.get('auth_user', {})
    permissions = auth_user.get('permissions', {})
    
    # Permission check
    if not permissions.get(page_id, False):
        ui.navigate.to('/')
        ui.notify('Unauthorized! You do not have permission to access this page.', type='warning')
        return
    
    # Initialize SettingsManager
    settings_manager = SettingsManager(db_client)
    
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
    
    # Store UI elements for updating
    ui_elements = {}
    
    def load_settings():
        """Load settings from database and update UI."""
        try:
            groups = settings_manager.get_groups()
            
            for group in groups:
                group_settings = settings_manager.get_by_group(group)
                
                # Update UI elements with loaded values
                for setting in group_settings:
                    setting_name = setting['setting_name']
                    if setting_name in ui_elements:
                        ui_elements[setting_name].set_value(setting['setting_value'])
            
            logger.info("Settings loaded successfully")
            ui.notify('Settings loaded successfully!', type='positive')
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            ui.notify(f'Error loading settings: {e}', type='negative')
    
    def save_settings():
        """Save all settings to database."""
        try:
            success_count = 0
            for setting_name, element in ui_elements.items():
                if settings_manager.set(setting_name, element.value):
                    success_count += 1
            
            if success_count > 0:
                logger.info(f"Saved {success_count} settings")
                ui.notify(f'Successfully saved {success_count} settings!', type='positive')
                load_settings()
            else:
                ui.notify('No settings were saved', type='warning')
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            ui.notify(f'Error saving settings: {e}', type='negative')
    
    def reset_setting(setting_name):
        """Reset a single setting to default."""
        try:
            if settings_manager.reset_to_default(setting_name):
                ui.notify(f'Reset {setting_name} to default', type='positive')
                load_settings()
            else:
                ui.notify(f'Failed to reset {setting_name}', type='negative')
        except Exception as e:
            logger.error(f"Error resetting setting: {e}")
            ui.notify(f'Error: {e}', type='negative')
    
    # Main content
    with ui.column().classes('w-full p-6 gap-4'):
        # Header section
        with ui.row().classes('w-full justify-between items-center'):
            with ui.column().classes('gap-1'):
                ui.label('Application Settings').classes('text-h4 font-bold')
                ui.label('Manage system configuration and preferences').classes('text-body2 text-grey-7')
            
            with ui.row().classes('gap-2'):
                ui.button('Reload', icon='refresh', on_click=load_settings).props('outline color=primary')
                ui.button('Save Settings', icon='save', on_click=save_settings).props('color=primary')
        
        # Load all settings grouped by category
        try:
            groups = settings_manager.get_groups()
            
            for group in groups:
                group_settings = settings_manager.get_by_group(group)
                
                if not group_settings:
                    continue
                
                # Card for each group
                with ui.card().classes('w-full'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label(group).classes('text-h5 font-bold')
                        ui.label(f'{len(group_settings)} settings').classes('text-body2 text-grey-7')
                    
                    # Display each setting in the group
                    for setting in group_settings:
                        setting_id = setting['setting_id']
                        setting_name = setting['setting_name']
                        setting_value = setting['setting_value']
                        description = setting.get('description', '')
                        options = setting.get('options', [])
                        
                        with ui.column().classes('w-full mb-4'):
                            with ui.row().classes('w-full justify-between items-center'):
                                ui.label(description or setting_name).classes('text-subtitle1 font-medium')
                                ui.button(icon='refresh', on_click=lambda sn=setting_name: reset_setting(sn)) \
                                    .props('flat dense round size=sm').tooltip('Reset to default')
                            
                            # Create select with options
                            if options:
                                option_dict = {opt['option_value']: opt['option_label'] for opt in options}
                                ui_elements[setting_name] = ui.select(
                                    options=option_dict,
                                    value=setting_value,
                                    label=setting_name
                                ).props('outlined').classes('w-full')
                            else:
                                # Fallback to text input if no options
                                ui_elements[setting_name] = ui.input(
                                    label=setting_name,
                                    value=setting_value
                                ).props('outlined').classes('w-full')
                            
                            ui.separator().classes('mt-2')
        
        except Exception as e:
            logger.error(f"Error building settings UI: {e}")
            ui.notify(f'Error loading settings: {e}', type='negative')
    
    # Load settings on page ready
    load_settings()