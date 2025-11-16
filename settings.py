"""
Settings management module for Smart System Operator.
Provides easy access to application settings with predefined options.
"""

import jsonlog
from typing import List, Dict, Any, Optional

logger = jsonlog.setup_logger("settings")


class SettingsManager:
    """Manager for application settings with predefined options."""
    
    def __init__(self, db_client):
        """
        Initialize SettingsManager.
        
        Args:
            db_client: Database client instance (MySQLClient or SQLiteClient)
        """
        self.db = db_client
        self._cache = {}
    
    def get(self, name: str, default: str = None) -> str:
        """
        Get setting value by name.
        
        Args:
            name: Setting name
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        try:
            result = self.db.fetch_one(
                "SELECT setting_value FROM app_settings WHERE setting_name = %s",
                (name,)
            )
            return result['setting_value'] if result else default
        except Exception as e:
            logger.error(f"Error getting setting '{name}': {e}")
            return default
    
    def get_by_id(self, setting_id: int, default: str = None) -> str:
        """
        Get setting value by ID.
        
        Args:
            setting_id: Setting ID
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        try:
            result = self.db.fetch_one(
                "SELECT setting_value FROM app_settings WHERE setting_id = %s",
                (setting_id,)
            )
            return result['setting_value'] if result else default
        except Exception as e:
            logger.error(f"Error getting setting ID {setting_id}: {e}")
            return default
    
    def set(self, name: str, value: str) -> bool:
        """
        Update setting value by name (must be one of the predefined options).
        
        Args:
            name: Setting name
            value: New value (must exist in setting_options)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get setting_id first
            setting = self.db.fetch_one(
                "SELECT setting_id FROM app_settings WHERE setting_name = %s",
                (name,)
            )
            
            if not setting:
                logger.warning(f"Setting '{name}' not found")
                return False
            
            return self.set_by_id(setting['setting_id'], value)
                
        except Exception as e:
            logger.error(f"Error setting '{name}' to '{value}': {e}")
            return False
    
    def set_by_id(self, setting_id: int, value: str) -> bool:
        """
        Update setting value by ID (must be one of the predefined options).
        
        Args:
            setting_id: Setting ID
            value: New value (must exist in setting_options)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate that the option exists
            option = self.db.fetch_one(
                "SELECT option_value FROM setting_options WHERE setting_id = %s AND option_value = %s",
                (setting_id, value)
            )
            
            if not option:
                logger.warning(f"Invalid option '{value}' for setting ID {setting_id}")
                return False
            
            # Update setting
            query = """
                UPDATE app_settings 
                SET setting_value = %s 
                WHERE setting_id = %s
            """
            affected, _ = self.db.execute_update(query, (value, setting_id))
            
            if affected > 0:
                logger.info(f"Setting ID {setting_id} updated to '{value}'")
                # Clear cache
                self._cache.clear()
                return True
            else:
                logger.warning(f"Setting ID {setting_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error setting ID {setting_id} to '{value}': {e}")
            return False
    
    def get_options(self, name: str) -> List[Dict[str, Any]]:
        """
        Get all available options for a setting by name.
        
        Args:
            name: Setting name
            
        Returns:
            List of option dictionaries with keys: option_value, option_label, is_default
        """
        try:
            query = """
                SELECT so.option_value, so.option_label, so.is_default 
                FROM setting_options so
                JOIN app_settings s ON so.setting_id = s.setting_id
                WHERE s.setting_name = %s 
                ORDER BY so.display_order
            """
            options = self.db.execute_query(query, (name,))
            return options
        except Exception as e:
            logger.error(f"Error getting options for '{name}': {e}")
            return []
    
    def get_options_by_id(self, setting_id: int) -> List[Dict[str, Any]]:
        """
        Get all available options for a setting by ID.
        
        Args:
            setting_id: Setting ID
            
        Returns:
            List of option dictionaries with keys: option_value, option_label, is_default
        """
        try:
            query = """
                SELECT option_value, option_label, is_default 
                FROM setting_options 
                WHERE setting_id = %s 
                ORDER BY display_order
            """
            options = self.db.execute_query(query, (setting_id,))
            return options
        except Exception as e:
            logger.error(f"Error getting options for setting ID {setting_id}: {e}")
            return []
    
    def get_all_settings(self) -> List[Dict[str, Any]]:
        """
        Get all settings with their current values and options.
        
        Returns:
            List of settings with metadata
        """
        try:
            query = """
                SELECT 
                    setting_id,
                    setting_name, 
                    setting_value, 
                    setting_group, 
                    description 
                FROM app_settings 
                ORDER BY setting_group, setting_name
            """
            settings = self.db.execute_query(query)
            
            # Attach options to each setting
            for setting in settings:
                setting['options'] = self.get_options_by_id(setting['setting_id'])
            
            return settings
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return []
    
    def get_by_group(self, group: str) -> List[Dict[str, Any]]:
        """
        Get all settings in a specific group.
        
        Args:
            group: Setting group name
            
        Returns:
            List of settings in the group
        """
        try:
            query = """
                SELECT 
                    setting_id,
                    setting_name, 
                    setting_value, 
                    setting_group, 
                    description 
                FROM app_settings 
                WHERE setting_group = %s 
                ORDER BY setting_name
            """
            settings = self.db.execute_query(query, (group,))
            
            # Attach options to each setting
            for setting in settings:
                setting['options'] = self.get_options_by_id(setting['setting_id'])
            
            return settings
        except Exception as e:
            logger.error(f"Error getting settings for group '{group}': {e}")
            return []
    
    def get_groups(self) -> List[str]:
        """
        Get all setting groups.
        
        Returns:
            List of group names
        """
        try:
            query = "SELECT DISTINCT setting_group FROM app_settings ORDER BY setting_group"
            results = self.db.execute_query(query)
            return [r['setting_group'] for r in results]
        except Exception as e:
            logger.error(f"Error getting setting groups: {e}")
            return []
    
    def reset_to_default(self, name: str) -> bool:
        """
        Reset a setting to its default value by name.
        
        Args:
            name: Setting name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get setting_id and default option
            query = """
                SELECT s.setting_id, so.option_value 
                FROM app_settings s
                JOIN setting_options so ON s.setting_id = so.setting_id
                WHERE s.setting_name = %s AND so.is_default = 1
            """
            result = self.db.fetch_one(query, (name,))
            
            if not result:
                logger.warning(f"No default option found for setting '{name}'")
                return False
            
            return self.set_by_id(result['setting_id'], result['option_value'])
        except Exception as e:
            logger.error(f"Error resetting setting '{name}': {e}")
            return False
    
    def reset_to_default_by_id(self, setting_id: int) -> bool:
        """
        Reset a setting to its default value by ID.
        
        Args:
            setting_id: Setting ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get default option
            default = self.db.fetch_one(
                "SELECT option_value FROM setting_options WHERE setting_id = %s AND is_default = 1",
                (setting_id,)
            )
            
            if not default:
                logger.warning(f"No default option found for setting ID {setting_id}")
                return False
            
            return self.set_by_id(setting_id, default['option_value'])
        except Exception as e:
            logger.error(f"Error resetting setting ID {setting_id}: {e}")
            return False
