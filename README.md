# Smart System Operator

> AI-powered server monitoring and automated operations with real-time metrics, intelligent analysis, and policy-based remediation.

[![Docker Build](https://img.shields.io/docker/automated/lanhlungbang/smart-system-operator)](https://hub.docker.com/r/lanhlungbang/smart-system-operator)
[![Docker Pulls](https://img.shields.io/docker/pulls/lanhlungbang/smart-system-operator)](https://hub.docker.com/r/lanhlungbang/smart-system-operator)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start-docker)
- [Installation](#installation)
- [Configuration](#configuration-env-vars)
- [Deployment](#deployment)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting-quick)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)
- [Roadmap](#roadmap)

## Overview

Smart System Operator monitors Linux servers, analyzes metrics using OpenAI models, and can automatically run safe remediation actions based on configurable policies. It ships with a NiceGUI web UI, FastAPI backend, MySQL storage, and Redis caching.

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

## Quick Start (Docker)

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

Open http://localhost:8080

- Default admin username: `sysadmin`
- Default admin password: value of `APP_INIT_SECRET` (change it immediately)

## Installation

### Docker Compose (recommended)

```yaml
version: '3.8'
services:
  app:
    image: lanhlungbang/smart-system-operator:latest
    ports: ["8080:8080"]
    environment:
      MYSQL_HOST: mysql
      MYSQL_USER: smartsys_user
      MYSQL_PASSWORD: secure_mysql_password
      MYSQL_DATABASE: smart_system
      REDIS_HOST: redis
      REDIS_PORT: 6379
      OPENAI_API_KEY: sk-your-openai-api-key
      APP_INIT_SECRET: change-this-secret
      APP_ENV: production
      APP_CRAWLER_DELAY: 60
      APP_MODEL_DELAY: 300
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: secure_root_password
      MYSQL_DATABASE: smart_system
      MYSQL_USER: smartsys_user
      MYSQL_PASSWORD: secure_mysql_password
    volumes: ["mysql_data:/var/lib/mysql"]
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass secure_redis_password
    volumes: ["redis_data:/data"]

volumes:
  mysql_data: {}
  redis_data: {}
```

Start: `docker-compose up -d`

### Manual (dev)

```bash
git clone https://github.com/tsufuwu/smart_system_operator.git
cd smart_system_operator
python3 -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
export MYSQL_HOST=localhost MYSQL_USER=user MYSQL_PASSWORD=pass MYSQL_DATABASE=smart_system \
       REDIS_HOST=localhost REDIS_PORT=6379 OPENAI_API_KEY=sk-your-key APP_INIT_SECRET=dev-secret
python app.py
```

## Configuration (env vars)

### MySQL
- `MYSQL_HOST`, `MYSQL_PORT` (default: `3306`)
- `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`

### Redis
- `REDIS_HOST`, `REDIS_PORT` (default: `6379`)
- `REDIS_PASSWORD`, `REDIS_DB` (default: `0`)

### OpenAI
- `OPENAI_API_KEY` (Required)
- `OPENAI_MODEL` (default: `gpt-4o`)
- `OPENAI_LANGUAGE` (default: `Vietnamese`)
- `OPENAI_BASE_URL` (default: `https://api.openai.com/v1`)

### Application
- `APP_INIT_SECRET` (Required: Admin password & session secret)
- `APP_ENV` (default: `development`), `APP_DEBUG` (default: `false`)
- `APP_LOG_LEVEL` (default: `INFO`), `APP_NAME` (default: `smart_system`)
- `APP_PORT` (default: `8080`)
- `APP_CRAWLER_DELAY` (default: `30`), `APP_MODEL_DELAY` (default: `120`)

## Deployment

- Docker Hub: https://hub.docker.com/r/lanhlungbang/smart-system-operator
- Bridge network is recommended; use service names for `MYSQL_HOST`/`REDIS_HOST` in Compose.
- Access host services from Linux containers with `--add-host=host.docker.internal:host-gateway` and set host as `host.docker.internal`.

Kubernetes (example):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: {name: smart-system-operator, namespace: monitoring}
spec:
  replicas: 2
  selector: {matchLabels: {app: smart-system-operator}}
  template:
    metadata: {labels: {app: smart-system-operator}}
    spec:
      containers:
      - name: app
        image: lanhlungbang/smart-system-operator:latest
        ports: [{containerPort: 8080}]
        env:
        - {name: MYSQL_HOST, value: mysql-service}
        - name: MYSQL_USER
          valueFrom: {secretKeyRef: {name: mysql-credentials, key: username}}
        - name: MYSQL_PASSWORD
          valueFrom: {secretKeyRef: {name: mysql-credentials, key: password}}
        - {name: REDIS_HOST, value: redis-service}
        - name: OPENAI_API_KEY
          valueFrom: {secretKeyRef: {name: openai-credentials, key: api-key}}
        - name: APP_INIT_SECRET
          valueFrom: {secretKeyRef: {name: app-secrets, key: init-secret}}
        readinessProbe: {httpGet: {path: /api/health, port: 8080}, initialDelaySeconds: 10}
        livenessProbe: {httpGet: {path: /api/health, port: 8080}, initialDelaySeconds: 30}
---
apiVersion: v1
kind: Service
metadata: {name: smart-system-operator, namespace: monitoring}
spec:
  selector: {app: smart-system-operator}
  ports: [{port: 80, targetPort: 8080}]
  type: LoadBalancer
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
   - Enable monitoring actions (`get_cpu_usage`, `get_memory_usage`, etc.)
   - Enable execute actions if needed (`restart_service`, `cleanup`, etc.)
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

## Troubleshooting (quick)

- App won’t start: `docker logs smart-system-operator`; verify required env vars
- MySQL/Redis: check hosts/ports, credentials, and container networking
- OpenAI errors: verify `OPENAI_API_KEY`, model availability, and quotas
- SSH failures: validate private key format and remote sudo permissions
- High memory: increase delays, clean old logs, review Redis memory

Useful checks:

```bash
# MySQL
mysql -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD -e "SHOW DATABASES;"

# Redis
redis-cli -h $REDIS_HOST -p ${REDIS_PORT:-6379} PING

# OpenAI
curl -sH "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models | head
```

## Development

```bash
git clone https://github.com/tsufuwu/smart_system_operator.git
cd smart_system_operator
python3 -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
export APP_ENV=development APP_DEBUG=true APP_LOG_LEVEL=DEBUG
python app.py
```

Core modules: `app.py` (entry), `config.py`, `database.py`, `redis_cache.py`, `authen.py`, `servers.py`, `action.py`, `openai_client.py`, `cron.py`, `webui/*`.

## Contributing

PRs welcome! Please keep changes focused, add tests where reasonable, and update docs. For CI builds, configure `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets in your fork.

## License

MIT — see [LICENSE](LICENSE).

## Support

- Issues: https://github.com/tsufuwu/smart_system_operator/issues
- Docker Hub: https://hub.docker.com/r/lanhlungbang/smart-system-operator

## Roadmap

- Notifications (email/Slack/Discord)
- Prometheus/Grafana integrations
- Scheduled reports
- Action playbooks and webhooks
- API tokens and SSO/LDAP
