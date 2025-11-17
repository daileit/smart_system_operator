# Smart System Operator

> AI-powered server monitoring and automated operations platform with real-time metrics collection, intelligent analysis, and automated remediation.

[![Docker Build](https://img.shields.io/docker/automated/lanhlungbang/smart-system-operator)](https://hub.docker.com/r/lanhlungbang/smart-system-operator)
[![Docker Pulls](https://img.shields.io/docker/pulls/lanhlungbang/smart-system-operator)](https://hub.docker.com/r/lanhlungbang/smart-system-operator)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Usage](#usage)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🎯 Overview

Smart System Operator is an intelligent infrastructure management platform that combines real-time server monitoring, AI-driven analysis, and automated operations. It continuously monitors your servers, analyzes metrics using OpenAI's GPT models, and can automatically execute remediation actions based on configurable risk policies.

### Key Capabilities

- **Real-time Metrics Collection**: Automated collection of CPU, memory, disk, network, and process metrics via SSH
- **AI-Powered Analysis**: OpenAI GPT-4 analyzes server health and recommends actions with confidence scoring
- **Automated Remediation**: Configurable automatic execution of low/medium risk actions (service restarts, cleanup, etc.)
- **Comprehensive Reporting**: Interactive dashboards with charts, timelines, and exportable analytics
- **Role-Based Access Control**: Multi-user support with granular permissions
- **Action Management**: Extensible action system supporting SSH commands and HTTP requests
- **Audit Trail**: Complete logging of all actions, analyses, and executions

## ✨ Features

### Monitoring & Metrics
- ⚡ **Automated Metrics Crawling**: Configurable interval collection (default: 60s)
- 📊 **Real-time Dashboards**: Live server status with auto-refresh
- 🎯 **Custom Actions**: Define command-line or HTTP-based monitoring actions
- 💾 **Redis Caching**: 600s TTL cache for optimal database performance

### AI Analysis
- 🤖 **GPT-4 Integration**: Intelligent analysis of server metrics and trends
- 🎚️ **Risk Assessment**: Automatic classification (low/medium/high)
- 💡 **Actionable Recommendations**: Context-aware suggestions with reasoning
- 📈 **Confidence Scoring**: AI confidence levels for each recommendation
- 🔄 **Historical Context**: Considers past analyses for trend detection

### Automation
- ⚙️ **Automatic Execution**: Policy-based automatic action execution
- 🔐 **Approval Workflows**: High-risk actions require manual approval
- 🔧 **Service Management**: Restart, stop, start systemd services
- 🧹 **Maintenance Tasks**: Cleanup, process management, firewall rules
- 📝 **Execution Logging**: Complete audit trail with results and timing

### Reporting & Analytics
- 📉 **5 Report Types**: Overview, Actions, Servers, AI Insights, Errors
- 📈 **Interactive Charts**: Chart.js powered visualizations
- 📅 **Time Windows**: Quick select (24h, 7d, 30d, 90d) or custom ranges
- 🔍 **Server Filtering**: Global or per-server analytics
- 💾 **Export Options**: CSV and JSON export for all reports

### Security & Access
- 👥 **User Management**: Create and manage user accounts
- 🔑 **Role-Based Permissions**: Admin, Operator, Viewer roles
- 🔒 **SSH Key Authentication**: Secure server access
- 🔐 **Session Management**: Secure authentication with bcrypt
- 📋 **Page-level Permissions**: Granular access control

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web UI (NiceGUI)                        │
│  Login │ Dashboard │ Servers │ Reports │ Users │ Settings   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                   FastAPI Application                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Auth      │  │   API        │  │   Static     │       │
│  │   Manager   │  │   Endpoints  │  │   Assets     │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                   Core Services                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Metrics     │  │  AI          │  │  Action      │      │
│  │  Crawler     │─▶│  Analyzer    │─▶│  Executor    │      │
│  │  (60s)       │  │  (300s)      │  │  (On-demand) │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
┌─────────┴──────────────────┴──────────────────┴──────────────┐
│                   Data Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   MySQL      │  │   Redis      │  │   OpenAI     │       │
│  │   Database   │  │   Cache      │  │   API        │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└───────────────────────────────────────────────────────────────┘
          │                  │                  │
┌─────────┴──────────────────┴──────────────────┴──────────────┐
│                   Target Servers                              │
│  Server 1 (SSH)   Server 2 (SSH)   Server N (SSH)            │
└───────────────────────────────────────────────────────────────┘
```

## 📦 Prerequisites

### Required Services

1. **MySQL 8.0+** - Primary data storage
   - Tables: users, roles, servers, actions, execution_logs, ai_analysis
   - Minimum requirements: 1GB RAM, 10GB storage

2. **Redis 6.0+** - Caching layer
   - Used for: Metrics queue, action caching, server info caching
   - Minimum requirements: 512MB RAM

3. **OpenAI API** - AI analysis engine
   - Supported models: GPT-4, GPT-4-turbo, GPT-4o
   - API key required from https://platform.openai.com/
   - Estimated cost: ~$0.01-0.05 per analysis

### System Requirements

**Application Server:**
- OS: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+) or macOS
- Python: 3.11+
- RAM: 2GB minimum, 4GB recommended
- CPU: 2 cores minimum
- Storage: 5GB minimum
- Network: Outbound HTTPS (OpenAI API), MySQL, Redis, SSH to target servers

**Target Servers:**
- OS: Linux with SSH access
- SSH: Key-based authentication
- Python: Not required on targets
- Sudo: Required for system actions

## 🚀 Quick Start

### Using Docker (Recommended)

Pull the pre-built image from Docker Hub:

```bash
docker pull lanhlungbang/smart-system-operator:latest

docker run -d \
  --name smart-system-operator \
  -p 8080:8080 \
  -e MYSQL_HOST=your-mysql-host \
  -e MYSQL_USER=your-mysql-user \
  -e MYSQL_PASSWORD=your-mysql-password \
  -e MYSQL_DATABASE=smart_system \
  -e REDIS_HOST=your-redis-host \
  -e REDIS_PORT=6379 \
  -e OPENAI_API_KEY=your-openai-api-key \
  -e APP_INIT_SECRET=your-secret-key \
  lanhlungbang/smart-system-operator:latest
```

Access the application at `http://localhost:8080`

### Default Credentials

On first run, the system creates a default admin account:
- **Username**: `admin`
- **Password**: Value of `APP_INIT_SECRET` environment variable

⚠️ **Change the password immediately after first login!**

## 📥 Installation

### Method 1: Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    image: lanhlungbang/smart-system-operator:latest
    container_name: smart-system-operator
    ports:
      - "8080:8080"
    environment:
      # MySQL Configuration
      MYSQL_HOST: mysql
      MYSQL_USER: smartsys_user
      MYSQL_PASSWORD: secure_mysql_password
      MYSQL_DATABASE: smart_system
      MYSQL_PORT: 3306
      
      # Redis Configuration
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: secure_redis_password
      REDIS_DB: 0
      
      # OpenAI Configuration
      OPENAI_API_KEY: sk-your-openai-api-key-here
      OPENAI_BASE_URL: https://api.openai.com/v1
      OPENAI_MODEL: gpt-4o
      OPENAI_LANGUAGE: English
      
      # Application Configuration
      APP_ENV: production
      APP_DEBUG: false
      APP_INIT_SECRET: change-this-secret-key-now
      APP_LOG_LEVEL: INFO
      APP_PORT: 8080
      APP_CRAWLER_DELAY: 60
      APP_MODEL_DELAY: 300
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    networks:
      - smartsys-network

  mysql:
    image: mysql:8.0
    container_name: smartsys-mysql
    environment:
      MYSQL_ROOT_PASSWORD: secure_root_password
      MYSQL_DATABASE: smart_system
      MYSQL_USER: smartsys_user
      MYSQL_PASSWORD: secure_mysql_password
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - smartsys-network

  redis:
    image: redis:7-alpine
    container_name: smartsys-redis
    command: redis-server --requirepass secure_redis_password
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - smartsys-network

volumes:
  mysql_data:
    driver: local
  redis_data:
    driver: local

networks:
  smartsys-network:
    driver: bridge
```

Start the stack:

```bash
docker-compose up -d
```

Check logs:

```bash
docker-compose logs -f app
```

### Method 2: Manual Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tsufuwu/smart_system_operator.git
   cd smart_system_operator
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up MySQL database:**
   ```bash
   mysql -u root -p
   CREATE DATABASE smart_system;
   CREATE USER 'smartsys_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON smart_system.* TO 'smartsys_user'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

5. **Set up Redis:**
   ```bash
   # Install Redis (Ubuntu/Debian)
   sudo apt-get update
   sudo apt-get install redis-server
   sudo systemctl start redis
   sudo systemctl enable redis
   ```

6. **Configure environment:**
   ```bash
   export MYSQL_HOST=localhost
   export MYSQL_USER=smartsys_user
   export MYSQL_PASSWORD=your_password
   export MYSQL_DATABASE=smart_system
   export REDIS_HOST=localhost
   export REDIS_PORT=6379
   export OPENAI_API_KEY=sk-your-key-here
   export APP_INIT_SECRET=your-secret-key
   ```

7. **Run the application:**
   ```bash
   python app.py
   ```

8. **Access the application:**
   Open browser to `http://localhost:8080`

## ⚙️ Configuration

### Environment Variables Reference

#### MySQL Database (Required)

| Variable | Default | Description |
|----------|---------|-------------|
| `MYSQL_HOST` | `localhost` | MySQL server hostname or IP |
| `MYSQL_USER` | `task_user` | Database username |
| `MYSQL_PASSWORD` | *(none)* | Database password ⚠️ **Required** |
| `MYSQL_DATABASE` | `database` | Database name |
| `MYSQL_PORT` | `3306` | MySQL port |

#### Redis Cache (Required)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis server hostname or IP |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | *(empty)* | Redis authentication password |
| `REDIS_DB` | `0` | Redis database number (0-15) |

#### OpenAI API (Required for AI features)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(none)* | OpenAI API key ⚠️ **Required** |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API base URL (for proxy/custom endpoints) |
| `OPENAI_MODEL` | `gpt-4o` | Model to use (gpt-4, gpt-4-turbo, gpt-4o) |
| `OPENAI_LANGUAGE` | `Vietnamese` | Analysis language preference |

#### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment: `development` or `production` |
| `APP_DEBUG` | `false` | Enable debug mode (`true`/`false`) |
| `APP_INIT_SECRET` | *(auto-generated)* | Admin password & session secret ⚠️ **Set this!** |
| `APP_LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `APP_PORT` | `8080` | Application HTTP port |
| `APP_CRAWLER_DELAY` | `60` | Metrics collection interval (seconds) |
| `APP_MODEL_DELAY` | `300` | AI analysis interval (seconds) |

### Configuration Examples

**Development Environment:**
```bash
APP_ENV=development
APP_DEBUG=true
APP_LOG_LEVEL=DEBUG
MYSQL_HOST=localhost
REDIS_HOST=localhost
OPENAI_MODEL=gpt-4o
APP_CRAWLER_DELAY=30
APP_MODEL_DELAY=120
```

**Production Environment:**
```bash
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO
MYSQL_HOST=prod-mysql.example.com
REDIS_HOST=prod-redis.example.com
OPENAI_MODEL=gpt-4-turbo
APP_CRAWLER_DELAY=60
APP_MODEL_DELAY=300
```

## 🐳 Deployment

## 🐳 Deployment

### Docker Hub Registry

Pre-built images are automatically built and published to Docker Hub:

🐳 **Repository**: https://hub.docker.com/r/lanhlungbang/smart-system-operator

**Available Tags:**
- `latest` - Latest stable build from main branch
- `v1.x.x` - Semantic version tags
- `<git-sha>` - Specific commit builds

### Pull Pre-built Image

```bash
# Latest version
docker pull lanhlungbang/smart-system-operator:latest

# Specific version
docker pull lanhlungbang/smart-system-operator:v1.0.0

# Specific commit
docker pull lanhlungbang/smart-system-operator:abc1234
```

### Building Custom Image

If you need to customize the application:

```bash
# Clone repository
git clone https://github.com/tsufuwu/smart_system_operator.git
cd smart_system_operator

# Build image
docker build -t my-smart-system-operator:custom .

# Or with build args
docker build \
  --build-arg PYTHON_VERSION=3.13 \
  -t my-smart-system-operator:custom \
  .
```

### Docker Network Configuration

⚠️ **Important**: When running the application inside Docker, be aware of network binding:

**Problem**: By default, the application binds to `0.0.0.0:8080` which works fine, but you need to ensure proper network configuration.

**Solutions:**

1. **Using Host Network (Simple but less secure):**
   ```bash
   docker run -d \
     --network host \
     -e MYSQL_HOST=localhost \
     -e REDIS_HOST=localhost \
     lanhlungbang/smart-system-operator:latest
   ```
   Note: This gives the container full access to the host network.

2. **Using Bridge Network (Recommended):**
   ```bash
   # Create custom network
   docker network create smartsys-net
   
   # Run MySQL
   docker run -d \
     --name mysql \
     --network smartsys-net \
     -e MYSQL_ROOT_PASSWORD=rootpass \
     mysql:8.0
   
   # Run Redis
   docker run -d \
     --name redis \
     --network smartsys-net \
     redis:7-alpine
   
   # Run application
   docker run -d \
     --name smart-system-operator \
     --network smartsys-net \
     -p 8080:8080 \
     -e MYSQL_HOST=mysql \
     -e REDIS_HOST=redis \
     -e OPENAI_API_KEY=your-key \
     lanhlungbang/smart-system-operator:latest
   ```

3. **Accessing External Databases:**
   If MySQL/Redis are on the host machine:
   ```bash
   docker run -d \
     -p 8080:8080 \
     -e MYSQL_HOST=host.docker.internal \
     -e REDIS_HOST=host.docker.internal \
     lanhlungbang/smart-system-operator:latest
   ```
   
   On Linux, you may need to add `--add-host=host.docker.internal:host-gateway`

### Docker Compose Deployment (Recommended)

Use the complete stack provided in the installation section. This handles networking automatically.

### Kubernetes Deployment

Example Kubernetes manifests:

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: smart-system-operator
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: smart-system-operator
  template:
    metadata:
      labels:
        app: smart-system-operator
    spec:
      containers:
      - name: app
        image: lanhlungbang/smart-system-operator:latest
        ports:
        - containerPort: 8080
        env:
        - name: MYSQL_HOST
          value: "mysql-service"
        - name: MYSQL_USER
          valueFrom:
            secretKeyRef:
              name: mysql-credentials
              key: username
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-credentials
              key: password
        - name: REDIS_HOST
          value: "redis-service"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-credentials
              key: api-key
        - name: APP_INIT_SECRET
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: init-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: smart-system-operator
  namespace: monitoring
spec:
  selector:
    app: smart-system-operator
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

### CI/CD Pipeline

The project includes GitHub Actions for automated builds:

**.github/workflows/docker-build.yml** handles:
- Automated builds on push to main
- Tag-based versioning on git tags
- Multi-platform builds (amd64, arm64)
- Push to Docker Hub registry

To use in your fork:
1. Set GitHub secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
2. Push to main or create a version tag (`v1.0.0`)
3. Image builds automatically

### Environment-specific Deployments

**Development:**
```bash
docker run -d \
  -p 8080:8080 \
  -e APP_ENV=development \
  -e APP_DEBUG=true \
  -e APP_LOG_LEVEL=DEBUG \
  -e APP_CRAWLER_DELAY=30 \
  lanhlungbang/smart-system-operator:latest
```

**Staging:**
```bash
docker run -d \
  -p 8080:8080 \
  -e APP_ENV=staging \
  -e APP_LOG_LEVEL=INFO \
  -e OPENAI_MODEL=gpt-4o \
  lanhlungbang/smart-system-operator:latest
```

**Production:**
```bash
docker run -d \
  -p 8080:8080 \
  --restart unless-stopped \
  -e APP_ENV=production \
  -e APP_DEBUG=false \
  -e APP_LOG_LEVEL=WARNING \
  -e APP_CRAWLER_DELAY=60 \
  -e APP_MODEL_DELAY=300 \
  lanhlungbang/smart-system-operator:latest
```

## 📖 Usage

### Initial Setup

1. **First Login:**
   - Navigate to `http://your-server:8080`
   - Login with username `admin` and password from `APP_INIT_SECRET`
   - **Change password immediately** in Settings

2. **Add Servers:**
   - Go to **Servers** page
   - Click **Add Server**
   - Provide:
     - Name (friendly identifier)
     - IP address
     - SSH port (default: 22)
     - Username
     - SSH private key (paste full key including `-----BEGIN...-----`)

3. **Assign Actions:**
   - In server details, click **Manage Actions**
   - Enable monitoring actions (get_cpu_usage, get_memory_usage, etc.)
   - Enable execute actions if needed (restart_service, cleanup, etc.)
   - Set **Automatic** flag for low-risk actions you want auto-executed

4. **Configure Users:**
   - Go to **Users** page
   - Create operator/viewer accounts
   - Assign appropriate roles
   - Set page permissions

### Using the Dashboard

**Live Monitoring:**
- View real-time server metrics
- CPU, memory, disk, load averages
- AI recommendations appear automatically
- Click servers to see detailed metrics

**Reports & Analytics:**
- Navigate to **Reports** page
- Choose report type: Overview, Actions, Servers, AI Insights, Errors
- Filter by time range and server
- Export data as CSV or JSON

### Automation Workflow

1. **Metrics Crawler** (every 60s by default):
   - Connects to each server via SSH
   - Executes assigned "get" actions
   - Stores metrics in Redis queue
   - Logs all executions

2. **AI Analyzer** (every 300s by default):
   - Retrieves metrics from Redis
   - Sends to OpenAI with context
   - Receives analysis with risk level
   - Stores in database

3. **Auto-Execution** (triggered by AI):
   - If action has `automatic=true` flag
   - AND risk level is low/medium
   - Executes action automatically
   - Logs result with analysis reference

4. **Manual Execution**:
   - High-risk actions require approval
   - Admins can manually trigger any action
   - View execution history in Reports

### Action Management

**Pre-configured Actions:**

*Monitoring (command_get):*
- `get_cpu_usage` - Current CPU usage percentage
- `get_memory_usage` - Memory usage with breakdown
- `get_disk_usage` - Disk space usage
- `get_system_load` - Load averages
- `get_top_processes` - Top CPU/memory processes
- `get_service_status` - Systemd service status
- `get_failed_services` - Failed systemd services

*Execution (command_execute):*
- `restart_service` - Restart systemd service
- `stop_service` - Stop systemd service
- `start_service` - Start systemd service
- `reboot_system` - Reboot server (HIGH RISK)
- `kill_process` - Kill processes by name
- `cleanup_temp_files` - Clean /tmp directory
- `block_ip_firewalld` - Block IP with firewalld
- `unblock_ip_firewalld` - Unblock IP

**Creating Custom Actions:**

1. Go to **Settings** > **Actions**
2. Click **Create Action**
3. Fill in:
   - Action name (e.g., `check_nginx_status`)
   - Type: `command_get` or `command_execute`
   - Description
   - Command template: `systemctl status nginx`
   - Timeout (seconds)
4. Assign to servers

### Best Practices

**Security:**
- ✅ Use SSH key authentication (never passwords)
- ✅ Create dedicated SSH users with minimal privileges
- ✅ Use sudo for privileged operations
- ✅ Rotate API keys regularly
- ✅ Enable only necessary actions per server
- ✅ Set `automatic=false` for dangerous actions

**Performance:**
- ⚡ Keep crawler delay >= 30s to avoid overwhelming servers
- ⚡ Monitor Redis memory usage
- ⚡ Use MySQL indexes (auto-created by init scripts)
- ⚡ Clean old execution logs periodically
- ⚡ Scale horizontally with multiple app instances (shared DB/Redis)

**Reliability:**
- 🔄 Monitor application logs: `docker logs -f smart-system-operator`
- 🔄 Set up health check monitoring: `GET /api/health`
- 🔄 Backup MySQL database regularly
- 🔄 Use Redis persistence (AOF or RDB)
- 🔄 Configure automatic restarts: `--restart unless-stopped`

## 🛠️ Development

## 🛠️ Development

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tsufuwu/smart_system_operator.git
   cd smart_system_operator
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up development environment:**
   Create `.env` file:
   ```bash
   export MYSQL_HOST=localhost
   export MYSQL_USER=dev_user
   export MYSQL_PASSWORD=dev_password
   export MYSQL_DATABASE=smart_system_dev
   export REDIS_HOST=localhost
   export REDIS_PORT=6379
   export OPENAI_API_KEY=sk-your-dev-key
   export APP_INIT_SECRET=dev_secret_key
   export APP_ENV=development
   export APP_DEBUG=true
   export APP_LOG_LEVEL=DEBUG
   export APP_CRAWLER_DELAY=30
   export APP_MODEL_DELAY=120
   ```

5. **Run development server:**
   ```bash
   python app.py
   ```

6. **Access the application:**
   Open browser to `http://localhost:8080`

### Project Structure

```
smart_system_operator/
├── app.py                    # Main application entry point (FastAPI + NiceGUI)
├── config.py                 # Environment configuration manager
├── database.py               # MySQL client with connection pooling
├── redis_cache.py            # Redis client with JSON serialization
├── authen.py                 # Authentication logic (bcrypt)
├── user.py                   # User management operations
├── servers.py                # Server management operations
├── action.py                 # Action execution engine (SSH/HTTP)
├── openai_client.py          # OpenAI GPT integration
├── cron.py                   # Background schedulers (metrics, AI)
├── init.py                   # Database initialization
├── jsonlog.py                # Structured JSON logging
├── settings.py               # Application settings management
├── setting_module.py         # Settings CRUD operations
├── Dockerfile                # Container definition
├── requirements.txt          # Python dependencies
├── .dockerignore            # Docker build exclusions
├── .github/
│   └── workflows/
│       └── docker-build.yml # CI/CD pipeline
├── init/
│   └── database/            # SQL initialization scripts
│       ├── 0_system.sql     # Users, roles, permissions
│       ├── 1_fuction.sql    # Servers, actions, logs
│       └── 2_setting.sql    # Application settings
├── assets/                  # Static assets
│   ├── css/
│   │   └── style.css
│   └── img/
│       └── application-logo.png
└── webui/                   # Web UI modules (NiceGUI)
    ├── __init__.py          # Module exports
    ├── shared.py            # Shared resources & session
    ├── login_page.py        # Login & authentication
    ├── main_page.py         # Main dashboard
    ├── dashboard_page.py    # Live monitoring dashboard
    ├── servers_page.py      # Server management
    ├── users_page.py        # User management
    ├── settings_page.py     # Application settings
    └── reports_page.py      # Analytics & reporting
```

### Key Components

**Core Services:**
- `MetricsCrawler` (cron.py): Collects server metrics via SSH
- `AIAnalyzer` (cron.py): Analyzes metrics with OpenAI GPT
- `ActionManager` (action.py): Executes SSH commands/HTTP requests
- `ServerManager` (servers.py): Server CRUD operations
- `RedisClient` (redis_cache.py): Caching with datetime serialization

**Web UI:**
- Built with NiceGUI (FastAPI + Vue 3)
- Session-based authentication
- Role-based page permissions
- Real-time updates via timers
- Responsive design with Tailwind CSS

### Adding New Features

#### 1. Create a New Page

Create `webui/analytics_page.py`:
```python
from nicegui import ui
from .shared import APP_TITLE, APP_LOGO_PATH, user_session, db_client

@ui.page('/analytics')
def analytics_page():
    """Analytics page with custom visualizations."""
    ui.page_title(f"{APP_TITLE} - Analytics")
    ui.add_head_html(f'<link rel="icon" href="{APP_LOGO_PATH}">')
    
    # Authentication check
    if not user_session.get('authenticated'):
        ui.navigate.to('/login')
        ui.notify('Please log in', type='warning')
        return
    
    # Permission check
    user_context = user_session.get('auth_user')
    if not user_context['permissions'].get('analytics', False):
        ui.navigate.to('/')
        ui.notify('Unauthorized!', type='warning')
        return
    
    # Your page content here
    with ui.header().classes('bg-primary text-white'):
        ui.label('Analytics').classes('text-h5')
    
    with ui.column().classes('w-full p-4'):
        ui.label('Your custom content')
```

Export in `webui/__init__.py`:
```python
from .analytics_page import analytics_page

__all__ = [
    'login_page',
    'main_page',
    'dashboard_page',
    'users_page',
    'settings_page',
    'servers_page',
    'reports_page',
    'analytics_page',  # Add new page
]
```

Import in `app.py`:
```python
from webui import (
    login_page, main_page, dashboard_page, 
    users_page, settings_page, servers_page, 
    reports_page, analytics_page
)
```

Add database permission in `init/database/0_system.sql`:
```sql
INSERT IGNORE INTO pages (page_id, page_name, description) 
VALUES ('analytics', 'Analytics', 'Custom analytics page');
```

#### 2. Create a New Action Type

Add to `init/database/1_fuction.sql`:
```sql
INSERT IGNORE INTO actions (action_name, action_type, description) VALUES
('get_nginx_status', 'command_get', 'Check Nginx status and connections');

INSERT IGNORE INTO command_configs (action_id, command_template, timeout_seconds) VALUES
((SELECT id FROM actions WHERE action_name = 'get_nginx_status'), 
 'systemctl status nginx && ss -tuln | grep :80', 
 10);
```

#### 3. Add Custom Cron Job

In `cron.py`, add to `CronManager`:
```python
class CustomJob:
    def __init__(self, db_client, delay_seconds=600):
        self.db = db_client
        self.delay_seconds = delay_seconds
        self.running = False
        self.task = None
    
    async def _job_cycle(self):
        # Your custom logic
        pass
    
    async def _run_loop(self):
        while self.running:
            try:
                await self._job_cycle()
                await asyncio.sleep(self.delay_seconds)
            except Exception as e:
                logger.error(f"Custom job error: {e}")
    
    def start(self):
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._run_loop())
    
    def stop(self):
        if self.running:
            self.running = False
            if self.task:
                self.task.cancel()
```

Register in `CronManager.__init__()`:
```python
self.custom_job = CustomJob(self.db, delay_seconds=600)
```

Start in `CronManager.start_all()`:
```python
self.custom_job.start()
```

### Code Style Guidelines

- **PEP 8**: Follow Python style guide
- **Type Hints**: Use typing annotations
- **Docstrings**: Document all functions/classes
- **Error Handling**: Always use try-except with logging
- **SQL Queries**: Use parameterized queries (never string interpolation)
- **Async**: Use async/await for I/O operations
- **Logging**: Use `jsonlog` for structured logging

### Testing

**Manual Testing Checklist:**
- [ ] Login/logout works
- [ ] User creation and role assignment
- [ ] Server CRUD operations
- [ ] Action assignment and execution
- [ ] Metrics collection
- [ ] AI analysis triggered
- [ ] Reports generation and export
- [ ] Permission enforcement

**Database Testing:**
```bash
# Test connection
mysql -h localhost -u smartsys_user -p smart_system

# Check tables
SHOW TABLES;

# Test queries
SELECT * FROM execution_logs ORDER BY executed_at DESC LIMIT 10;
SELECT * FROM ai_analysis ORDER BY analyzed_at DESC LIMIT 10;
```

**Redis Testing:**
```bash
# Connect
redis-cli

# Check keys
KEYS *

# Check server metrics
GET server_metrics:1

# Check cache
GET cache:server_actions:1
```

### Debugging

**Enable Debug Logging:**
```bash
export APP_DEBUG=true
export APP_LOG_LEVEL=DEBUG
```

**View Logs:**
```bash
# Docker
docker logs -f smart-system-operator

# Local
tail -f logs/app.log  # If file logging enabled
```

**Common Issues:**

1. **Database connection failed:**
   - Check MYSQL_HOST, credentials
   - Verify MySQL is running: `mysql -h HOST -u USER -p`
   - Check firewall rules

2. **Redis connection failed:**
   - Check REDIS_HOST, port
   - Verify Redis is running: `redis-cli ping`
   - Check REDIS_PASSWORD if set

3. **OpenAI API errors:**
   - Verify OPENAI_API_KEY is valid
   - Check API usage limits
   - Test: `curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models`

4. **SSH connection failed:**
   - Verify SSH key format (include headers)
   - Test manually: `ssh -i key.pem user@host`
   - Check target server firewall

5. **Docker network issues:**
   - Use `host.docker.internal` for host services
   - Check Docker network: `docker network inspect bridge`
   - Verify container can reach services: `docker exec -it smart-system-operator ping mysql`

## 🐛 Troubleshooting

### Application Won't Start

**Symptom**: Container exits immediately

**Solutions:**
```bash
# Check logs
docker logs smart-system-operator

# Common causes:
# 1. Missing required env vars
docker run ... -e MYSQL_PASSWORD=pass -e OPENAI_API_KEY=key

# 2. Database not ready
# Use depends_on with healthcheck in docker-compose

# 3. Port already in use
docker run ... -p 8081:8080  # Use different host port
```

### Can't Connect to MySQL/Redis from Container

**Symptom**: Connection timeout or refused

**Solutions:**
```bash
# 1. Check container can resolve hostname
docker exec smart-system-operator ping mysql

# 2. Use IP instead of hostname
docker run ... -e MYSQL_HOST=192.168.1.10

# 3. Use host.docker.internal (Mac/Windows)
docker run ... -e MYSQL_HOST=host.docker.internal

# 4. Linux: Add host gateway
docker run --add-host=host.docker.internal:host-gateway ...

# 5. Check MySQL bind address
# In my.cnf: bind-address = 0.0.0.0

# 6. Check MySQL user permissions
GRANT ALL ON smart_system.* TO 'user'@'%' IDENTIFIED BY 'pass';
```

### Metrics Not Collecting

**Symptom**: Empty dashboard, no metrics

**Check:**
```bash
# 1. Verify cron scheduler started
docker logs smart-system-operator | grep "Metrics crawler started"

# 2. Check server connections
# View execution logs in Reports > Errors

# 3. Verify Redis connection
docker exec smart-system-operator redis-cli -h redis PING

# 4. Check server SSH keys
# Ensure private key is complete including headers

# 5. Adjust crawler delay
docker run ... -e APP_CRAWLER_DELAY=60
```

### AI Analysis Not Working

**Symptom**: No AI recommendations

**Check:**
```bash
# 1. Verify OpenAI API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# 2. Check analyzer started
docker logs smart-system-operator | grep "AI analyzer started"

# 3. Verify metrics exist in Redis
docker exec redis redis-cli KEYS "server_metrics:*"

# 4. Check OpenAI model availability
docker run ... -e OPENAI_MODEL=gpt-4o

# 5. Review analyzer logs
docker logs smart-system-operator | grep "AI analysis"
```

### High Memory Usage

**Symptom**: Container using excessive memory

**Solutions:**
```bash
# 1. Limit container memory
docker run -m 2G ...

# 2. Clean old execution logs
DELETE FROM execution_logs WHERE executed_at < DATE_SUB(NOW(), INTERVAL 90 DAY);

# 3. Reduce cache TTL
# Modify redis_cache.py ttl values

# 4. Increase crawler/analyzer delays
docker run ... -e APP_CRAWLER_DELAY=120 -e APP_MODEL_DELAY=600

# 5. Monitor Redis memory
docker exec redis redis-cli INFO memory
```

### Permission Denied Errors

**Symptom**: Can't execute actions on servers

**Check:**
```bash
# 1. Verify sudo access
ssh user@server 'sudo -n true'

# 2. Configure passwordless sudo
# On target: sudo visudo
# Add: username ALL=(ALL) NOPASSWD: ALL

# 3. Check SSH key permissions
chmod 600 private_key.pem

# 4. Verify user in correct groups
ssh user@server 'groups'
```

### Docker Build Fails

**Symptom**: Build errors

**Solutions:**
```bash
# 1. Clear build cache
docker build --no-cache -t smart-system-operator .

# 2. Check Dockerfile syntax
docker build --progress=plain -t smart-system-operator .

# 3. Verify requirements.txt
pip install -r requirements.txt  # Test locally first

# 4. Check base image availability
docker pull python:3.13-slim-bullseye
```

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Contribution Workflow

1. **Fork the repository**
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Test thoroughly** (see testing checklist)
5. **Commit with clear messages:**
   ```bash
   git commit -m "Add: New analytics dashboard"
   git commit -m "Fix: Redis connection timeout"
   git commit -m "Update: Improve AI prompt context"
   ```
6. **Push to your fork:**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request** with:
   - Clear description of changes
   - Screenshots if UI changes
   - Testing performed
   - Breaking changes (if any)

### Development Guidelines

- Follow existing code structure
- Add tests for new features
- Update documentation
- Keep commits atomic and focused
- Write meaningful commit messages
- Comment complex logic

### Getting Help

- 📖 Check existing documentation
- 🔍 Search existing issues
- 💬 Ask in pull requests
- 📧 Contact maintainers for major changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **NiceGUI**: Beautiful web UI framework
- **OpenAI**: GPT-4 AI analysis engine
- **FastAPI**: High-performance web framework
- **Redis**: Fast caching layer
- **MySQL**: Reliable data storage
- **Chart.js**: Interactive charting library
- **Docker**: Containerization platform

## 📞 Support

- **GitHub Issues**: https://github.com/tsufuwu/smart_system_operator/issues
- **Docker Hub**: https://hub.docker.com/r/lanhlungbang/smart-system-operator
- **Documentation**: See this README and inline code comments

## 🗺️ Roadmap

### Planned Features

- [ ] Email notifications for high-risk events
- [ ] Slack/Discord webhook integrations
- [ ] Prometheus metrics export
- [ ] Grafana dashboard templates
- [ ] Multi-language support
- [ ] Mobile-responsive UI improvements
- [ ] Scheduled reports (daily/weekly)
- [ ] Custom AI prompts per server
- [ ] Action playbooks (sequential execution)
- [ ] Webhook-triggered actions
- [ ] API authentication tokens
- [ ] LDAP/SSO integration

### Version History

**v1.0.0** (Current)
- Initial release
- Server monitoring
- AI analysis
- Automated actions
- Reports & analytics
- User management
- Docker deployment

---

**Built with ❤️ by the Smart System Operator team**

*For production deployments, always use versioned releases and secure your secrets!*