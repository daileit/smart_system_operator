"""
Servers management page for Smart System Operator.
Provides CRUD operations for server management with SSH connection testing.
"""

from nicegui import ui
import jsonlog
import servers as servers_module
import action as action_module
from .shared import APP_TITLE, APP_LOGO_PATH, user_session, db_client

logger = jsonlog.setup_logger("servers_page")


@ui.page('/servers')
def servers_page():
    """Servers management page with CRUD operations."""
    ui.page_title(APP_TITLE)
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    page_id = 'servers'
    
    if not user_session.get('authenticated'):
        ui.navigate.to('/login')
        ui.notify('Please log in to access this page', type='warning')
        return
    
    username = user_session.get('username')
    auth_user = user_session.get('auth_user', {})
    permissions = auth_user.get('permissions', {})
    user_id = auth_user.get('user_id')
    
    if not permissions.get(page_id, False):
        ui.navigate.to('/')
        ui.notify('Unauthorized! You do not have permission to access this page.', type='warning')
        return
    
    # Initialize Managers
    server_manager = servers_module.ServerManager(db_client)
    action_manager = action_module.ActionManager(db_client)
    
    # Load all available actions
    available_actions = action_manager.get_all_actions()
    action_options = {action['id']: f"{action['action_name']} ({action['action_type']})" 
                     for action in available_actions}
    
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
    servers_list = []
    
    def refresh_servers():
        updated_list = server_manager.get_all_servers(include_actions=True)
        servers_table.update_rows(rows=get_rows(updated_list), clear_selection=True)
    
    def test_connection(host, port, username, ssh_key_path, test_button=None):
        """Test SSH connection to server."""
        try:
            if test_button:
                test_button.props('loading')
            
            result = action_manager.execute_ssh_command(
                host=host,
                port=int(port),
                username=username,
                ssh_key_path=ssh_key_path,
                command='echo "Connection test successful"',
                timeout=10
            )
            
            if test_button:
                test_button.props(remove='loading')
            
            if result.success:
                ui.notify('✓ Connection test successful!', type='positive')
                return True
            else:
                ui.notify(f'✗ Connection failed: {result.error}', type='negative')
                return False
                
        except Exception as e:
            if test_button:
                test_button.props(remove='loading')
            ui.notify(f'✗ Connection test error: {str(e)}', type='negative')
            return False
    
    def show_create_dialog():
        connection_tested = {'value': False}
        
        with ui.dialog() as create_dialog, ui.card().classes('w-[600px]'):
            ui.label('Add New Server').classes('text-h6 font-bold mb-4')
            
            with ui.row().classes('w-full gap-4'):
                with ui.column().classes('w-1/2 gap-2'):
                    name_input = ui.input('Server Name', placeholder='e.g., Web Server 1') \
                        .classes('w-full').props('outlined')
                    ip_input = ui.input('IP Address', placeholder='e.g., 192.168.1.100') \
                        .classes('w-full').props('outlined')
                    port_input = ui.number('SSH Port', value=22, min=1, max=65535) \
                        .classes('w-full').props('outlined')
                
                with ui.column().classes('w-1/2 gap-2'):
                    username_input = ui.input('SSH Username', placeholder='e.g., root') \
                        .classes('w-full').props('outlined')
                    ssh_key_input = ui.input('SSH Key Path', placeholder='/path/to/private_key') \
                        .classes('w-full').props('outlined')
                    description_input = ui.textarea('Description', placeholder='Optional description') \
                        .classes('w-full').props('outlined')
            
            # Connection test section
            with ui.card().classes('w-full bg-blue-grey-1 mt-2'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column().classes('gap-1'):
                        ui.label('Connection Test').classes('text-subtitle2 font-bold')
                        connection_status = ui.label('Not tested yet').classes('text-caption text-grey-7')
                    test_btn = ui.button('Test Connection', icon='wifi_tethering', 
                                        on_click=lambda: handle_test()).props('outline color=primary')
            
            def handle_test():
                if not ip_input.value or not username_input.value or not ssh_key_input.value:
                    ui.notify('Please fill in IP, username, and SSH key path first', type='warning')
                    return
                
                connection_status.text = 'Testing...'
                connection_status.classes('text-caption text-orange')
                
                success = test_connection(
                    ip_input.value,
                    port_input.value or 22,
                    username_input.value,
                    ssh_key_input.value,
                    test_btn
                )
                
                if success:
                    connection_tested['value'] = True
                    connection_status.text = '✓ Connection successful'
                    connection_status.classes('text-caption text-positive font-bold')
                else:
                    connection_tested['value'] = False
                    connection_status.text = '✗ Connection failed'
                    connection_status.classes('text-caption text-negative')
            
            # Actions selection
            ui.separator().classes('my-4')
            ui.label('Allowed Actions').classes('text-subtitle2 font-bold mb-2')
            ui.label('Select actions that can be executed on this server').classes('text-caption text-grey-7 mb-2')
            
            actions_select = ui.select(
                action_options,
                label='Actions',
                multiple=True,
                value=[]
            ).classes('w-full').props('outlined use-chips')
            
            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('Create Server', icon='add', on_click=lambda: handle_create()).props('color=primary')
                ui.button('Cancel', on_click=create_dialog.close).props('outline')
            
            def handle_create():
                if not name_input.value or not ip_input.value or not username_input.value or not ssh_key_input.value:
                    ui.notify('Please fill in all required fields', type='warning')
                    return
                
                if not connection_tested['value']:
                    ui.notify('Please test the connection before creating the server', type='warning')
                    return
                
                selected_actions = actions_select.value if isinstance(actions_select.value, list) else (
                    [actions_select.value] if actions_select.value else []
                )
                
                server_id = server_manager.create_server(
                    name=name_input.value,
                    ip_address=ip_input.value,
                    username=username_input.value,
                    ssh_key_path=ssh_key_input.value,
                    port=int(port_input.value or 22),
                    description=description_input.value or None,
                    created_by=user_id,
                    action_ids=selected_actions
                )
                
                if server_id:
                    ui.notify(f'Server created successfully!', type='positive')
                    create_dialog.close()
                    refresh_servers()
                else:
                    ui.notify('Failed to create server (may already exist)', type='negative')
        
        create_dialog.open()
    
    def show_edit_dialog(server_id):
        server = server_manager.get_server(int(server_id), include_actions=True)
        if not server:
            ui.notify('Server not found', type='negative')
            return
        
        connection_tested = {'value': True}  # Already exists, so initial test passed
        
        with ui.dialog() as edit_dialog, ui.card().classes('w-[600px]'):
            ui.label(f'Edit Server: {server["name"]}').classes('text-h6 font-bold mb-4')
            
            with ui.row().classes('w-full gap-4'):
                with ui.column().classes('w-1/2 gap-2'):
                    name_input = ui.input('Server Name', value=server['name']) \
                        .classes('w-full').props('outlined')
                    ip_input = ui.input('IP Address', value=server['ip_address']) \
                        .classes('w-full').props('outlined')
                    port_input = ui.number('SSH Port', value=server['port'], min=1, max=65535) \
                        .classes('w-full').props('outlined')
                
                with ui.column().classes('w-1/2 gap-2'):
                    username_input = ui.input('SSH Username', value=server['username']) \
                        .classes('w-full').props('outlined')
                    ssh_key_input = ui.input('SSH Key Path', value=server['ssh_key_path']) \
                        .classes('w-full').props('outlined')
                    description_input = ui.textarea('Description', 
                                                   value=server.get('description') or '') \
                        .classes('w-full').props('outlined')
            
            # Connection test section
            with ui.card().classes('w-full bg-blue-grey-1 mt-2'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.column().classes('gap-1'):
                        ui.label('Connection Test').classes('text-subtitle2 font-bold')
                        connection_status = ui.label('✓ Previously tested (click to retest)') \
                            .classes('text-caption text-positive')
                    test_btn = ui.button('Test Connection', icon='wifi_tethering', 
                                        on_click=lambda: handle_test()).props('outline color=primary')
            
            def handle_test():
                if not ip_input.value or not username_input.value or not ssh_key_input.value:
                    ui.notify('Please fill in IP, username, and SSH key path first', type='warning')
                    return
                
                connection_status.text = 'Testing...'
                connection_status.classes('text-caption text-orange')
                
                success = test_connection(
                    ip_input.value,
                    port_input.value or 22,
                    username_input.value,
                    ssh_key_input.value,
                    test_btn
                )
                
                if success:
                    connection_tested['value'] = True
                    connection_status.text = '✓ Connection successful'
                    connection_status.classes('text-caption text-positive font-bold')
                else:
                    connection_tested['value'] = False
                    connection_status.text = '✗ Connection failed'
                    connection_status.classes('text-caption text-negative')
            
            # Actions selection
            ui.separator().classes('my-4')
            ui.label('Allowed Actions').classes('text-subtitle2 font-bold mb-2')
            
            current_action_ids = [action['id'] for action in server.get('allowed_actions', [])]
            actions_select = ui.select(
                action_options,
                label='Actions',
                multiple=True,
                value=current_action_ids
            ).classes('w-full').props('outlined use-chips')
            
            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('Update Server', icon='save', on_click=lambda: handle_update()).props('color=primary')
                ui.button('Cancel', on_click=edit_dialog.close).props('outline')
            
            def handle_update():
                if not connection_tested['value']:
                    ui.notify('Please test the connection before updating the server', type='warning')
                    return
                
                success = server_manager.update_server(
                    server_id=server['id'],
                    name=name_input.value,
                    ip_address=ip_input.value,
                    port=int(port_input.value or 22),
                    username=username_input.value,
                    ssh_key_path=ssh_key_input.value,
                    description=description_input.value or None
                )
                
                if success:
                    # Update actions - remove old and add new
                    selected_actions = actions_select.value if isinstance(actions_select.value, list) else (
                        [actions_select.value] if actions_select.value else []
                    )
                    
                    if set(current_action_ids) != set(selected_actions):
                        server_manager.detach_all_actions(server['id'])
                        if selected_actions:
                            server_manager.attach_actions(server['id'], selected_actions)
                    
                    ui.notify('Server updated successfully!', type='positive')
                    edit_dialog.close()
                    refresh_servers()
                else:
                    ui.notify('Failed to update server', type='negative')
        
        edit_dialog.open()
    
    def show_actions_dialog(server_id):
        server = server_manager.get_server(int(server_id), include_actions=True)
        if not server:
            ui.notify('Server not found', type='negative')
            return
        
        with ui.dialog() as actions_dialog, ui.card().classes('w-[800px]'):
            ui.label(f'Manage Actions: {server["name"]}').classes('text-h6 font-bold mb-4')
            ui.label(f'IP: {server["ip_address"]}:{server["port"]}').classes('text-caption text-grey-7 mb-4')
            
            current_actions = server.get('allowed_actions', [])
            
            if not current_actions:
                with ui.card().classes('w-full bg-grey-2'):
                    ui.label('No actions configured for this server').classes('text-body2 text-grey-7')
            else:
                # Group actions by type
                cmd_execute = [a for a in current_actions if a['action_type'] == 'command_execute']
                cmd_get = [a for a in current_actions if a['action_type'] == 'command_get']
                http_actions = [a for a in current_actions if a['action_type'] == 'http']
                
                if cmd_execute:
                    ui.label('Execute Commands (Modify Server)').classes('text-subtitle2 font-bold text-orange mt-2')
                    with ui.card().classes('w-full bg-orange-1'):
                        for action in cmd_execute:
                            with ui.row().classes('w-full items-center justify-between mb-2'):
                                with ui.column().classes('gap-1'):
                                    ui.label(action['action_name']).classes('text-body2 font-bold')
                                    ui.label(action['description']).classes('text-caption text-grey-7')
                                
                                with ui.row().classes('gap-2'):
                                    auto_toggle = ui.switch('Auto', value=action.get('automatic', False))
                                    auto_toggle.on_value_change(
                                        lambda e, aid=action['id']: server_manager.set_action_automatic(
                                            server_id, aid, e.value
                                        )
                                    )
                                    ui.button(icon='remove_circle', 
                                            on_click=lambda aid=action['id']: remove_action(aid)).props(
                                        'flat dense round color=negative size=sm'
                                    ).tooltip('Remove action')
                
                if cmd_get:
                    ui.label('Get Information (Safe/Read-only)').classes('text-subtitle2 font-bold text-positive mt-4')
                    with ui.card().classes('w-full bg-green-1'):
                        for action in cmd_get:
                            with ui.row().classes('w-full items-center justify-between mb-2'):
                                with ui.column().classes('gap-1'):
                                    ui.label(action['action_name']).classes('text-body2 font-bold')
                                    ui.label(action['description']).classes('text-caption text-grey-7')
                                
                                with ui.row().classes('gap-2'):
                                    auto_toggle = ui.switch('Auto', value=action.get('automatic', False))
                                    auto_toggle.on_value_change(
                                        lambda e, aid=action['id']: server_manager.set_action_automatic(
                                            server_id, aid, e.value
                                        )
                                    )
                                    ui.button(icon='remove_circle', 
                                            on_click=lambda aid=action['id']: remove_action(aid)).props(
                                        'flat dense round color=negative size=sm'
                                    ).tooltip('Remove action')
                
                if http_actions:
                    ui.label('HTTP Requests').classes('text-subtitle2 font-bold text-primary mt-4')
                    with ui.card().classes('w-full bg-blue-1'):
                        for action in http_actions:
                            with ui.row().classes('w-full items-center justify-between mb-2'):
                                with ui.column().classes('gap-1'):
                                    ui.label(action['action_name']).classes('text-body2 font-bold')
                                    ui.label(action['description']).classes('text-caption text-grey-7')
                                
                                with ui.row().classes('gap-2'):
                                    auto_toggle = ui.switch('Auto', value=action.get('automatic', False))
                                    auto_toggle.on_value_change(
                                        lambda e, aid=action['id']: server_manager.set_action_automatic(
                                            server_id, aid, e.value
                                        )
                                    )
                                    ui.button(icon='remove_circle', 
                                            on_click=lambda aid=action['id']: remove_action(aid)).props(
                                        'flat dense round color=negative size=sm'
                                    ).tooltip('Remove action')
            
            def remove_action(action_id):
                if server_manager.detach_action(server_id, action_id):
                    ui.notify('Action removed', type='positive')
                    actions_dialog.close()
                    show_actions_dialog(server_id)  # Reopen to refresh
            
            ui.separator().classes('my-4')
            ui.button('Close', on_click=actions_dialog.close).props('color=primary')
        
        actions_dialog.open()
    
    def confirm_delete(server_name, server_id):
        with ui.dialog() as delete_dialog, ui.card():
            ui.label(f'Delete Server: {server_name}?').classes('text-h6 font-bold mb-4')
            ui.label('This will remove the server and all associated action configurations.') \
                .classes('text-body2 text-red mb-4')
            
            with ui.row().classes('gap-2'):
                ui.button('Delete', on_click=lambda: handle_delete(server_id, delete_dialog)) \
                    .props('color=negative')
                ui.button('Cancel', on_click=delete_dialog.close).props('outline')
        
        delete_dialog.open()
    
    def handle_delete(server_id, dialog):
        success = server_manager.delete_server(server_id)
        if success:
            ui.notify('Server deleted successfully!', type='positive')
            dialog.close()
            refresh_servers()
        else:
            ui.notify('Failed to delete server', type='negative')
    
    # Main content
    with ui.column().classes('w-full p-6 gap-4'):
        # Header section with statistics
        with ui.row().classes('w-full justify-between items-center'):
            with ui.column().classes('gap-1'):
                ui.label('Server Management').classes('text-h4 font-bold text-primary')
                servers_list = server_manager.get_all_servers()
                ui.label(f'Total Servers: {len(servers_list)}').classes('text-body2 text-grey-7')
            
            with ui.row().classes('gap-2'):
                ui.button('Refresh', icon='refresh', on_click=refresh_servers) \
                    .props('outline color=primary')
                ui.button('Add Server', icon='dns', on_click=show_create_dialog) \
                    .props('color=primary')
                ui.button('Back to Home', icon='home', on_click=lambda: ui.navigate.to('/')) \
                    .props('color=primary')
        
        # Servers table
        with ui.card().classes('w-full'):
            columns = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True, 'align': 'left'},
                {'name': 'name', 'label': 'Server Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                {'name': 'ip_address', 'label': 'IP Address', 'field': 'ip_address', 'sortable': True, 'align': 'left'},
                {'name': 'port', 'label': 'Port', 'field': 'port', 'sortable': True, 'align': 'center'},
                {'name': 'username', 'label': 'Username', 'field': 'username', 'sortable': True, 'align': 'left'},
                {'name': 'actions_count', 'label': 'Actions', 'field': 'actions_count', 'align': 'center'},
                {'name': 'description', 'label': 'Description', 'field': 'description', 'align': 'left'},
                {'name': 'created_at', 'label': 'Created At', 'field': 'created_at', 'sortable': True, 'align': 'left'},
                {'name': 'actions_btn', 'label': 'Actions', 'field': 'actions_btn', 'align': 'center'},
            ]
            
            def get_rows(servers=servers_list):
                rows = []
                for server in servers:
                    actions_count = len(server.get('allowed_actions', []))
                    created_text = server['created_at'].strftime('%Y-%m-%d %H:%M') if server.get('created_at') else 'N/A'
                    
                    rows.append({
                        'id': server['id'],
                        'name': server['name'],
                        'ip_address': server['ip_address'],
                        'port': server['port'],
                        'username': server['username'],
                        'actions_count': f'{actions_count} configured',
                        'description': server.get('description') or '-',
                        'created_at': created_text
                    })
                return rows
            
            servers_table = ui.table(
                columns=columns,
                rows=get_rows(),
                row_key='id',
                pagination={'rowsPerPage': 10, 'sortBy': 'id', 'descending': False}
            ).classes('w-full')
            
            # Add action buttons in table
            servers_table.add_slot('body-cell-actions_btn', '''
                <q-td :props="props">
                    <q-btn flat dense round icon="edit" color="primary" size="sm" @click="$parent.$emit('edit', props.row)">
                        <q-tooltip>Edit Server</q-tooltip>
                    </q-btn>
                    <q-btn flat dense round icon="settings" color="secondary" size="sm" @click="$parent.$emit('manage', props.row)">
                        <q-tooltip>Manage Actions</q-tooltip>
                    </q-btn>
                    <q-btn flat dense round icon="delete" color="negative" size="sm" @click="$parent.$emit('delete', props.row)">
                        <q-tooltip>Delete Server</q-tooltip>
                    </q-btn>
                </q-td>
            ''')
            
            # Handle table events
            servers_table.on('edit', lambda e: show_edit_dialog(e.args.get('id')))
            servers_table.on('manage', lambda e: show_actions_dialog(e.args.get('id')))
            servers_table.on('delete', lambda e: confirm_delete(e.args.get('name'), e.args.get('id')))
        
        # Actions overview section
        with ui.card().classes('w-full mt-6 shadow-lg'):
            with ui.row().classes('w-full justify-between items-center mb-6 pb-4 border-b'):
                with ui.column().classes('gap-1'):
                    ui.label('Available Actions Overview').classes('text-h5 font-bold text-primary')
                    ui.label(f'Total of {len(available_actions)} predefined actions available') \
                        .classes('text-body2 text-grey-6')
                ui.icon('bolt').classes('text-5xl text-primary opacity-20')
            
            # Group actions by type
            cmd_execute = [a for a in available_actions if a['action_type'] == 'command_execute']
            cmd_get = [a for a in available_actions if a['action_type'] == 'command_get']
            http_actions = [a for a in available_actions if a['action_type'] == 'http']
            
            with ui.row().classes('w-full gap-4'):
                # Execute commands card
                with ui.card().classes('w-1/3 bg-orange-1 border-l-4 border-orange'):
                    ui.label('Execute Commands').classes('text-subtitle1 font-bold text-orange-9')
                    ui.label(f'{len(cmd_execute)} actions').classes('text-h5 font-bold text-orange-9')
                    ui.label('Modify server state').classes('text-caption text-grey-7')
                
                # Get commands card
                with ui.card().classes('w-1/3 bg-green-1 border-l-4 border-green'):
                    ui.label('Get Information').classes('text-subtitle1 font-bold text-green-9')
                    ui.label(f'{len(cmd_get)} actions').classes('text-h5 font-bold text-green-9')
                    ui.label('Read-only operations').classes('text-caption text-grey-7')
                
                # HTTP requests card
                with ui.card().classes('w-1/3 bg-blue-1 border-l-4 border-blue'):
                    ui.label('HTTP Requests').classes('text-subtitle1 font-bold text-blue-9')
                    ui.label(f'{len(http_actions)} actions').classes('text-h5 font-bold text-blue-9')
                    ui.label('API integrations').classes('text-caption text-grey-7')
