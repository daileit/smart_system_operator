from fastapi import FastAPI
from nicegui import ui
import jsonlog
import uvicorn

logger = jsonlog.setup_logger("app")
app = FastAPI()

# FastAPI routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/data")
async def get_data():
    return {"message": "Hello from API"}

# NiceGUI interface
@ui.page('/')
def main_page():
    ui.label('Web Application').classes('text-h3')
    ui.button('Click me', on_click=lambda: ui.notify('Button clicked!'))
    
@ui.page('/dashboard')
def dashboard():
    ui.label('Dashboard').classes('text-h3')
    with ui.card():
        ui.label('Welcome to the dashboard')

# Mount NiceGUI on FastAPI
ui.run_with(
    app,
    mount_path='/',
    storage_secret='change-this-secret-key'
)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)