"""
Reports page for Smart System Operator.
Analytics, charts, and export functionality for system insights.
"""

from nicegui import ui
from .shared import APP_TITLE, APP_LOGO_PATH, user_session, db_client
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json


@ui.page('/reports')
def reports_page():
    """Comprehensive reports with analytics, charts, and export options."""
    ui.page_title(f"{APP_TITLE} - Reports & Analytics")
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    
    # Add Chart.js for charting
    ui.add_head_html('''
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
        .chart-container {
            position: relative;
            height: 400px;
            width: 100%;
        }
        .report-card {
            transition: all 0.3s ease;
        }
        .report-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 20px rgba(0,0,0,0.15);
        }
        .metric-badge {
            animation: fadeInUp 0.5s ease-out;
        }
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    </style>
    ''')
    
    page_id = ui.context.client.page.path.lstrip('/')
    
    if not user_session.get('authenticated'):
        ui.navigate.to('/login')
        ui.notify('Unauthorized! Please log in to access reports', type='warning')
        return
    
    username = user_session.get('username')
    user_context = user_session.get('auth_user')
    
    if not user_context['permissions'].get(f'{page_id}', False):
        ui.navigate.to('/')
        ui.notify('Unauthorized!', type='warning')
        return
    
    if not db_client:
        with ui.column().classes('w-full h-screen items-center justify-center'):
            ui.icon('error', size='xl').classes('text-red-500')
            ui.label('Database connection unavailable').classes('text-h5 text-red-500')
        return
    
    # State management
    state = {
        'time_range': '7d',
        'selected_server': None,
        'selected_report': 'overview',
        'date_from': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        'date_to': datetime.now().strftime('%Y-%m-%d')
    }
    
    # Data fetching functions
    def get_servers_list():
        """Get all servers for filter."""
        result = db_client.execute_query("SELECT id, name FROM servers ORDER BY name")
        return result or []
    
    def get_overview_stats(date_from: str, date_to: str, server_id: Optional[int] = None):
        """Get high-level overview statistics."""
        server_filter = f"AND el.server_id = {server_id}" if server_id else ""
        
        # Total executions
        total_exec = db_client.fetch_one(
            f"""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                   AVG(execution_time) as avg_time
            FROM execution_logs el
            WHERE el.executed_at BETWEEN %s AND %s {server_filter}
            """,
            (date_from, date_to)
        ) or {}
        
        # AI Analysis stats
        ai_stats = db_client.fetch_one(
            f"""
            SELECT COUNT(*) as total_analysis,
                   AVG(confidence) as avg_confidence,
                   SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END) as low_risk,
                   SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END) as medium_risk,
                   SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) as high_risk
            FROM ai_analysis aa
            WHERE aa.analyzed_at BETWEEN %s AND %s {server_filter.replace('el.', 'aa.')}
            """,
            (date_from, date_to)
        ) or {}
        
        # Active servers
        active_servers = db_client.fetch_one(
            f"""
            SELECT COUNT(DISTINCT server_id) as count
            FROM execution_logs
            WHERE executed_at BETWEEN %s AND %s {server_filter}
            """,
            (date_from, date_to)
        ) or {}
        
        return {
            'executions': total_exec,
            'ai_analysis': ai_stats,
            'active_servers': active_servers.get('count', 0)
        }
    
    def get_execution_timeline(date_from: str, date_to: str, server_id: Optional[int] = None):
        """Get execution timeline data for chart."""
        server_filter = f"AND server_id = {server_id}" if server_id else ""
        
        result = db_client.execute_query(
            f"""
            SELECT DATE(executed_at) as date,
                   COUNT(*) as total,
                   SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM execution_logs
            WHERE executed_at BETWEEN %s AND %s {server_filter}
            GROUP BY DATE(executed_at)
            ORDER BY date
            """,
            (date_from, date_to)
        )
        return result or []
    
    def get_action_distribution(date_from: str, date_to: str, server_id: Optional[int] = None):
        """Get action distribution data."""
        server_filter = f"AND el.server_id = {server_id}" if server_id else ""
        
        result = db_client.execute_query(
            f"""
            SELECT a.action_name, a.action_type,
                   COUNT(*) as execution_count,
                   SUM(CASE WHEN el.status = 'success' THEN 1 ELSE 0 END) as success_count,
                   AVG(el.execution_time) as avg_time
            FROM execution_logs el
            JOIN actions a ON el.action_id = a.id
            WHERE el.executed_at BETWEEN %s AND %s {server_filter}
            GROUP BY a.id, a.action_name, a.action_type
            ORDER BY execution_count DESC
            LIMIT 15
            """,
            (date_from, date_to)
        )
        return result or []
    
    def get_server_performance(date_from: str, date_to: str):
        """Get server performance comparison."""
        result = db_client.execute_query(
            """
            SELECT s.name, s.id,
                   COUNT(el.id) as total_executions,
                   SUM(CASE WHEN el.status = 'success' THEN 1 ELSE 0 END) as success_count,
                   SUM(CASE WHEN el.status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                   AVG(el.execution_time) as avg_execution_time,
                   COUNT(DISTINCT aa.id) as ai_analysis_count
            FROM servers s
            LEFT JOIN execution_logs el ON s.id = el.server_id 
                AND el.executed_at BETWEEN %s AND %s
            LEFT JOIN ai_analysis aa ON s.id = aa.server_id 
                AND aa.analyzed_at BETWEEN %s AND %s
            GROUP BY s.id, s.name
            HAVING total_executions > 0
            ORDER BY total_executions DESC
            LIMIT 20
            """,
            (date_from, date_to, date_from, date_to)
        )
        return result or []
    
    def get_ai_insights(date_from: str, date_to: str, server_id: Optional[int] = None):
        """Get AI analysis insights."""
        server_filter = f"AND aa.server_id = {server_id}" if server_id else ""
        
        result = db_client.execute_query(
            f"""
            SELECT aa.id, aa.reasoning, aa.confidence, aa.risk_level,
                   aa.recommended_actions, aa.analyzed_at,
                   s.name as server_name,
                   COUNT(el.id) as actions_executed
            FROM ai_analysis aa
            JOIN servers s ON aa.server_id = s.id
            LEFT JOIN execution_logs el ON aa.id = el.analysis_id
            WHERE aa.analyzed_at BETWEEN %s AND %s {server_filter}
            GROUP BY aa.id, aa.reasoning, aa.confidence, aa.risk_level, 
                     aa.recommended_actions, aa.analyzed_at, s.name
            ORDER BY aa.analyzed_at DESC
            LIMIT 50
            """,
            (date_from, date_to)
        )
        return result or []
    
    def get_risk_timeline(date_from: str, date_to: str, server_id: Optional[int] = None):
        """Get risk level timeline."""
        server_filter = f"AND server_id = {server_id}" if server_id else ""
        
        result = db_client.execute_query(
            f"""
            SELECT DATE(analyzed_at) as date,
                   SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END) as low,
                   SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END) as medium,
                   SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) as high
            FROM ai_analysis
            WHERE analyzed_at BETWEEN %s AND %s {server_filter}
            GROUP BY DATE(analyzed_at)
            ORDER BY date
            """,
            (date_from, date_to)
        )
        return result or []
    
    def get_error_analysis(date_from: str, date_to: str, server_id: Optional[int] = None):
        """Get error analysis data."""
        server_filter = f"AND el.server_id = {server_id}" if server_id else ""
        
        result = db_client.execute_query(
            f"""
            SELECT el.error_message, a.action_name, s.name as server_name,
                   COUNT(*) as occurrence_count,
                   MAX(el.executed_at) as last_occurrence
            FROM execution_logs el
            JOIN actions a ON el.action_id = a.id
            JOIN servers s ON el.server_id = s.id
            WHERE el.status = 'failed' 
                AND el.executed_at BETWEEN %s AND %s 
                AND el.error_message IS NOT NULL {server_filter}
            GROUP BY el.error_message, a.action_name, s.name
            ORDER BY occurrence_count DESC
            LIMIT 20
            """,
            (date_from, date_to)
        )
        return result or []
    
    # Export functions
    def export_to_csv(data: List[Dict], filename: str):
        """Generate CSV export."""
        if not data:
            ui.notify('No data to export', type='warning')
            return
        
        import io
        import csv
        
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        csv_content = output.getvalue()
        ui.download(csv_content.encode(), filename)
        ui.notify(f'Exported {len(data)} rows to {filename}', type='positive')
    
    def export_to_json(data: Any, filename: str):
        """Generate JSON export."""
        if not data:
            ui.notify('No data to export', type='warning')
            return
        
        json_content = json.dumps(data, indent=2, default=str)
        ui.download(json_content.encode(), filename)
        ui.notify(f'Exported to {filename}', type='positive')
    
    # UI rendering functions
    def render_overview_report():
        """Render overview dashboard."""
        content_area.clear()
        
        with content_area:
            # Get data
            date_from = state['date_from']
            date_to = state['date_to']
            server_id = state['selected_server']
            
            stats = get_overview_stats(date_from, date_to, server_id)
            
            # Summary cards
            with ui.row().classes('w-full gap-4 mb-6'):
                # Executions card
                with ui.card().classes('flex-1 report-card'):
                    with ui.column().classes('p-4'):
                        ui.label('Total Executions').classes('text-caption text-gray-600')
                        ui.label(str(stats['executions'].get('total', 0))).classes('text-h3 font-bold text-blue-600 metric-badge')
                        with ui.row().classes('gap-4 mt-2'):
                            with ui.column():
                                ui.label('Success').classes('text-caption')
                                ui.label(str(stats['executions'].get('success', 0))).classes('text-body1 text-green-600 font-bold')
                            with ui.column():
                                ui.label('Failed').classes('text-caption')
                                ui.label(str(stats['executions'].get('failed', 0))).classes('text-body1 text-red-600 font-bold')
                
                # AI Analysis card
                with ui.card().classes('flex-1 report-card'):
                    with ui.column().classes('p-4'):
                        ui.label('AI Analyses').classes('text-caption text-gray-600')
                        ui.label(str(stats['ai_analysis'].get('total_analysis', 0))).classes('text-h3 font-bold text-purple-600 metric-badge')
                        with ui.row().classes('gap-2 mt-2'):
                            ui.badge(f"Low: {stats['ai_analysis'].get('low_risk', 0)}", color='green')
                            ui.badge(f"Med: {stats['ai_analysis'].get('medium_risk', 0)}", color='orange')
                            ui.badge(f"High: {stats['ai_analysis'].get('high_risk', 0)}", color='red')
                
                # Performance card
                with ui.card().classes('flex-1 report-card'):
                    with ui.column().classes('p-4'):
                        ui.label('Avg Execution Time').classes('text-caption text-gray-600')
                        avg_time = stats['executions'].get('avg_time', 0) or 0
                        ui.label(f'{avg_time:.2f}s').classes('text-h3 font-bold text-indigo-600 metric-badge')
                        ui.label(f'{stats["active_servers"]} Active Servers').classes('text-caption mt-2')
            
            # Charts row
            with ui.row().classes('w-full gap-4 mb-6'):
                # Execution timeline chart
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4 w-full'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label('Execution Timeline').classes('text-h6 font-bold')
                            ui.button(icon='download', on_click=lambda: export_to_csv(
                                get_execution_timeline(date_from, date_to, server_id),
                                f'execution_timeline_{datetime.now().strftime("%Y%m%d")}.csv'
                            )).props('flat dense').tooltip('Export to CSV')
                        
                        timeline_data = get_execution_timeline(date_from, date_to, server_id)
                        if timeline_data:
                            chart_html = ui.html()
                            canvas_id = f'timeline_chart_{id(chart_html)}'
                            
                            dates = [row['date'].strftime('%Y-%m-%d') for row in timeline_data]
                            success = [row['success'] for row in timeline_data]
                            failed = [row['failed'] for row in timeline_data]
                            
                            chart_html.content = f'''
                            <div class="chart-container">
                                <canvas id="{canvas_id}"></canvas>
                            </div>
                            <script>
                            (function() {{
                                const ctx = document.getElementById('{canvas_id}').getContext('2d');
                                new Chart(ctx, {{
                                    type: 'line',
                                    data: {{
                                        labels: {json.dumps(dates)},
                                        datasets: [{{
                                            label: 'Success',
                                            data: {json.dumps(success)},
                                            borderColor: 'rgb(34, 197, 94)',
                                            backgroundColor: 'rgba(34, 197, 94, 0.1)',
                                            tension: 0.4
                                        }}, {{
                                            label: 'Failed',
                                            data: {json.dumps(failed)},
                                            borderColor: 'rgb(239, 68, 68)',
                                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                            tension: 0.4
                                        }}]
                                    }},
                                    options: {{
                                        responsive: true,
                                        maintainAspectRatio: false,
                                        plugins: {{
                                            legend: {{ position: 'top' }},
                                            title: {{ display: false }}
                                        }},
                                        scales: {{
                                            y: {{ beginAtZero: true }}
                                        }}
                                    }}
                                }});
                            }})();
                            </script>
                            '''
                        else:
                            ui.label('No data available').classes('text-gray-500 text-center')
                
                # Risk timeline chart
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4 w-full'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label('Risk Level Timeline').classes('text-h6 font-bold')
                            ui.button(icon='download', on_click=lambda: export_to_csv(
                                get_risk_timeline(date_from, date_to, server_id),
                                f'risk_timeline_{datetime.now().strftime("%Y%m%d")}.csv'
                            )).props('flat dense').tooltip('Export to CSV')
                        
                        risk_data = get_risk_timeline(date_from, date_to, server_id)
                        if risk_data:
                            chart_html = ui.html()
                            canvas_id = f'risk_chart_{id(chart_html)}'
                            
                            dates = [row['date'].strftime('%Y-%m-%d') for row in risk_data]
                            low = [row['low'] for row in risk_data]
                            medium = [row['medium'] for row in risk_data]
                            high = [row['high'] for row in risk_data]
                            
                            chart_html.content = f'''
                            <div class="chart-container">
                                <canvas id="{canvas_id}"></canvas>
                            </div>
                            <script>
                            (function() {{
                                const ctx = document.getElementById('{canvas_id}').getContext('2d');
                                new Chart(ctx, {{
                                    type: 'bar',
                                    data: {{
                                        labels: {json.dumps(dates)},
                                        datasets: [{{
                                            label: 'Low Risk',
                                            data: {json.dumps(low)},
                                            backgroundColor: 'rgba(34, 197, 94, 0.8)'
                                        }}, {{
                                            label: 'Medium Risk',
                                            data: {json.dumps(medium)},
                                            backgroundColor: 'rgba(249, 115, 22, 0.8)'
                                        }}, {{
                                            label: 'High Risk',
                                            data: {json.dumps(high)},
                                            backgroundColor: 'rgba(239, 68, 68, 0.8)'
                                        }}]
                                    }},
                                    options: {{
                                        responsive: true,
                                        maintainAspectRatio: false,
                                        plugins: {{
                                            legend: {{ position: 'top' }}
                                        }},
                                        scales: {{
                                            x: {{ stacked: true }},
                                            y: {{ stacked: true, beginAtZero: true }}
                                        }}
                                    }}
                                }});
                            }})();
                            </script>
                            '''
                        else:
                            ui.label('No data available').classes('text-gray-500 text-center')
    
    def render_action_report():
        """Render action distribution report."""
        content_area.clear()
        
        with content_area:
            date_from = state['date_from']
            date_to = state['date_to']
            server_id = state['selected_server']
            
            ui.label('Action Distribution Analysis').classes('text-h5 font-bold mb-4')
            
            action_data = get_action_distribution(date_from, date_to, server_id)
            
            if not action_data:
                ui.label('No action data available for the selected period').classes('text-gray-500')
                return
            
            # Export buttons
            with ui.row().classes('mb-4 gap-2'):
                ui.button('Export CSV', icon='download', on_click=lambda: export_to_csv(
                    action_data,
                    f'action_distribution_{datetime.now().strftime("%Y%m%d")}.csv'
                )).props('color=primary')
                ui.button('Export JSON', icon='download', on_click=lambda: export_to_json(
                    action_data,
                    f'action_distribution_{datetime.now().strftime("%Y%m%d")}.json'
                )).props('color=secondary')
            
            # Charts
            with ui.row().classes('w-full gap-4 mb-6'):
                # Action type distribution pie chart
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4 w-full'):
                        ui.label('Action Type Distribution').classes('text-h6 font-bold mb-4')
                        
                        # Group by action type
                        type_counts = {}
                        for row in action_data:
                            action_type = row['action_type']
                            type_counts[action_type] = type_counts.get(action_type, 0) + row['execution_count']
                        
                        chart_html = ui.html()
                        canvas_id = f'type_pie_{id(chart_html)}'
                        
                        chart_html.content = f'''
                        <div class="chart-container">
                            <canvas id="{canvas_id}"></canvas>
                        </div>
                        <script>
                        (function() {{
                            const ctx = document.getElementById('{canvas_id}').getContext('2d');
                            new Chart(ctx, {{
                                type: 'doughnut',
                                data: {{
                                    labels: {json.dumps(list(type_counts.keys()))},
                                    datasets: [{{
                                        data: {json.dumps(list(type_counts.values()))},
                                        backgroundColor: [
                                            'rgba(59, 130, 246, 0.8)',
                                            'rgba(168, 85, 247, 0.8)',
                                            'rgba(34, 197, 94, 0.8)'
                                        ]
                                    }}]
                                }},
                                options: {{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {{
                                        legend: {{ position: 'right' }}
                                    }}
                                }}
                            }});
                        }})();
                        </script>
                        '''
                
                # Success rate chart
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4 w-full'):
                        ui.label('Action Success Rates').classes('text-h6 font-bold mb-4')
                        
                        chart_html = ui.html()
                        canvas_id = f'success_rate_{id(chart_html)}'
                        
                        action_names = [row['action_name'][:20] for row in action_data[:10]]
                        success_rates = [
                            (row['success_count'] / row['execution_count'] * 100) if row['execution_count'] > 0 else 0
                            for row in action_data[:10]
                        ]
                        
                        chart_html.content = f'''
                        <div class="chart-container">
                            <canvas id="{canvas_id}"></canvas>
                        </div>
                        <script>
                        (function() {{
                            const ctx = document.getElementById('{canvas_id}').getContext('2d');
                            new Chart(ctx, {{
                                type: 'bar',
                                data: {{
                                    labels: {json.dumps(action_names)},
                                    datasets: [{{
                                        label: 'Success Rate (%)',
                                        data: {json.dumps(success_rates)},
                                        backgroundColor: 'rgba(34, 197, 94, 0.8)',
                                        borderColor: 'rgba(34, 197, 94, 1)',
                                        borderWidth: 1
                                    }}]
                                }},
                                options: {{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    indexAxis: 'y',
                                    plugins: {{
                                        legend: {{ display: false }}
                                    }},
                                    scales: {{
                                        x: {{ beginAtZero: true, max: 100 }}
                                    }}
                                }}
                            }});
                        }})();
                        </script>
                        '''
            
            # Data table
            with ui.card().classes('w-full'):
                with ui.column().classes('p-4 w-full'):
                    ui.label('Top Actions by Execution Count').classes('text-h6 font-bold mb-4')
                    
                    columns = [
                        {'name': 'action_name', 'label': 'Action Name', 'field': 'action_name', 'align': 'left'},
                        {'name': 'action_type', 'label': 'Type', 'field': 'action_type', 'align': 'left'},
                        {'name': 'execution_count', 'label': 'Executions', 'field': 'execution_count', 'align': 'right'},
                        {'name': 'success_count', 'label': 'Success', 'field': 'success_count', 'align': 'right'},
                        {'name': 'success_rate', 'label': 'Success Rate', 'field': 'success_rate', 'align': 'right'},
                        {'name': 'avg_time', 'label': 'Avg Time (s)', 'field': 'avg_time', 'align': 'right'}
                    ]
                    
                    # Add success rate calculation
                    table_data = []
                    for row in action_data:
                        row_copy = dict(row)
                        row_copy['success_rate'] = f"{(row['success_count'] / row['execution_count'] * 100):.1f}%" if row['execution_count'] > 0 else '0%'
                        row_copy['avg_time'] = f"{row['avg_time']:.3f}" if row['avg_time'] else '0'
                        table_data.append(row_copy)
                    
                    ui.table(columns=columns, rows=table_data, row_key='action_name').classes('w-full')
    
    def render_server_report():
        """Render server performance report."""
        content_area.clear()
        
        with content_area:
            date_from = state['date_from']
            date_to = state['date_to']
            
            ui.label('Server Performance Comparison').classes('text-h5 font-bold mb-4')
            
            server_data = get_server_performance(date_from, date_to)
            
            if not server_data:
                ui.label('No server data available for the selected period').classes('text-gray-500')
                return
            
            # Export buttons
            with ui.row().classes('mb-4 gap-2'):
                ui.button('Export CSV', icon='download', on_click=lambda: export_to_csv(
                    server_data,
                    f'server_performance_{datetime.now().strftime("%Y%m%d")}.csv'
                )).props('color=primary')
            
            # Charts
            with ui.row().classes('w-full gap-4 mb-6'):
                # Total executions by server
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4 w-full'):
                        ui.label('Executions by Server').classes('text-h6 font-bold mb-4')
                        
                        chart_html = ui.html()
                        canvas_id = f'server_exec_{id(chart_html)}'
                        
                        server_names = [row['name'][:15] for row in server_data[:10]]
                        exec_counts = [row['total_executions'] for row in server_data[:10]]
                        
                        chart_html.content = f'''
                        <div class="chart-container">
                            <canvas id="{canvas_id}"></canvas>
                        </div>
                        <script>
                        (function() {{
                            const ctx = document.getElementById('{canvas_id}').getContext('2d');
                            new Chart(ctx, {{
                                type: 'bar',
                                data: {{
                                    labels: {json.dumps(server_names)},
                                    datasets: [{{
                                        label: 'Total Executions',
                                        data: {json.dumps(exec_counts)},
                                        backgroundColor: 'rgba(59, 130, 246, 0.8)'
                                    }}]
                                }},
                                options: {{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {{
                                        legend: {{ display: false }}
                                    }},
                                    scales: {{
                                        y: {{ beginAtZero: true }}
                                    }}
                                }}
                            }});
                        }})();
                        </script>
                        '''
                
                # Success vs Failed
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4 w-full'):
                        ui.label('Success vs Failed Executions').classes('text-h6 font-bold mb-4')
                        
                        chart_html = ui.html()
                        canvas_id = f'server_status_{id(chart_html)}'
                        
                        server_names = [row['name'][:15] for row in server_data[:10]]
                        success_counts = [row['success_count'] for row in server_data[:10]]
                        failed_counts = [row['failed_count'] for row in server_data[:10]]
                        
                        chart_html.content = f'''
                        <div class="chart-container">
                            <canvas id="{canvas_id}"></canvas>
                        </div>
                        <script>
                        (function() {{
                            const ctx = document.getElementById('{canvas_id}').getContext('2d');
                            new Chart(ctx, {{
                                type: 'bar',
                                data: {{
                                    labels: {json.dumps(server_names)},
                                    datasets: [{{
                                        label: 'Success',
                                        data: {json.dumps(success_counts)},
                                        backgroundColor: 'rgba(34, 197, 94, 0.8)'
                                    }}, {{
                                        label: 'Failed',
                                        data: {json.dumps(failed_counts)},
                                        backgroundColor: 'rgba(239, 68, 68, 0.8)'
                                    }}]
                                }},
                                options: {{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {{
                                        legend: {{ position: 'top' }}
                                    }},
                                    scales: {{
                                        x: {{ stacked: true }},
                                        y: {{ stacked: true, beginAtZero: true }}
                                    }}
                                }}
                            }});
                        }})();
                        </script>
                        '''
            
            # Performance table
            with ui.card().classes('w-full'):
                with ui.column().classes('p-4 w-full'):
                    ui.label('Server Performance Metrics').classes('text-h6 font-bold mb-4')
                    
                    columns = [
                        {'name': 'name', 'label': 'Server', 'field': 'name', 'align': 'left'},
                        {'name': 'total_executions', 'label': 'Total Exec', 'field': 'total_executions', 'align': 'right'},
                        {'name': 'success_rate', 'label': 'Success Rate', 'field': 'success_rate', 'align': 'right'},
                        {'name': 'avg_execution_time', 'label': 'Avg Time (s)', 'field': 'avg_execution_time', 'align': 'right'},
                        {'name': 'ai_analysis_count', 'label': 'AI Analyses', 'field': 'ai_analysis_count', 'align': 'right'}
                    ]
                    
                    table_data = []
                    for row in server_data:
                        row_copy = dict(row)
                        total = row['total_executions']
                        success = row['success_count']
                        row_copy['success_rate'] = f"{(success / total * 100):.1f}%" if total > 0 else '0%'
                        row_copy['avg_execution_time'] = f"{row['avg_execution_time']:.3f}" if row['avg_execution_time'] else '0'
                        table_data.append(row_copy)
                    
                    ui.table(columns=columns, rows=table_data, row_key='name').classes('w-full')
    
    def render_ai_report():
        """Render AI insights report."""
        content_area.clear()
        
        with content_area:
            date_from = state['date_from']
            date_to = state['date_to']
            server_id = state['selected_server']
            
            ui.label('AI Analysis Insights').classes('text-h5 font-bold mb-4')
            
            ai_data = get_ai_insights(date_from, date_to, server_id)
            
            if not ai_data:
                ui.label('No AI analysis data available for the selected period').classes('text-gray-500')
                return
            
            # Export button
            with ui.row().classes('mb-4 gap-2'):
                ui.button('Export CSV', icon='download', on_click=lambda: export_to_csv(
                    ai_data,
                    f'ai_insights_{datetime.now().strftime("%Y%m%d")}.csv'
                )).props('color=primary')
            
            # Summary cards
            total_analyses = len(ai_data)
            avg_confidence = sum(float(row['confidence']) for row in ai_data) / total_analyses if total_analyses > 0 else 0
            high_confidence = sum(1 for row in ai_data if float(row['confidence']) >= 0.8)
            
            with ui.row().classes('w-full gap-4 mb-6'):
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4'):
                        ui.label('Total Analyses').classes('text-caption text-gray-600')
                        ui.label(str(total_analyses)).classes('text-h4 font-bold text-purple-600')
                
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4'):
                        ui.label('Avg Confidence').classes('text-caption text-gray-600')
                        ui.label(f'{avg_confidence:.2%}').classes('text-h4 font-bold text-blue-600')
                
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4'):
                        ui.label('High Confidence (≥80%)').classes('text-caption text-gray-600')
                        ui.label(str(high_confidence)).classes('text-h4 font-bold text-green-600')
            
            # AI Analysis list
            with ui.card().classes('w-full'):
                with ui.column().classes('p-4 w-full'):
                    ui.label('Recent AI Analysis').classes('text-h6 font-bold mb-4')
                    
                    with ui.scroll_area().classes('h-[600px]'):
                        for idx, analysis in enumerate(ai_data[:20]):
                            with ui.card().classes('w-full mb-3 hover:shadow-lg transition-shadow'):
                                with ui.column().classes('p-3 w-full'):
                                    # Header
                                    with ui.row().classes('w-full justify-between items-start mb-2'):
                                        with ui.column().classes('gap-1'):
                                            ui.label(analysis['server_name']).classes('text-body1 font-bold')
                                            analyzed_at = analysis['analyzed_at']
                                            if isinstance(analyzed_at, datetime):
                                                time_str = analyzed_at.strftime('%Y-%m-%d %H:%M:%S')
                                            else:
                                                time_str = str(analyzed_at)
                                            ui.label(time_str).classes('text-caption text-gray-600')
                                        
                                        with ui.row().classes('gap-2'):
                                            # Risk badge
                                            risk_color = {'low': 'green', 'medium': 'orange', 'high': 'red'}
                                            ui.badge(analysis['risk_level'].upper(), 
                                                    color=risk_color.get(analysis['risk_level'], 'gray'))
                                            # Confidence badge
                                            conf_val = float(analysis['confidence'])
                                            conf_color = 'green' if conf_val >= 0.8 else 'orange' if conf_val >= 0.6 else 'red'
                                            ui.badge(f"{conf_val:.0%}", color=conf_color)
                                    
                                    # Reasoning
                                    with ui.expansion('View Analysis', icon='psychology').classes('w-full'):
                                        ui.label(analysis['reasoning']).classes('text-body2 whitespace-pre-wrap')
                                        
                                        # Actions executed
                                        if analysis['actions_executed'] > 0:
                                            ui.label(f"✓ {analysis['actions_executed']} actions executed").classes('text-caption text-green-600 mt-2')
    
    def render_error_report():
        """Render error analysis report."""
        content_area.clear()
        
        with content_area:
            date_from = state['date_from']
            date_to = state['date_to']
            server_id = state['selected_server']
            
            ui.label('Error Analysis').classes('text-h5 font-bold mb-4')
            
            error_data = get_error_analysis(date_from, date_to, server_id)
            
            if not error_data:
                ui.label('No errors found for the selected period 🎉').classes('text-green-600 text-h6')
                return
            
            # Export button
            with ui.row().classes('mb-4 gap-2'):
                ui.button('Export CSV', icon='download', on_click=lambda: export_to_csv(
                    error_data,
                    f'error_analysis_{datetime.now().strftime("%Y%m%d")}.csv'
                )).props('color=primary')
            
            # Error summary
            total_errors = sum(row['occurrence_count'] for row in error_data)
            unique_errors = len(error_data)
            
            with ui.row().classes('w-full gap-4 mb-6'):
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4'):
                        ui.label('Total Error Occurrences').classes('text-caption text-gray-600')
                        ui.label(str(total_errors)).classes('text-h4 font-bold text-red-600')
                
                with ui.card().classes('flex-1'):
                    with ui.column().classes('p-4'):
                        ui.label('Unique Error Types').classes('text-caption text-gray-600')
                        ui.label(str(unique_errors)).classes('text-h4 font-bold text-orange-600')
            
            # Top errors chart
            with ui.card().classes('w-full mb-6'):
                with ui.column().classes('p-4 w-full'):
                    ui.label('Top 10 Errors by Occurrence').classes('text-h6 font-bold mb-4')
                    
                    chart_html = ui.html()
                    canvas_id = f'error_chart_{id(chart_html)}'
                    
                    error_labels = [f"{row['action_name'][:20]} - {row['server_name'][:15]}" for row in error_data[:10]]
                    error_counts = [row['occurrence_count'] for row in error_data[:10]]
                    
                    chart_html.content = f'''
                    <div class="chart-container">
                        <canvas id="{canvas_id}"></canvas>
                    </div>
                    <script>
                    (function() {{
                        const ctx = document.getElementById('{canvas_id}').getContext('2d');
                        new Chart(ctx, {{
                            type: 'bar',
                            data: {{
                                labels: {json.dumps(error_labels)},
                                datasets: [{{
                                    label: 'Occurrences',
                                    data: {json.dumps(error_counts)},
                                    backgroundColor: 'rgba(239, 68, 68, 0.8)'
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                indexAxis: 'y',
                                plugins: {{
                                    legend: {{ display: false }}
                                }},
                                scales: {{
                                    x: {{ beginAtZero: true }}
                                }}
                            }}
                        }});
                    }})();
                    </script>
                    '''
            
            # Error details table
            with ui.card().classes('w-full'):
                with ui.column().classes('p-4 w-full'):
                    ui.label('Error Details').classes('text-h6 font-bold mb-4')
                    
                    with ui.scroll_area().classes('h-[400px]'):
                        for idx, error in enumerate(error_data):
                            with ui.card().classes('w-full mb-3 bg-red-50'):
                                with ui.column().classes('p-3 w-full'):
                                    with ui.row().classes('w-full justify-between items-start'):
                                        with ui.column().classes('gap-1 flex-1'):
                                            ui.label(f"Action: {error['action_name']}").classes('text-body1 font-bold')
                                            ui.label(f"Server: {error['server_name']}").classes('text-body2 text-gray-700')
                                            ui.label(f"Error: {error['error_message']}").classes('text-body2 text-red-700 mt-1')
                                        
                                        with ui.column().classes('items-end gap-1'):
                                            ui.badge(f"{error['occurrence_count']} times", color='red')
                                            last_occ = error['last_occurrence']
                                            if isinstance(last_occ, datetime):
                                                time_str = last_occ.strftime('%Y-%m-%d %H:%M')
                                            else:
                                                time_str = str(last_occ)
                                            ui.label(f"Last: {time_str}").classes('text-caption text-gray-600')
    
    def update_date_range():
        """Update date range based on quick selection."""
        time_range = state['time_range']
        today = datetime.now()
        
        if time_range == '24h':
            state['date_from'] = (today - timedelta(days=1)).strftime('%Y-%m-%d')
        elif time_range == '7d':
            state['date_from'] = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        elif time_range == '30d':
            state['date_from'] = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        elif time_range == '90d':
            state['date_from'] = (today - timedelta(days=90)).strftime('%Y-%m-%d')
        
        state['date_to'] = today.strftime('%Y-%m-%d')
        refresh_report()
    
    def refresh_report():
        """Refresh current report."""
        report_type = state['selected_report']
        
        if report_type == 'overview':
            render_overview_report()
        elif report_type == 'actions':
            render_action_report()
        elif report_type == 'servers':
            render_server_report()
        elif report_type == 'ai':
            render_ai_report()
        elif report_type == 'errors':
            render_error_report()
    
    # Main Layout
    with ui.header().classes('items-center justify-between bg-primary text-white'):
        with ui.row().classes('items-center gap-4'):
            ui.image(APP_LOGO_PATH).classes('w-10 h-10')
            with ui.row().classes('items-center gap-2'):
                ui.icon('assessment', size='md')
                ui.label(f'{APP_TITLE} - Reports').classes('text-h5 font-bold')
        
        with ui.row().classes('items-center gap-4'):
            ui.label(f'👤 {username}').classes('text-body2')
            with ui.button(icon='account_circle').props('flat round color=white'):
                with ui.menu():
                    ui.menu_item('Dashboard', on_click=lambda: ui.navigate.to('/dashboard'))
                    ui.menu_item('Servers', on_click=lambda: ui.navigate.to('/servers'))
                    ui.menu_item('Settings', on_click=lambda: ui.navigate.to('/settings'))
                    ui.menu_separator()
                    ui.menu_item('Logout', on_click=lambda: (user_session.clear(), ui.navigate.to('/login')))
    
    # Layout
    with ui.row().classes('w-full h-[calc(100vh-64px)] gap-0'):
        # Left sidebar - Report types
        with ui.column().classes('w-1/6 h-full border-r-2 border-gray-300 p-4 bg-gray-50'):
            ui.label('Report Types').classes('text-h6 font-bold mb-4')
            
            report_types = [
                {'id': 'overview', 'label': 'Overview', 'icon': 'dashboard'},
                {'id': 'actions', 'label': 'Actions', 'icon': 'play_circle'},
                {'id': 'servers', 'label': 'Servers', 'icon': 'dns'},
                {'id': 'ai', 'label': 'AI Insights', 'icon': 'psychology'},
                {'id': 'errors', 'label': 'Errors', 'icon': 'error'}
            ]
            
            for report in report_types:
                ui.button(
                    report['label'],
                    icon=report['icon'],
                    on_click=lambda r=report: (
                        state.update({'selected_report': r['id']}),
                        refresh_report()
                    )
                ).props('flat align=left color=primary').classes('w-full justify-start mb-2')
        
        # Main content area
        with ui.column().classes('flex-1 h-full p-6 overflow-y-auto bg-white'):
            # Filters panel
            with ui.card().classes('w-full mb-6 bg-gradient-to-r from-blue-50 to-purple-50'):
                with ui.column().classes('p-4 w-full'):
                    ui.label('Filters & Time Range').classes('text-h6 font-bold mb-3')
                    
                    with ui.row().classes('w-full gap-4 items-end'):
                        # Quick time range
                        with ui.column().classes('gap-1'):
                            ui.label('Quick Select').classes('text-caption')
                            ui.select(
                                ['24h', '7d', '30d', '90d'],
                                value=state['time_range'],
                                on_change=lambda e: (
                                    state.update({'time_range': e.value}),
                                    update_date_range()
                                )
                            ).props('dense outlined').classes('w-32')
                        
                        # Custom date range
                        with ui.column().classes('gap-1'):
                            ui.label('From Date').classes('text-caption')
                            ui.input(
                                value=state['date_from'],
                                on_change=lambda e: state.update({'date_from': e.value})
                            ).props('type=date dense outlined').classes('w-40')
                        
                        with ui.column().classes('gap-1'):
                            ui.label('To Date').classes('text-caption')
                            ui.input(
                                value=state['date_to'],
                                on_change=lambda e: state.update({'date_to': e.value})
                            ).props('type=date dense outlined').classes('w-40')
                        
                        # Server filter
                        servers = get_servers_list()
                        server_options = [{'label': 'All Servers', 'value': None}] + [
                            {'label': s['name'], 'value': s['id']} for s in servers
                        ]
                        
                        with ui.column().classes('gap-1'):
                            ui.label('Server').classes('text-caption')
                            ui.select(
                                options=server_options,
                                value=state['selected_server'],
                                on_change=lambda e: state.update({'selected_server': e.value})
                            ).props('dense outlined').classes('w-48')
                        
                        # Apply button
                        ui.button(
                            'Apply Filters',
                            icon='filter_alt',
                            on_click=refresh_report
                        ).props('color=primary')
                        
                        ui.button(
                            'Refresh',
                            icon='refresh',
                            on_click=refresh_report
                        ).props('flat color=primary')
            
            # Content area (will be populated by report renderers)
            content_area = ui.column().classes('w-full')
            
            # Initial render
            render_overview_report()
