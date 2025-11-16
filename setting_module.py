from database import MySQLClient
import jsonlog
from typing import List, Dict, Any

logger = jsonlog.setup_logger("settings_model")

class SettingsModel:
    """
    Lớp này xử lý logic nghiệp vụ cho việc đọc/ghi
    các cài đặt ứng dụng từ CSDL.
    """
    
    def __init__(self, db_client: MySQLClient):
        self.db = db_client

    async def get_all_settings(self) -> List[Dict[str, Any]]:
        """Lấy tất cả cài đặt từ CSDL."""
        try:
            sql = "SELECT setting_name, setting_value, setting_group, description FROM app_settings ORDER BY setting_group, setting_name"
            results = await self.db.execute_query(sql)
            return results
        except Exception as e:
            logger.error(f"Lỗi khi lấy tất cả cài đặt: {e}")
            return []

    async def get_settings_as_dict(self) -> Dict[str, Any]:
        """Lấy tất cả cài đặt và trả về dưới dạng một dictionary tiện lợi."""
        settings_list = await self.get_all_settings()
        # Chuyển đổi list of dicts -> dict (key: value)
        return {s['setting_name']: s['setting_value'] for s in settings_list}

    async def update_setting(self, name: str, value: str) -> bool:
        """Cập nhật một giá trị cài đặt cụ thể."""
        try:
            sql = "UPDATE app_settings SET setting_value = %s WHERE setting_name = %s"
            params = (value, name)
            affected_rows, _ = await self.db.execute_update(sql, params)
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cài đặt '{name}': {e}")
            return False

    async def bulk_update_settings(self, settings_to_update: Dict[str, str]) -> bool:
        """
        Cập nhật nhiều cài đặt cùng lúc.
        Sử dụng transaction để đảm bảo an toàn.
        """
        try:
            # Bắt đầu một transaction
            with self.db.transaction() as cursor:
                for name, value in settings_to_update.items():
                    sql = "UPDATE app_settings SET setting_value = %s WHERE setting_name = %s"
                    params = (value, name)
                    cursor.execute(sql, params)
            
            logger.info(f"Cập nhật thành công {len(settings_to_update)} cài đặt.")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật hàng loạt cài đặt: {e}")
            return False