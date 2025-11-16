## Deployment

### Environment Configuration

The application is configured using environment variables. All configuration is managed through `config.py` which supports grouped configurations.

#### Required Environment Variables

**MySQL Database:**
```bash
MYSQL_HOST=localhost          # Database host (default: localhost)
MYSQL_USER=task_user          # Database user (default: task_user)
MYSQL_PASSWORD=your_password  # Database password (required)
MYSQL_DATABASE=database       # Database name (default: database)
MYSQL_PORT=3306              # Database port (default: 3306)
```

**Redis Cache:**
```bash
REDIS_HOST=localhost     # Redis host (default: localhost)
REDIS_PORT=6379         # Redis port (default: 6379)
REDIS_PASSWORD=         # Redis password (default: empty)
REDIS_DB=0             # Redis database number (default: 0)
```

**Application:**
```bash
APP_ENV=production          # Environment: development/production (default: development)
APP_DEBUG=false            # Debug mode (default: false)
APP_INIT_SECRET=secret123  # Admin initialization password (required, auto-generated if not set)
APP_LOG_LEVEL=INFO        # Log level: DEBUG/INFO/WARNING/ERROR (default: INFO)
APP_PORT=8080             # Application port (default: 8080)
APP_VERSION=1.0.0         # Application version
APP_DEPLOY_TIME=2025-11-15 # Deployment timestamp
```

### Docker Deployment

The application is containerized using Docker for easy deployment.

#### Build Docker Image

```bash
docker build -t smart-system-operator:latest .
```

#### Run with Docker

```bash
docker run -d \
  --name smart-system-operator \
  -p 8080:8080 \
  -e MYSQL_HOST=mysql_host \
  -e MYSQL_USER=admin \
  -e MYSQL_PASSWORD=secure_password \
  -e MYSQL_DATABASE=smart_system \
  -e APP_INIT_SECRET=your_secret_key \
  -e APP_ENV=production \
  -e APP_VERSION=1.0.0 \
  -e APP_DEPLOY_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  smart-system-operator:latest
```

#### Docker Compose Example

```yaml
version: '3.8'
services:
  app:
    image: smart-system-operator:latest
    ports:
      - "8080:8080"
    environment:
      MYSQL_HOST: mysql
      MYSQL_USER: admin
      MYSQL_PASSWORD: secure_password
      MYSQL_DATABASE: smart_system
      APP_INIT_SECRET: your_secret_key
      APP_ENV: production
      APP_LOG_LEVEL: INFO
    depends_on:
      - mysql
      - redis
  
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: smart_system
      MYSQL_USER: admin
      MYSQL_PASSWORD: secure_password
    volumes:
      - mysql_data:/var/lib/mysql
  
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass redis_password
    environment:
      REDIS_PASSWORD: redis_password

volumes:
  mysql_data:
```

### CI/CD Deployment

The project includes GitHub Actions workflow for automated Docker builds. Images are tagged with:
- Semantic version tags (e.g., `v1.0.0`)
- Git SHA for commit tracking
- `latest` tag for the most recent build

## Contributing

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tsufuwu/smart_system_operator.git
   cd smart_system_operator
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file or export variables:
   ```bash
   export MYSQL_HOST=localhost
   export MYSQL_USER=dev_user
   export MYSQL_PASSWORD=dev_password
   export MYSQL_DATABASE=smart_system_dev
   export APP_INIT_SECRET=dev_secret_key
   export APP_ENV=development
   export APP_DEBUG=true
   export APP_LOG_LEVEL=DEBUG
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the application:**
   Open your browser to `http://localhost:8080`

### Adding New Features

#### Creating a New Page

1. Create a new module in `webui/` (e.g., `analytics.py`):
   ```python
   from nicegui import ui
   from .shared import APP_TITLE, APP_LOGO_PATH, user_session
   
   @ui.page('/analytics')
   def analytics_page():
       if not user_session.get('authenticated'):
           ui.navigate.to('/login')
           return
       
       # Permission check
       auth_user = user_session.get('auth_user', {})
       permissions = auth_user.get('permissions', {})
       if not permissions.get('analytics', False):
           ui.navigate.to('/')
           ui.notify('Unauthorized!', type='warning')
           return
       
       # Your page content here
   ```

2. Export the page in `webui/__init__.py`:
   ```python
   from .analytics import analytics_page
   
   __all__ = [
       'login_page',
       'main_page',
       'dashboard_page',
       'users_page',
       'analytics_page',  # Add new page
   ]
   ```

3. Import in `app.py`:
   ```python
   from webui import login_page, main_page, dashboard_page, users_page, analytics_page
   ```

4. Update database permissions in `init/database/system.sql` if needed.

### Code Style Guidelines

- Follow PEP 8 Python style guide
- Use type hints where applicable
- Add docstrings to functions and classes
- Keep functions small and focused
- Use meaningful variable names
- Comment complex logic

### Testing

Before submitting a pull request:
1. Test all CRUD operations
2. Verify permission-based access control
3. Check authentication flow
4. Test with different user roles
5. Ensure no console errors in browser
6. Verify Docker build succeeds

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request with a clear description

### Project Structure

```
smart_system_operator/
├── app.py                 # Main application entry point
├── config.py             # Environment configuration manager
├── database.py           # Database client and operations
├── authen.py             # Authentication logic
├── user.py               # User management
├── init.py               # Database initialization
├── Dockerfile            # Docker containerization
├── requirements.txt      # Python dependencies
├── webui/               # Web UI modules
│   ├── __init__.py
│   ├── shared.py        # Shared resources
│   ├── login.py         # Login page
│   ├── main.py          # Main dashboard
│   ├── dashboard.py     # Dashboard details
│   └── users.py         # User management
├── assets/              # Static assets
│   ├── css/
│   └── img/
└── init/                # Initialization scripts
    └── database/
        └── system.sql   # Database schema
```

### Getting Help

- Check existing issues on GitHub
- Review the code documentation
- Ask questions in pull requests
- Contact maintainers for major changes

### License

This project follows the repository's license terms.