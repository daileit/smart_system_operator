"""
Dashboard page for Smart System Operator.
Real-time server monitoring with live metrics and AI insights.
"""

from nicegui import ui
from .shared import APP_TITLE, APP_LOGO_PATH, user_session, db_client, redis_client, openai_client
from servers import ServerManager
import json
from datetime import datetime


@ui.page('/dashboard')
def dashboard_page():
    """Main dashboard with servers list, live metrics, and AI chat."""
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
    
    # Initialize managers
    server_manager = ServerManager(db_client) if db_client else None
    
    # State
    selected_server_id = {'value': None}
    
    # UI Components storage
    server_cards = {}
    metric_charts = {}
    ai_messages = []
    
    def get_server_metrics(server_id: int):
        """Get latest metrics for a server from Redis."""
        if not redis_client:
            return None
        
        key = f"server_metrics:{server_id}"
        metrics_list = redis_client.get_json_list(key)
        
        if metrics_list and len(metrics_list) > 0:
            return metrics_list[0]  # Most recent
        return None
    
    def parse_metric_value(output: str, metric_type: str):
        """Parse metric output to extract numeric value."""
        try:
            if metric_type == 'cpu':
                # Extract percentage from CPU output
                if '%' in output:
                    return float(output.strip().replace('%', ''))
            elif metric_type == 'memory':
                # Extract percentage from memory output
                if '(' in output and '%' in output:
                    percent_str = output.split('(')[1].split('%')[0]
                    return float(percent_str)
            elif metric_type == 'load':
                # Extract 1-min load average
                parts = output.split()
                if len(parts) > 2:
                    return float(parts[2].rstrip(','))
        except:
            pass
        return 0.0
    
    def get_ai_recommendations(server_id: int):
        """Get AI recommendations for a server from execution_logs."""
        if not db_client:
            return []
        
        logs = db_client.execute_query(
            """
            SELECT ai_reasoning, execution_details, executed_at, status
            FROM execution_logs
            WHERE server_id = %s AND execution_type = 'recommended'
            ORDER BY executed_at DESC
            LIMIT 10
            """,
            (server_id,)
        )
        
        return logs or []
    
    def select_server(server_id: int):
        """Handle server selection."""
        selected_server_id['value'] = server_id
        
        # Update server card highlights
        for sid, card in server_cards.items():
            if sid == server_id:
                card.classes('bg-blue-100 border-2 border-blue-500', remove='bg-white')
            else:
                card.classes('bg-white', remove='bg-blue-100 border-2 border-blue-500')
        
        # Update metrics
        update_metrics_panel(server_id)
        
        # Update AI chat
        update_ai_panel(server_id)
    
    def update_metrics_panel(server_id: int):
        """Update metrics panel with latest data."""
        metrics_container.clear()
        
        with metrics_container:
            # Get server info
            server = server_manager.get_server(server_id) if server_manager else None
            if not server:
                ui.label('Server not found').classes('text-red-500')
                return
            
            # Header with gradient background
            with ui.card().classes('w-full p-4 mb-4 shadow-lg bg-gradient-to-r from-blue-500 to-blue-600'):
                with ui.row().classes('w-full justify-between items-center'):
                    with ui.column().classes('gap-1'):
                        ui.label(f"{server['name']}").classes('text-h5 font-bold text-white')
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('location_on', size='xs').classes('text-white')
                            ui.label(f"{server['ip_address']}:{server['port']}").classes('text-body2 text-white')
                    ui.icon('dns', size='lg').classes('text-white opacity-30')
            
            # Get latest metrics
            metrics = get_server_metrics(server_id)
            
            if not metrics:
                with ui.card().classes('w-full p-6 border-2 border-dashed border-gray-300'):
                    with ui.column().classes('items-center gap-2'):
                        ui.icon('hourglass_empty', size='lg').classes('text-gray-400')
                        ui.label('No metrics available yet').classes('text-gray-600 font-bold')
                        ui.label('Waiting for metrics crawler...').classes('text-caption text-gray-400')
                        ui.spinner(size='lg', color='primary')
                return
            
            # Parse metrics
            data = metrics.get('data', {})
            timestamp = metrics.get('timestamp', 'Unknown')
            
            # CPU Usage
            cpu_data = data.get('get_cpu_usage', {})
            cpu_value = parse_metric_value(cpu_data.get('output', '0%'), 'cpu') if 'output' in cpu_data else 0.0
            
            with ui.card().classes('w-full p-4 mb-4 shadow-md hover:shadow-lg transition-shadow'):
                with ui.row().classes('w-full items-center gap-2 mb-2'):
                    ui.icon('memory', size='sm').classes('text-blue-600')
                    ui.label('CPU Usage').classes('text-h6 font-bold')
                with ui.row().classes('w-full items-center gap-4'):
                    ui.linear_progress(cpu_value / 100).props(f'size=25px color={"red" if cpu_value > 80 else "orange" if cpu_value > 60 else "green"}').classes('flex-grow')
                    ui.label(f'{cpu_value:.1f}%').classes('text-h4 font-bold min-w-[80px]')
            
            # Memory Usage
            memory_data = data.get('get_memory_usage', {})
            memory_value = parse_metric_value(memory_data.get('output', '0%'), 'memory') if 'output' in memory_data else 0.0
            
            with ui.card().classes('w-full p-4 mb-4 shadow-md hover:shadow-lg transition-shadow'):
                with ui.row().classes('w-full items-center gap-2 mb-2'):
                    ui.icon('storage', size='sm').classes('text-purple-600')
                    ui.label('Memory Usage').classes('text-h6 font-bold')
                with ui.row().classes('w-full items-center gap-4'):
                    ui.linear_progress(memory_value / 100).props(f'size=25px color={"red" if memory_value > 80 else "orange" if memory_value > 60 else "green"}').classes('flex-grow')
                    ui.label(f'{memory_value:.1f}%').classes('text-h4 font-bold min-w-[80px]')
            
            # System Load
            load_data = data.get('get_system_load', {})
            if 'output' in load_data:
                with ui.card().classes('w-full p-4 mb-4 shadow-md hover:shadow-lg transition-shadow'):
                    with ui.row().classes('w-full items-center gap-2 mb-2'):
                        ui.icon('speed', size='sm').classes('text-orange-600')
                        ui.label('System Load').classes('text-h6 font-bold')
                    ui.label(load_data['output']).classes('text-body1 font-mono bg-gray-100 p-2 rounded')
            
            # Disk Usage
            disk_data = data.get('get_disk_usage', {})
            if 'output' in disk_data:
                with ui.card().classes('w-full p-4 mb-4 shadow-md hover:shadow-lg transition-shadow'):
                    with ui.row().classes('w-full items-center gap-2 mb-2'):
                        ui.icon('folder', size='sm').classes('text-green-600')
                        ui.label('Disk Usage (/)').classes('text-h6 font-bold')
                    ui.label(disk_data['output']).classes('text-body2 font-mono whitespace-pre bg-gray-100 p-2 rounded')
            
            # Top Processes
            process_data = data.get('get_top_processes', {})
            if 'output' in process_data or 'parsed_processes' in process_data:
                with ui.card().classes('w-full p-4 mb-4 shadow-md hover:shadow-lg transition-shadow'):
                    with ui.row().classes('w-full items-center gap-2 mb-3'):
                        ui.icon('assessment', size='sm').classes('text-indigo-600')
                        ui.label('Top Processes (Resource Consumption)').classes('text-h6 font-bold')
                    
                    # Show parsed process data if available
                    if 'parsed_processes' in process_data and process_data['parsed_processes']:
                        # Create table header
                        with ui.row().classes('w-full gap-2 mb-2 text-caption font-bold bg-gray-100 p-2 rounded'):
                            ui.label('PID').classes('w-[80px]')
                            ui.label('CPU %').classes('w-[80px]')
                            ui.label('MEM %').classes('w-[80px]')
                            ui.label('Command').classes('flex-grow')
                        
                        # Process rows
                        with ui.scroll_area().classes('h-[180px]'):
                            for proc in process_data['parsed_processes']:
                                cpu_color = 'text-red-600' if proc['cpu_percent'] > 50 else 'text-orange-600' if proc['cpu_percent'] > 25 else 'text-green-600'
                                mem_color = 'text-red-600' if proc['mem_percent'] > 50 else 'text-orange-600' if proc['mem_percent'] > 25 else 'text-green-600'
                                
                                with ui.row().classes('w-full gap-2 mb-1 text-caption hover:bg-gray-50 p-1 rounded'):
                                    ui.label(proc['pid']).classes('w-[80px] font-mono')
                                    ui.label(f"{proc['cpu_percent']:.1f}%").classes(f'w-[80px] font-mono font-bold {cpu_color}')
                                    ui.label(f"{proc['mem_percent']:.1f}%").classes(f'w-[80px] font-mono font-bold {mem_color}')
                                    ui.label(proc['command'][:50] + '...' if len(proc['command']) > 50 else proc['command']).classes('flex-grow font-mono text-gray-700')
                    else:
                        # Fallback to raw output
                        with ui.scroll_area().classes('h-[200px]'):
                            ui.label(process_data.get('output', 'No data')).classes('text-caption font-mono whitespace-pre bg-gray-100 p-2 rounded')
            
            # Last updated footer
            with ui.row().classes('w-full justify-between items-center mt-4 p-2 bg-gray-100 rounded'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('schedule', size='xs').classes('text-gray-600')
                    ui.label(f'Last updated: {timestamp}').classes('text-caption text-gray-600')
                ui.badge('LIVE', color='green').classes('pulse')
    
    def update_ai_panel(server_id: int):
        """Update AI recommendations panel."""
        ai_container.clear()
        
        with ai_container:
            # Get server info
            server = server_manager.get_server(server_id) if server_manager else None
            if not server:
                ui.label('Server not found').classes('text-red-500')
                return
            
            # Header with AI branding
            with ui.card().classes('w-full p-4 mb-4 shadow-lg bg-gradient-to-r from-purple-500 to-indigo-600'):
                with ui.row().classes('w-full justify-between items-center'):
                    with ui.column().classes('gap-1'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('smart_toy', size='sm').classes('text-white')
                            ui.label('AI Recommendations').classes('text-h6 font-bold text-white')
                        ui.label(f'Analyzing {server["name"]}').classes('text-caption text-white')
                    ui.icon('auto_awesome', size='lg').classes('text-white opacity-30')
            
            # Get AI recommendations
            recommendations = get_ai_recommendations(server_id)
            
            if not recommendations:
                with ui.card().classes('w-full p-6 border-2 border-dashed border-purple-300 bg-purple-50'):
                    with ui.column().classes('items-center gap-2'):
                        ui.icon('psychology', size='lg').classes('text-purple-400')
                        ui.label('No AI recommendations yet').classes('text-gray-600 font-bold')
                        ui.label('AI analysis runs periodically...').classes('text-caption text-gray-400')
                        ui.spinner(size='lg', color='purple')
                return
            
            # Display recommendations as chat-like messages
            with ui.scroll_area().classes('w-full h-[calc(100vh-300px)]'):
                for idx, rec in enumerate(recommendations):
                    timestamp = rec['executed_at'].strftime('%Y-%m-%d %H:%M:%S') if rec.get('executed_at') else 'Unknown'
                    reasoning = rec.get('ai_reasoning', 'No reasoning provided')
                    status = rec.get('status', 'unknown')
                    
                    # Parse execution details
                    details = {}
                    try:
                        if rec.get('execution_details'):
                            details = json.loads(rec['execution_details']) if isinstance(rec['execution_details'], str) else rec['execution_details']
                    except:
                        pass
                    
                    action_name = details.get('action_name', 'Unknown action')
                    priority = details.get('priority', 5)
                    
                    # AI message card with enhanced styling
                    card_bg = 'bg-gradient-to-r from-blue-50 to-indigo-50' if idx == 0 else 'bg-blue-50'
                    border_class = 'border-l-4 border-blue-500' if idx == 0 else 'border-l-2 border-blue-300'
                    
                    with ui.card().classes(f'w-full p-4 mb-3 {card_bg} {border_class} shadow-md hover:shadow-lg transition-shadow'):
                        # Header row
                        with ui.row().classes('w-full justify-between items-start mb-2'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('lightbulb', size='xs').classes('text-yellow-600')
                                ui.label(action_name).classes('text-subtitle2 font-bold text-blue-900')
                            with ui.row().classes('items-center gap-2'):
                                # Priority badge
                                priority_color = 'red' if priority >= 8 else 'orange' if priority >= 5 else 'green'
                                ui.badge(f'P{priority}', color=priority_color).classes('px-2')
                                ui.label(timestamp).classes('text-caption text-gray-600')
                        
                        # Reasoning text
                        ui.label(reasoning).classes('text-body2 mb-2 whitespace-pre-wrap text-gray-700')
                        
                        # Status and confidence badges
                        with ui.row().classes('gap-2 items-center'):
                            status_color = {
                                'recommended': 'blue',
                                'success': 'green',
                                'failed': 'red',
                                'timeout': 'orange'
                            }.get(status, 'gray')
                            
                            ui.badge(status.upper(), color=status_color).classes('px-3')
                            
                            # Show confidence if available
                            confidence = details.get('confidence', 0)
                            if confidence:
                                confidence_color = 'green' if confidence > 0.7 else 'orange' if confidence > 0.4 else 'red'
                                ui.badge(f'Confidence: {confidence:.0%}', color=confidence_color).classes('px-3')
                        
                        # Show parameters if available
                        if details.get('parameters'):
                            with ui.expansion('⚙️ Parameters', icon='settings').classes('w-full mt-2 bg-white rounded'):
                                ui.json_editor({'content': {'json': details['parameters']}}).classes('w-full').props('read-only')
            
            # Footer with info
            with ui.row().classes('w-full justify-between items-center mt-4 p-2 bg-purple-100 rounded'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('info', size='xs').classes('text-purple-600')
                    ui.label(f'{len(recommendations)} recommendations found').classes('text-caption text-purple-800 font-bold')
                ui.badge('AI', color='purple').classes('px-3')
    
    def refresh_all():
        """Refresh all panels."""
        if selected_server_id['value']:
            update_metrics_panel(selected_server_id['value'])
            update_ai_panel(selected_server_id['value'])
        load_servers()
    
    def load_servers():
        """Load servers list."""
        servers_container.clear()
        
        with servers_container:
            if not server_manager:
                ui.label('Database not connected').classes('text-red-500')
                return
            
            servers = server_manager.get_all_servers(include_actions=False)
            
            if not servers:
                ui.label('No servers configured').classes('text-gray-500')
                return
            
            for server in servers:
                server_id = server['id']
                
                # Server card
                is_selected = server_id == selected_server_id['value']
                card = ui.card().classes('w-full p-3 mb-2 cursor-pointer hover:shadow-lg transition-shadow')
                card.classes('bg-blue-100 border-2 border-blue-500' if is_selected else 'bg-white')
                server_cards[server_id] = card
                
                with card:
                    card.on('click', lambda sid=server_id: select_server(sid))
                    
                    # Server name
                    ui.label(server['name']).classes('text-subtitle1 font-bold')
                    
                    # Server IP
                    ui.label(f"{server['ip_address']}:{server['port']}").classes('text-caption text-gray-600')
                    
                    # Get latest metrics for status indicator
                    metrics = get_server_metrics(server_id)
                    if metrics:
                        data = metrics.get('data', {})
                        cpu_data = data.get('get_cpu_usage', {})
                        
                        if 'output' in cpu_data:
                            cpu_value = parse_metric_value(cpu_data['output'], 'cpu')
                            status_color = 'red' if cpu_value > 80 else 'orange' if cpu_value > 60 else 'green'
                            with ui.row().classes('items-center gap-2 mt-2'):
                                ui.icon('circle', size='xs').classes(f'text-{status_color}-500')
                                ui.label(f'CPU: {cpu_value:.1f}%').classes('text-caption')
                        else:
                            ui.label('Waiting for metrics...').classes('text-caption text-gray-400')
                    else:
                        ui.label('No metrics yet').classes('text-caption text-gray-400')
    
    # Main Layout
    with ui.header().classes('items-center justify-between bg-primary text-white'):
        with ui.row().classes('items-center gap-4'):
            ui.image(APP_LOGO_PATH).classes('w-10 h-10')
            with ui.row().classes('items-center gap-2'):
                ui.icon('dashboard', size='md')
                ui.label(APP_TITLE).classes('text-h5 font-bold')
        
        with ui.row().classes('items-center gap-4'):
            ui.label(f'👤 {username}').classes('text-body2')
            with ui.button(icon='account_circle').props('flat round color=white'):
                with ui.menu():
                    ui.menu_item(f'{username}', lambda: None).props('disable')
                    ui.separator()
                    ui.menu_item('Home', lambda: ui.navigate.to('/'), icon='home')
                    ui.menu_item('Settings', lambda: ui.navigate.to('/settings'), icon='settings')
                    ui.menu_item('Logout', lambda: (user_session.clear(), ui.navigate.to('/login')), icon='logout')
    
    # Three-column layout
    with ui.row().classes('w-full h-[calc(100vh-64px)] gap-0'):
        # Left: Servers List
        with ui.column().classes('w-1/5 h-full border-r-2 border-gray-300 p-4 overflow-y-auto bg-gradient-to-b from-blue-50 to-white'):
            with ui.card().classes('w-full mb-4 shadow-md bg-white'):
                with ui.row().classes('w-full justify-between items-center p-2'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('dns', size='sm').classes('text-primary')
                        ui.label('Servers').classes('text-h6 font-bold text-primary')
                    with ui.row().classes('gap-1'):
                        ui.button(icon='refresh', on_click=refresh_all).props('flat dense round color=primary size=sm').tooltip('Refresh All')
                        ui.button(icon='add', on_click=lambda: ui.navigate.to('/servers')).props('flat dense round color=primary size=sm').tooltip('Manage Servers')
            
            servers_container = ui.column().classes('w-full gap-2')
        
        # Middle: Live Metrics
        with ui.column().classes('w-2/5 h-full p-4 overflow-y-auto bg-white'):
            # Header section for metrics panel
            with ui.card().classes('w-full mb-4 shadow-md bg-gradient-to-r from-green-50 to-blue-50'):
                with ui.row().classes('w-full justify-between items-center p-3'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('monitor_heart', size='sm').classes('text-green-600')
                        ui.label('Live Metrics').classes('text-h6 font-bold text-gray-800')
                    ui.badge('Real-time', color='green').classes('px-3 py-1')
            
            metrics_container = ui.column().classes('w-full')
            
            # Initial state
            with metrics_container:
                with ui.card().classes('w-full p-8 text-center bg-gray-50 border-2 border-dashed border-gray-300'):
                    ui.icon('monitor_heart', size='xl').classes('text-gray-400 mb-4')
                    ui.label('Select a server to view metrics').classes('text-h6 text-gray-500 mb-2')
                    ui.label('Choose a server from the list on the left').classes('text-caption text-gray-400')
        
        # Right: AI Recommendations
        with ui.column().classes('w-2/5 h-full border-l-2 border-gray-300 p-4 bg-gradient-to-b from-purple-50 to-white'):
            # Header section for AI panel
            with ui.card().classes('w-full mb-4 shadow-md bg-gradient-to-r from-purple-50 to-blue-50'):
                with ui.row().classes('w-full justify-between items-center p-3'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('smart_toy', size='sm').classes('text-purple-600')
                        ui.label('AI Insights').classes('text-h6 font-bold text-gray-800')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('auto_awesome', size='xs').classes('text-yellow-500')
                        ui.badge('AI Powered', color='purple').classes('px-3 py-1')
            
            ai_container = ui.column().classes('w-full')
            
            # Initial state
            with ai_container:
                with ui.card().classes('w-full p-8 text-center bg-gray-50 border-2 border-dashed border-gray-300'):
                    ui.icon('smart_toy', size='xl').classes('text-gray-400 mb-4')
                    ui.label('Select a server to view AI insights').classes('text-h6 text-gray-500 mb-2')
                    ui.label('AI recommendations will appear here').classes('text-caption text-gray-400')
    
    # Load servers on page load
    load_servers()
    
    # Auto-refresh timer (every 30 seconds)
    ui.timer(30.0, refresh_all).props('outline')
