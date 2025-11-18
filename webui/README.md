# WebUI Module

Web UI pages for the Smart System Operator application, built with NiceGUI and organized into modular components.

## Quick Reference

### Static Assets

**CSS Animations:**
```python
ui.add_head_html('<link rel="stylesheet" href="/assets/css/animations.css">')
ui.card().classes('animate-fade-in')
ui.label('Live').classes('live-indicator')
```

**Chart.js Integration:**
```python
ui.add_head_html('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>')
ui.add_head_html('<script src="/assets/js/charts.js"></script>')

# Available functions: createRiskTimelineChart, createActionTypePieChart, 
# createSuccessRateChart, createServerExecutionsChart, createSuccessVsFailedChart, createTimeSeriesChart
```

**Asset Locations:** `/assets/css/`, `/assets/js/`, `/assets/img/`

## Structure

```
webui/
├── __init__.py           # Module exports
├── shared.py             # Shared resources (config, session, db)
├── login_page.py         # /login - Authentication
├── main_page.py          # / - Home dashboard
├── dashboard_page.py     # /dashboard - Real-time monitoring
├── servers_page.py       # /servers - Server management
├── users_page.py         # /users - User management
├── reports_page.py       # /reports - Analytics & reports
└── settings_page.py      # /settings - System configuration
```

## Pages

| Page | Route | Description | Permissions |
|------|-------|-------------|-------------|
| **Login** | `/login` | User authentication, first-run setup | Public |
| **Home** | `/` | Welcome dashboard, quick stats | All authenticated |
| **Dashboard** | `/dashboard` | Real-time server monitoring, AI recommendations | Operator+ |
| **Servers** | `/servers` | Server CRUD, SSH configuration | Administrator |
| **Users** | `/users` | User management, role assignment | Administrator |
| **Reports** | `/reports` | Analytics, charts, data export | Operator+ |
| **Settings** | `/settings` | System configuration | Administrator |

## Usage

Pages auto-register via `@ui.page()` decorators. Import in `app.py`:

```python
from webui import (login_page, main_page, dashboard_page, 
                   servers_page, users_page, reports_page, settings_page)
```

## Adding New Pages

1. Create `webui/my_page.py`
2. Use `@ui.page('/my-route')` decorator
3. Import shared resources from `shared.py`
4. Export from `webui/__init__.py`
5. Import in `app.py`

**Template:**
```python
from nicegui import ui
from .shared import APP_TITLE, user_session, has_permission

@ui.page('/my-route')
def my_page():
    if not user_session.get('username'):
        ui.navigate.to('/login')
        return
    
    if not has_permission('my_permission'):
        ui.label('Access Denied')
        return
    
    ui.page_title(APP_TITLE)
    # Page content
```

## Static Assets

### CSS Utilities (`/assets/css/animations.css`)

**Animations:** `fadeIn`, `fadeInUp`, `slideIn`, `pulse-glow`, `spin-slow`, `live-pulse`  
**Classes:** `animate-fade-in`, `animate-slide-in`, `live-indicator`, `metric-badge`

### JavaScript Charts (`/assets/js/charts.js`)

**Functions:**
- `createRiskTimelineChart(canvasId, dates, low, medium, high)` - Stacked bar
- `createActionTypePieChart(canvasId, labels, data)` - Doughnut chart
- `createSuccessRateChart(canvasId, labels, rates)` - Horizontal bar
- `createServerExecutionsChart(canvasId, labels, data)` - Bar chart
- `createSuccessVsFailedChart(canvasId, labels, success, failed)` - Stacked bar
- `createTimeSeriesChart(canvasId, dates, datasets)` - Line chart

**Example:**
```python
chart_html = ui.html()
chart_html.content = f'''
<div class="chart-container">
    <canvas id="myChart"></canvas>
</div>
<script>
    createActionTypePieChart('myChart', {json.dumps(labels)}, {json.dumps(data)});
</script>
'''
```

## Best Practices

- Use external CSS/JS assets instead of inline code
- Reference `shared.py` for common resources (avoid duplication)
- Implement permission checks at page entry
- Use consistent color schemes from `CHART_COLORS`
- Create unique canvas IDs: `f'chart_{id(element)}'`
- Wrap charts in `<div class="chart-container">`
- Export data as JSON: `json.dumps()` for JavaScript

## Reports Page

### Overview
Analytics dashboard at `/reports` with comprehensive data visualization and export capabilities.

### Report Types

1. **Overview** - Total executions, AI analysis, execution timelines, risk trends
2. **Action Distribution** - Action type breakdown, success rates, execution counts
3. **Server Performance** - Per-server metrics, success/failure analysis
4. **AI Insights** - AI recommendations, confidence scores, risk assessments
5. **Error Analysis** - Error occurrences, failure patterns, troubleshooting data

### Features

- **Time Filters:** 24h, 7d, 30d, 90d, custom date range
- **Server Filter:** All servers or specific server
- **Charts:** Line, bar, doughnut, stacked bar (Chart.js 4.4.0)
- **Export:** CSV and JSON formats
- **Permissions:** Operator+ (read-only for operators, full access for admins)

### Database Tables

- `execution_logs` - Execution history, status, timing
- `ai_analysis` - AI recommendations, confidence, risk levels
- `servers` - Server information
- `actions` - Action definitions

### Code Structure

```python
# Data fetching
get_overview_stats(), get_execution_timeline(), get_action_distribution()
get_server_performance(), get_ai_insights(), get_error_analysis()

# Export
export_to_csv(), export_to_json()

# Rendering
render_overview_report(), render_action_report(), render_server_report()
render_ai_report(), render_error_report()
```

## Troubleshooting

### Common Issues

**No data displayed:**
- Check time range and filters
- Verify database connection
- Ensure executions exist in selected period

**Charts not rendering:**
- Check browser console for JavaScript errors
- Verify Chart.js CDN accessibility
- Ensure modern browser with canvas support

**Export fails:**
- Confirm data exists for selected filters
- Check browser download permissions
- Try filtering to reduce dataset size

**Static assets not loading:**
- Verify `/assets` directory mounted in `app.py`
- Check browser console for 404 errors
- Clear browser cache
- Ensure CDN accessibility

---

**Version:** 1.1.0  
**Last Updated:** November 18, 2024
