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
        Update setting value by name.
        
        Args:
            name: Setting name
            value: New value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if setting has options
            options = self.get_options(name)
            
            # If options exist, validate the value
            if options:
                valid_values = [opt['option_value'] for opt in options]
                if value not in valid_values:
                    logger.warning(f"Invalid option '{value}' for setting '{name}'. Valid options: {valid_values}")
                    return False
            
            # Update setting value
            query = "UPDATE app_settings SET setting_value = %s WHERE setting_name = %s"
            affected, _ = self.db.execute_update(query, (value, name))
            
            if affected > 0:
                logger.info(f"Setting '{name}' updated to '{value}'")
                self._cache.clear()
                return True
            else:
                logger.warning(f"Setting '{name}' not found")
                return False
                
        except Exception as e:
            logger.error(f"Error setting '{name}' to '{value}': {e}")
            return False
    
    def set_by_id(self, setting_id: int, value: str) -> bool:
        """
        Update setting value by ID.
        
        Args:
            setting_id: Setting ID
            value: New value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get setting name first
            setting = self.db.fetch_one(
                "SELECT setting_name FROM app_settings WHERE setting_id = %s",
                (setting_id,)
            )
            
            if not setting:
                logger.warning(f"Setting ID {setting_id} not found")
                return False
            
            # Use set() method which handles validation
            return self.set(setting['setting_name'], value)
                
        except Exception as e:
            logger.error(f"Error setting ID {setting_id} to '{value}': {e}")
            return False
    
    def get_options(self, name: str) -> List[Dict[str, Any]]:
        """
        Get all available options for a setting by name.
        
        Args:
            name: Setting name
            
        Returns:
            List of option dictionaries with keys: option_value, option_label
        """
        try:
            query = """
                SELECT option_value, option_label
                FROM setting_options
                WHERE setting_name = %s 
                ORDER BY display_order
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
            List of option dictionaries with keys: option_value, option_label
        """
        try:
            # Get setting name first
            setting = self.db.fetch_one(
                "SELECT setting_name FROM app_settings WHERE setting_id = %s",
                (setting_id,)
            )
            
            if not setting:
                return []
            
            return self.get_options(setting['setting_name'])
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
        Reset a setting to its default value (first option) by name.
        
        Args:
            name: Setting name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get first option (default is the first one by display_order)
            options = self.get_options(name)
            
            if not options:
                logger.warning(f"No options found for setting '{name}'")
                return False
            
            # Use first option as default
            default_value = options[0]['option_value']
            return self.set(name, default_value)
        except Exception as e:
            logger.error(f"Error resetting setting '{name}': {e}")
            return False
    
    def reset_to_default_by_id(self, setting_id: int) -> bool:
        """
        Reset a setting to its default value (first option) by ID.
        
        Args:
            setting_id: Setting ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get setting name
            setting = self.db.fetch_one(
                "SELECT setting_name FROM app_settings WHERE setting_id = %s",
                (setting_id,)
            )
            
            if not setting:
                logger.warning(f"Setting ID {setting_id} not found")
                return False
            
            return self.reset_to_default(setting['setting_name'])
        except Exception as e:
            logger.error(f"Error resetting setting ID {setting_id}: {e}")
            return False
