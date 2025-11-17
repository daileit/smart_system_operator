# WebUI Module

This folder contains all the web UI pages for the Smart System Operator application, organized into separate modules for better maintainability and structure.

## Structure

```
webui/
├── __init__.py         # Module initialization, exports all pages
├── shared.py           # Shared resources (session, config, constants)
├── login.py            # Login page (/login)
├── main.py             # Main dashboard page (/)
├── dashboard.py        # Dashboard detail page (/dashboard)
└── users.py            # User management page (/users)
```

## Modules

### `shared.py`
Common resources shared across all pages:
- `app_config` - Application configuration
- `APP_TITLE` - Application title
- `APP_LOGO_PATH` - Path to application logo
- `user_session` - Session dictionary for authentication
- `db_client` - Database client instance
- `system_status` - System status information

### `login.py`
Login page with authentication functionality:
- Route: `/login`
- Handles user authentication
- First-run initialization
- Redirects to main page on successful login

### `main.py`
Main dashboard home page:
- Route: `/`
- Displays welcome message and system information
- Navigation sidebar with permission-based menu items
- Quick stats and actions
- System information cards

### `dashboard.py`
Detailed dashboard page:
- Route: `/dashboard`
- Permission-based access control
- System monitoring and administrative tasks

### `users.py`
User management page with full CRUD operations:
- Route: `/users`
- Create, read, update, delete users
- Role assignment and management
- Password change functionality
- Sysadmin account protection
- Permission-based access control


## Usage

All pages are automatically registered when imported in `app.py`:

```python
from webui import login_page, main_page, dashboard_page, users_page
```

The `@ui.page()` decorators in each module register the routes with NiceGUI automatically.

## Adding New Pages

To add a new page:

1. Create a new file in `webui/` (e.g., `reports.py`)
2. Import necessary modules from `shared.py`
3. Define your page function with `@ui.page('/your-route')`
4. Add the import to `webui/__init__.py`
5. Import the page in `app.py`

Example:

```python
# webui/reports.py
from nicegui import ui
from .shared import APP_TITLE, APP_LOGO_PATH, user_session

@ui.page('/reports')
def reports_page():
    ui.page_title(APP_TITLE)
    # Your page content here
```

## Best Practices

- Keep pages focused on a single responsibility
- Use shared resources from `shared.py` instead of duplicating
- Implement permission checks at the start of each page
- Follow the existing pattern for headers and navigation
- Handle authentication state consistently


# Reports Page - Comprehensive Analytics & Insights

## Overview

The Reports page (`/reports`) provides comprehensive analytics, visualizations, and export capabilities for the Smart System Operator. It aggregates data from execution logs, AI analysis, and server metrics to deliver actionable insights.

## Features

### 📊 Report Types

#### 1. **Overview Dashboard**
- **High-level metrics:**
  - Total executions (success/failed breakdown)
  - AI analysis count with risk distribution
  - Average execution time
  - Active servers count
  
- **Charts:**
  - **Execution Timeline**: Line chart showing success/failed executions over time
  - **Risk Level Timeline**: Stacked bar chart showing AI risk assessments (low/medium/high)
  
- **Export**: CSV export for both timeline datasets

#### 2. **Action Distribution Report**
- **Metrics:**
  - Action type distribution (command_get vs command_execute)
  - Execution counts per action
  - Success rates per action
  - Average execution times
  
- **Charts:**
  - **Action Type Pie Chart**: Distribution of action types
  - **Success Rate Bar Chart**: Horizontal bar chart of top 10 actions by success rate
  
- **Data Table**: Detailed action statistics with sortable columns
- **Export**: CSV and JSON export

#### 3. **Server Performance Report**
- **Metrics:**
  - Total executions per server
  - Success vs failed comparison
  - Average execution time per server
  - AI analysis count per server
  
- **Charts:**
  - **Executions by Server**: Bar chart showing total activity
  - **Success vs Failed**: Stacked bar chart comparing outcomes
  
- **Performance Table**: Detailed server metrics with success rates
- **Export**: CSV export

#### 4. **AI Insights Report**
- **Summary Cards:**
  - Total analyses count
  - Average confidence score
  - High confidence analyses (≥80%)
  
- **Analysis List:**
  - Server-specific AI recommendations
  - Risk level badges
  - Confidence indicators
  - Expandable reasoning details
  - Executed actions count
  
- **Export**: CSV export of AI analysis data

#### 5. **Error Analysis Report**
- **Metrics:**
  - Total error occurrences
  - Unique error types
  
- **Charts:**
  - **Top 10 Errors**: Horizontal bar chart by occurrence count
  
- **Error Details:**
  - Error message breakdown
  - Action and server context
  - Occurrence frequency
  - Last occurrence timestamp
  
- **Export**: CSV export

### 🔍 Filters & Time Windows

#### Quick Time Range Selector
- **24h**: Last 24 hours
- **7d**: Last 7 days (default)
- **30d**: Last 30 days
- **90d**: Last 90 days

#### Custom Date Range
- **From Date**: Start date picker
- **To Date**: End date picker

#### Server Filter
- **All Servers**: View aggregated data across all servers
- **Specific Server**: Filter to a single server's data

#### Apply & Refresh
- **Apply Filters**: Refresh report with current filter settings
- **Refresh**: Reload data with existing filters

### 📥 Export Options

#### Supported Formats
1. **CSV**: Comma-separated values for spreadsheet analysis
2. **JSON**: Structured data for programmatic processing

#### Export Availability
- ✅ Overview: Execution timeline, Risk timeline
- ✅ Actions: Action distribution table
- ✅ Servers: Server performance table
- ✅ AI Insights: AI analysis records
- ✅ Errors: Error analysis details

### 📈 Chart Technology

- **Library**: Chart.js 4.4.0
- **Adapter**: Date-fns adapter for time-based charts
- **Chart Types**:
  - Line charts (timelines)
  - Bar charts (distributions, comparisons)
  - Horizontal bars (rankings)
  - Doughnut charts (type distributions)
  - Stacked bars (multi-category comparisons)

## Database Schema Utilization

### Tables Used

#### `execution_logs`
```sql
- id, server_id, action_id, analysis_id
- execution_result, status, error_message
- execution_time, executed_at
```

#### `ai_analysis`
```sql
- id, server_id, reasoning, confidence
- risk_level, requires_approval
- recommended_actions (JSON)
- analyzed_at
```

#### `servers`
```sql
- id, name, ip_address, port
- created_at, updated_at
```

#### `actions`
```sql
- id, action_name, action_type
- description, is_active
```

### Key Relationships

```
execution_logs.analysis_id → ai_analysis.id (1:N)
execution_logs.server_id → servers.id
execution_logs.action_id → actions.id
ai_analysis.server_id → servers.id
```

## SQL Query Examples

### Overview Statistics
```sql
SELECT COUNT(*) as total,
       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
       AVG(execution_time) as avg_time
FROM execution_logs
WHERE executed_at BETWEEN '2024-01-01' AND '2024-01-31'
```

### Action Distribution
```sql
SELECT a.action_name, a.action_type,
       COUNT(*) as execution_count,
       AVG(el.execution_time) as avg_time
FROM execution_logs el
JOIN actions a ON el.action_id = a.id
GROUP BY a.id
ORDER BY execution_count DESC
```

### Server Performance
```sql
SELECT s.name,
       COUNT(el.id) as total_executions,
       AVG(el.execution_time) as avg_time,
       COUNT(DISTINCT aa.id) as ai_analysis_count
FROM servers s
LEFT JOIN execution_logs el ON s.id = el.server_id
LEFT JOIN ai_analysis aa ON s.id = aa.server_id
GROUP BY s.id
```

### AI Insights with Executions
```sql
SELECT aa.*, s.name as server_name,
       COUNT(el.id) as actions_executed
FROM ai_analysis aa
JOIN servers s ON aa.server_id = s.id
LEFT JOIN execution_logs el ON aa.id = el.analysis_id
GROUP BY aa.id
ORDER BY aa.analyzed_at DESC
```

### Error Analysis
```sql
SELECT el.error_message, a.action_name, s.name,
       COUNT(*) as occurrence_count,
       MAX(el.executed_at) as last_occurrence
FROM execution_logs el
JOIN actions a ON el.action_id = a.id
JOIN servers s ON el.server_id = s.id
WHERE el.status = 'failed'
GROUP BY el.error_message, a.action_name, s.name
ORDER BY occurrence_count DESC
```

## UI/UX Features

### Responsive Design
- **Three-column layout**: Report types sidebar, filters, main content
- **Responsive charts**: Auto-adjust to container size
- **Scrollable content**: Handle large datasets gracefully

### Visual Feedback
- **Hover effects**: Cards lift on hover
- **Animated badges**: Metrics fade in on load
- **Color coding**:
  - 🟢 Success/Low risk: Green
  - 🟠 Medium risk/Warning: Orange
  - 🔴 Failed/High risk: Red
  - 🟣 AI-related: Purple
  - 🔵 Informational: Blue

### Interactive Elements
- **Expandable sections**: AI reasoning details
- **Sortable tables**: Click column headers (future enhancement)
- **Tooltips**: Export button hints
- **Date pickers**: Native HTML5 date inputs

## Performance Considerations

### Query Optimization
- Indexes on frequently queried columns:
  - `execution_logs(server_id, executed_at)`
  - `execution_logs(action_id, executed_at)`
  - `ai_analysis(server_id, analyzed_at)`
  
### Data Limiting
- **Timeline queries**: Grouped by date (reduces row count)
- **Top N queries**: LIMIT clauses on distributions (15-20 rows)
- **Recent data**: Time-based filtering on all queries

### Frontend Performance
- **Chart.js rendering**: Hardware-accelerated canvas
- **Lazy loading**: Data fetched on-demand per report type
- **Caching potential**: Add Redis caching for repeated queries (future)

## Access Control

### Permission Required
- **Page ID**: `reports`
- **Roles**: 
  - ✅ Administrator (full access)
  - ✅ Operator (read-only)
  - ❌ Viewer (no access by default)

### Navigation
- Available from main page left drawer
- Accessible via `/reports` URL
- Header navigation menu

## Future Enhancements

### Planned Features
1. **PDF Export**: Generate PDF reports with charts
2. **Scheduled Reports**: Email reports on schedule
3. **Custom Dashboards**: User-defined report layouts
4. **Real-time Updates**: WebSocket-based live data
5. **Drill-down**: Click chart elements to filter
6. **Comparison Mode**: Compare time periods side-by-side
7. **Alerts**: Set thresholds and get notifications
8. **Data Aggregation**: Hourly/daily/weekly rollups

### Technical Improvements
1. **Redis Caching**: Cache expensive queries for 60-300s
2. **Materialized Views**: Pre-aggregate common queries
3. **Lazy Chart Loading**: Render charts on scroll-into-view
4. **CSV Streaming**: Stream large exports instead of in-memory
5. **Query Pagination**: Handle 10K+ row datasets

## Code Structure

```
webui/reports_page.py
├── Data fetching functions
│   ├── get_servers_list()
│   ├── get_overview_stats()
│   ├── get_execution_timeline()
│   ├── get_action_distribution()
│   ├── get_server_performance()
│   ├── get_ai_insights()
│   ├── get_risk_timeline()
│   └── get_error_analysis()
│
├── Export functions
│   ├── export_to_csv()
│   └── export_to_json()
│
├── UI rendering functions
│   ├── render_overview_report()
│   ├── render_action_report()
│   ├── render_server_report()
│   ├── render_ai_report()
│   └── render_error_report()
│
└── Main layout
    ├── Header with user menu
    ├── Left sidebar (report types)
    ├── Filters panel
    └── Content area (dynamic)
```

## Usage Examples

### Scenario 1: Troubleshoot Server Issues
1. Navigate to `/reports`
2. Select "Server Performance" report
3. Set time range to "7d"
4. Identify servers with high failure rates
5. Switch to "Error Analysis" report
6. Filter to problematic server
7. Export error details for investigation

### Scenario 2: Evaluate AI Performance
1. Select "AI Insights" report
2. Set custom date range (last month)
3. Review average confidence scores
4. Check high-risk analyses
5. Verify executed actions count
6. Export for monthly review meeting

### Scenario 3: Action Usage Analysis
1. Select "Action Distribution" report
2. View action type pie chart
3. Identify most-used actions
4. Check success rates in table
5. Export CSV for capacity planning

## Troubleshooting

### No Data Displayed
- **Check time range**: Ensure executions exist in selected period
- **Verify filters**: "All Servers" vs specific server
- **Database connection**: Check system status indicator

### Charts Not Rendering
- **Browser console**: Look for JavaScript errors
- **Chart.js loaded**: Verify CDN accessibility
- **Canvas support**: Ensure modern browser

### Export Fails
- **Data availability**: Confirm data exists for export
- **Browser settings**: Check download permissions
- **Large datasets**: Try filtering to reduce size

## Best Practices

### For Administrators
1. Review reports weekly for trends
2. Export critical data monthly for archival
3. Monitor error patterns and address root causes
4. Use AI insights to optimize automation

### For Operators
1. Use overview dashboard for daily health checks
2. Filter to assigned servers for focused monitoring
3. Export error reports when escalating issues
4. Track AI recommendations vs manual actions

### For System Optimization
1. Identify frequently failing actions
2. Optimize high-execution-time actions
3. Review AI confidence trends
4. Balance automatic vs manual executions

## Support

For issues or feature requests related to the Reports page:
1. Check logs: `jsonlog` output for database queries
2. Database errors: Review `db_client` connection status
3. UI bugs: Browser console for JavaScript errors
4. Performance: Monitor query execution times in logs

---

**Version**: 1.0.0  
**Last Updated**: 2024-11-17  
**Author**: Smart System Operator Development Team
