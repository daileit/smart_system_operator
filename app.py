from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from nicegui import ui
import jsonlog
import uvicorn
import config as env_config

# Import webui pages
from webui import login_page, main_page, dashboard_page, users_page, setting_page

app_config = env_config.Config(group="APP")

logger = jsonlog.setup_logger("app")
app = FastAPI()

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