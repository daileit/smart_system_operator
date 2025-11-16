from nicegui import ui
from database import MySQLClient
from modules.settings_model import SettingsModel # Import model logic
import jsonlog
from typing import Dict

logger = jsonlog.setup_logger("settings_view")

def create_ui(db_client: MySQLClient):
    """
    Hàm này xây dựng toàn bộ giao diện cho trang Cài đặt.
    Nó nhận 'db_client' từ app.py.
    """
    

    model = SettingsModel(db_client)

    app_settings = ui.state(value={})

   
    ui_elements: Dict[str, ui.element] = {}

    async def load_settings():
        """Tải cài đặt từ CSDL và cập nhật UI state."""
        try:
            settings_dict = await model.get_settings_as_dict()
            app_settings.value = settings_dict
            
            # Cập nhật giá trị cho các UI element đã được tạo
            for name, element in ui_elements.items():
                if name in settings_dict:
                    element.set_value(settings_dict[name])
                    
            logger.info("Tải cài đặt thành công.")
            ui.notify('Tải cài đặt thành công!', color='positive')
        except Exception as e:
            logger.error(f"Lỗi khi tải cài đặt: {e}")
            ui.notify(f'Lỗi: {e}', color='red')

    async def save_settings():

        settings_to_save = {}
        # Lấy giá trị mới từ các UI element
        for name, element in ui_elements.items():
            settings_to_save[name] = element.value
            
        try:
            success = await model.bulk_update_settings(settings_to_save)
            if success:
                ui.notify('Đã lưu cài đặt thành công!', color='green')
                # Tải lại để đảm bảo dữ liệu đồng bộ
                await load_settings()
            else:
                ui.notify('Lỗi: Không thể lưu cài đặt.', color='red')
        except Exception as e:
            logger.error(f"Lỗi khi lưu cài đặt: {e}")
            ui.notify(f'Lỗi: {e}', color='red')

    # --- Xây dựng Giao diện (UI) ---
    ui.label('Cài đặt Ứng dụng').classes('text-h3')
    
    with ui.row().classes('w-full items-center'):
        ui.button('Lưu Cài đặt', on_click=save_settings).props('icon=save color=primary')
        ui.button('Tải lại', on_click=load_settings).props('icon=refresh')

    # Card cho Nhóm 'UI'
    with ui.card().classes('w-full mt-4'):
        ui.label('Giao diện (UI)').classes('text-h5')
        
        # Lấy giá trị mặc định từ state
        # Chúng ta thêm vào dict ui_elements để có thể 'save'
        ui_elements['APP_FONT'] = ui.input('Font chữ', value=app_settings.value.get('APP_FONT')) \
                                     .props('outlined').classes('w-full')
                                     
        ui_elements['APP_THEME'] = ui.select(['Light', 'Dark'], 
                                             label='Giao diện (Theme)', 
                                             value=app_settings.value.get('APP_THEME')) \
                                     .props('outlined').classes('w-full')

    # Card cho Nhóm 'AI'
    with ui.card().classes('w-full mt-4'):
        ui.label('Trí tuệ Nhân tạo (AI)').classes('text-h5')
        
        ui_elements['AI_MODEL'] = ui.select(['gpt-4o', 'gpt-4o-mini', 'claude-3-haiku'], 
                                            label='Mô hình AI', 
                                            value=app_settings.value.get('AI_MODEL')) \
                                    .props('outlined').classes('w-full')

    # Card cho Nhóm 'System'
    with ui.card().classes('w-full mt-4'):
        ui.label('Hệ thống (System)').classes('text-h5')
        
        ui_elements['ALERT_SEVERITY_THRESHOLD'] = \
            ui.select(['INFO', 'WARNING', 'CRITICAL'], 
                      label='Ngưỡng Cảnh báo', 
                      value=app_settings.value.get('ALERT_SEVERITY_THRESHOLD')) \
              .props('outlined').classes('w-full')


    # Tải dữ liệu lần đầu khi trang được mở
    ui.on_page_ready(load_settings)