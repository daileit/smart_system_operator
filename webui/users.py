"""
Users management page for Smart System Operator.
Provides CRUD operations for user management.
"""

from nicegui import ui
import jsonlog
import user as user_module
from .shared import APP_TITLE, APP_LOGO_PATH, user_session, db_client

logger = jsonlog.setup_logger("users_page")


@ui.page('/users')
def users_page():
    """Users management page with CRUD operations."""
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
    
    # Load all available roles
    available_roles = user_manager.get_all_roles()
    role_options = {role['role_id']: role['role_name'] for role in available_roles}
    
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
    
    def refresh_users():
        updated_list = user_manager.get_all_users()
        users_table.update_rows(rows=get_rows(updated_list), clear_selection = True)
    
    def show_create_dialog():
        with ui.dialog() as create_dialog, ui.card().classes('w-96'):
            ui.label('Create New User').classes('text-h6 font-bold mb-4')
            
            username_input = ui.input('Username', placeholder='Enter username').classes('w-full').props('outlined')
            email_input = ui.input('Email', placeholder='Enter email').classes('w-full').props('outlined')
            full_name_input = ui.input('Full Name', placeholder='Enter full name').classes('w-full').props('outlined')
            password_input = ui.input('Password', placeholder='Enter password', password=True).classes('w-full').props('outlined')
            
            # Role selection (multi-select)
            roles_select = ui.select(
                role_options,
                label='Roles',
                multiple=True,
                value=[2]  # Default to 'user' role
            ).classes('w-full').props('outlined use-chips')
            
            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('Create', on_click=lambda: handle_create()).props('color=primary')
                ui.button('Cancel', on_click=create_dialog.close).props('outline')
            
            def handle_create():
                if not username_input.value or not email_input.value or not password_input.value:
                    ui.notify('Please fill in all required fields', type='warning')
                    return
                
                # Ensure at least one role is selected
                selected_roles = roles_select.value if isinstance(roles_select.value, list) else [roles_select.value]
                if not selected_roles:
                    ui.notify('Please select at least one role', type='warning')
                    return
                
                user_id = user_manager.create_user(
                    username=username_input.value,
                    email=email_input.value,
                    password=password_input.value,
                    full_name=full_name_input.value or None,
                    status=1,
                    role_ids=selected_roles
                )
                
                if user_id:
                    ui.notify(f'User created successfully!', type='positive')
                    create_dialog.close()
                    refresh_users()
                else:
                    ui.notify('Failed to create user', type='negative')
        
        create_dialog.open()
    
    def show_edit_dialog(user_id):
        user_obj = user_manager.get_user_by_id(int(user_id))
        if not user_obj:
            ui.notify('User not found', type='negative')
            return        
        # Check if this is sysadmin - if so, prevent editing critical fields
        is_sysadmin = user_obj.username == 'sysadmin'
        
        with ui.dialog() as edit_dialog, ui.card().classes('w-96'):
            ui.label(f'Edit User: {user_obj.username}').classes('text-h6 font-bold mb-4')
            
            if is_sysadmin:
                ui.label('⚠️ System administrator account - username and email are locked').classes('text-caption text-orange mb-2')
            
            username_input = ui.input('Username', value=user_obj.username).classes('w-full').props('outlined' + (' disable' if is_sysadmin else ''))
            email_input = ui.input('Email', value=user_obj.email).classes('w-full').props('outlined' + (' disable' if is_sysadmin else ''))
            full_name_input = ui.input('Full Name', value=user_obj.full_name or '').classes('w-full').props('outlined')
            status_select = ui.select(
                {1: 'Active', 0: 'Inactive'},
                value=user_obj.status,
                label='Status'
            ).classes('w-full').props('outlined' + (' disable' if is_sysadmin else ''))
            
            # Role selection (multi-select)
            current_role_ids = [role['role_id'] for role in (user_obj.roles or [])]
            roles_select = ui.select(
                role_options,
                label='Roles',
                multiple=True,
                value=current_role_ids
            ).classes('w-full').props('outlined use-chips' + (' disable' if is_sysadmin else ''))
            
            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('Update', on_click=lambda: handle_update()).props('color=primary')
                ui.button('Cancel', on_click=edit_dialog.close).props('outline')
            
            def handle_update():
                # For sysadmin, only allow updating full_name
                if is_sysadmin:
                    success = user_manager.update_user(
                        user_id=user_obj.user_id,
                        full_name=full_name_input.value or None
                    )
                else:
                    # Ensure at least one role is selected
                    selected_roles = roles_select.value if isinstance(roles_select.value, list) else [roles_select.value]
                    if not selected_roles:
                        ui.notify('Please select at least one role', type='warning')
                        return
                    
                    success = user_manager.update_user(
                        user_id=user_obj.user_id,
                        username=username_input.value,
                        email=email_input.value,
                        full_name=full_name_input.value or None,
                        status=status_select.value
                    )
                    
                    # Update roles - remove old roles and assign new ones
                    if success and current_role_ids != selected_roles:
                        # Remove all current roles
                        user_manager.remove_roles(user_obj.user_id, current_role_ids)
                        # Assign new roles
                        user_manager.assign_roles(user_obj.user_id, selected_roles)
                
                if success:
                    ui.notify('User updated successfully!', type='positive')
                    edit_dialog.close()
                    refresh_users()
                else:
                    ui.notify('Failed to update user', type='negative')
        
        edit_dialog.open()
    
    def show_password_dialog(username, user_id):
        with ui.dialog() as password_dialog, ui.card().classes('w-96'):
            ui.label(f'Change Password: {username}').classes('text-h6 font-bold mb-4')
            
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
                
                success = user_manager.update_password(user_id, new_password_input.value)
                
                if success:
                    ui.notify('Password changed successfully!', type='positive')
                    password_dialog.close()
                else:
                    ui.notify('Failed to change password', type='negative')
        
        password_dialog.open()
    
    def confirm_delete(username, user_id):
        # Prevent deletion of sysadmin
        if username == 'sysadmin':
            ui.notify('Cannot delete system administrator account', type='warning')
            return
        
        with ui.dialog() as delete_dialog, ui.card():
            ui.label(f'Delete User: {username}?').classes('text-h6 font-bold mb-4')
            ui.label('This action cannot be undone.').classes('text-body2 text-red mb-4')
            
            with ui.row().classes('gap-2'):
                ui.button('Delete', on_click=lambda: handle_delete(user_id, delete_dialog)).props('color=negative')
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
                ui.label('User Management').classes('text-h4 font-bold text-primary')
                ui.label(f'Total Users: {user_manager.get_user_count()}').classes('text-body2 text-grey-7')
            
            with ui.row().classes('gap-2'):
                ui.button('Refresh', icon='refresh', on_click=refresh_users).props('outline color=primary')
                ui.button('Create User', icon='person_add', on_click=show_create_dialog).props('color=primary')
                ui.button('Back to Home', icon='home', on_click=lambda: ui.navigate.to('/')).props('color=primary')
        
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
            
            def get_rows(users=users_list):
                rows = []
                for user in users:
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
                        'created_at': created_text
                    })
                return rows
            
            users_table = ui.table(
                columns=columns,
                rows=get_rows(),
                row_key='user_id',
                pagination={'rowsPerPage': 10, 'sortBy': 'user_id', 'descending': False}
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
            users_table.on('edit', lambda e: show_edit_dialog(e.args.get('user_id')))
            users_table.on('password', lambda e: show_password_dialog(e.args.get('username'), e.args.get('user_id')))
            users_table.on('delete', lambda e: confirm_delete(e.args.get('username'), e.args.get('user_id')))
        
        # Role Permissions Matrix Section
        with ui.card().classes('w-full mt-6 shadow-lg'):
            with ui.row().classes('w-full justify-between items-center mb-6 pb-4 border-b'):
                with ui.column().classes('gap-1'):
                    ui.label('Role-Based Access Control (RBAC) Table').classes('text-h5 font-bold text-primary')
                    ui.label('View permissions for each role across all system pages').classes('text-body2 text-grey-6')
                ui.icon('admin_panel_settings').classes('text-5xl text-primary opacity-20')                

            # Get all pages and permissions for each role from UserManager
            all_pages = user_manager.get_all_pages()
            permissions_map = user_manager.get_role_permissions_matrix()
            
            # Create permissions table
            perm_columns = [
                {'name': 'page', 'label': 'Page', 'field': 'page', 'align': 'left', 'sortable': True}
            ]
            
            # Add a column for each role
            for role in available_roles:
                perm_columns.append({
                    'name': f"role_{role['role_id']}", 
                    'label': role['role_name'], 
                    'field': f"role_{role['role_id']}", 
                    'align': 'center'
                })
            
            def get_permissions_rows():
                rows = []
                for page in all_pages:
                    row = {
                        'page': f"{page['page_name']} ({page['page_id']})"
                    }
                    
                    # Add permission status for each role
                    for role in available_roles:
                        role_id = role['role_id']
                        has_access = permissions_map.get(role_id, {}).get(page['page_id'], False)
                        row[f"role_{role_id}"] = '✓ Allow' if has_access else '✗ Deny'
                    
                    rows.append(row)
                return rows
            
            permissions_table = ui.table(
                columns=perm_columns,
                rows=get_permissions_rows(),
                row_key='page',
                pagination={'rowsPerPage': 10}
            ).classes('w-full')
            
            # Add elegant styling with custom header and cell formatting
            permissions_table.props('flat bordered dense').classes('shadow-sm')
            
            # Style the header
            permissions_table.add_slot('header', '''
                <q-tr :props="props">
                    <q-th v-for="col in props.cols" :key="col.name" :props="props" 
                          class="bg-blue-grey-1 text-primary font-bold text-uppercase">
                        {{ col.label }}
                    </q-th>
                </q-tr>
            ''')
            
            # Style the permission cells with icons and colors
            permissions_table.add_slot('body-cell', '''
                <q-td :props="props">
                    <div v-if="props.col.name === 'page'" class="text-weight-medium">
                        {{ props.value }}
                    </div>
                    <div v-else-if="props.value && props.value.includes('Allow')" 
                         class="text-center">
                        <q-badge color="positive" class="q-pa-sm">
                            <q-icon name="check_circle" size="xs" class="q-mr-xs" />
                            <span class="text-weight-bold">Allow</span>
                        </q-badge>
                    </div>
                    <div v-else-if="props.value && props.value.includes('Deny')" 
                         class="text-center">
                        <q-badge color="negative" outline class="q-pa-sm">
                            <q-icon name="cancel" size="xs" class="q-mr-xs" />
                            <span>Deny</span>
                        </q-badge>
                    </div>
                    <div v-else>
                        {{ props.value }}
                    </div>
                </q-td>
            ''')
            
            # Add hover effect for rows
            permissions_table.props('row-hover')
