from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from nicegui import ui, app as nicegui_app
import jsonlog
import uvicorn
import config as env_config
from cron import CronManager

# Import webui pages
from webui import login_page, main_page, dashboard_page, users_page, settings_page, servers_page, reports_page

app_config = env_config.Config(group="APP")

logger = jsonlog.setup_logger("app")
app = FastAPI()

# Initialize cron manager
cron_manager = None

@app.on_event("startup")
async def startup_event():
    """Start cron schedulers on application startup."""
    global cron_manager
    try:
        cron_manager = CronManager()
        cron_manager.start_all()
        logger.info("Cron schedulers started successfully")
    except Exception as e:
        logger.error(f"Failed to start cron schedulers: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop cron schedulers on application shutdown."""
    global cron_manager
    if cron_manager:
        try:
            cron_manager.stop_all()
            logger.info("Cron schedulers stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop cron schedulers: {e}")

# Mount static files
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# FastAPI routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/data")
async def get_data():
    return {"message": "Hello from API"}

# Pages are defined in webui module and automatically registered via @ui.page decorators
# - /login (webui/login.py)
# - / (webui/main.py)
# - /dashboard (webui/dashboard.py)
# - /users (webui/users.py)

# Mount NiceGUI on FastAPI
ui.run_with(
    app,
    mount_path='/',
    storage_secret=app_config.get("APP_INIT_SECRET")
)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=int(app_config.get("APP_PORT")))