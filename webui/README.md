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


