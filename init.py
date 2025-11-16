import database as db
import config as env_config
import jsonlog
import bcrypt
import os
from pathlib import Path

logger = jsonlog.setup_logger("init")

mysql_config = env_config.Config(group="MYSQL")


def check_database_connection() -> db.DatabaseClient:
    """Check if the database connection can be established."""
    db_client = db.DatabaseClient(config={
        "host": mysql_config.get("MYSQL_HOST"),
        "user": mysql_config.get("MYSQL_USER"),
        "password": mysql_config.get("MYSQL_PASSWORD"),
        "database": mysql_config.get("MYSQL_DATABASE"),
        "port": int(mysql_config.get("MYSQL_PORT", 3306))
    }, use_pool=True, pool_size=10)
    try:
        with db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                logger.info("Database connection successful")
                return db_client
            else:
                logger.error("Database connection test query failed")
                return None
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def check_database_setup(db_client: db.DatabaseClient):
    """Check if essential database tables exist."""
    required_tables = ["users", "roles", "pages", "user_roles", "role_permissions", "app_settings", "setting_options"]
    try:
        with db_client.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            existing_tables = {row[0] for row in cursor.fetchall()}
            missing_tables = [table for table in required_tables if table not in existing_tables]
            if missing_tables:
                logger.warning(f"Missing required tables: {missing_tables}")
                return False
            logger.info("All required database tables are present")
            return True
    except Exception as e:
        logger.error(f"Error checking database setup: {e}")
        return False

def initialize_database(db_client: db.DatabaseClient, init_secret: str = ""):
    """Initialize the database with required tables and default data by loading all SQL schema files."""
    try:
        # Get all SQL files from the init/database directory
        sql_directory = Path("./init/database")
        sql_files = sorted(sql_directory.glob("*.sql"))
        
        if not sql_files:
            logger.warning("No SQL schema files found in ./init/database")
            return
        
        logger.info(f"Found {len(sql_files)} SQL schema files to execute")
        
        with db_client.get_connection() as conn:
            cursor = conn.cursor()
            
            # Execute each SQL file
            for sql_file in sql_files:
                logger.info(f"Executing schema file: {sql_file.name}")
                
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                
                # Split the script into individual statements
                statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
                
                # Execute each statement
                for statement in statements:
                    cursor.execute(statement)
                
                logger.info(f"Successfully executed {sql_file.name}")
            
            conn.commit()
            logger.info("Database schema initialized successfully from all SQL files")
            
        # Insert default data after successful initialization
        insert_default_data(db_client=db_client, init_secret=init_secret)
        
    except FileNotFoundError as e:
        logger.error(f"SQL file not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def insert_default_data(db_client: db.DatabaseClient, init_secret: str = ""):
    """Insert default data into the database."""
    try:
        # Insert predefined roles
        roles_query = "INSERT IGNORE INTO roles (role_id, role_name, description) VALUES (%s, %s, %s)"
        roles_data = [
            (1, 'admin', 'Administrator with full system access'),
            (2, 'manager', 'Manager with elevated access'),
            (3, 'user', 'Regular user with limited access')
        ]
        affected_rows = db_client.execute_many(roles_query, roles_data)
        logger.info(f"Inserted {affected_rows} roles")
        
        # Insert predefined pages
        pages_query = "INSERT IGNORE INTO pages (page_id, page_name, description) VALUES (%s, %s, %s)"
        pages_data = [
            ('dashboard', 'Dashboard', 'Main dashboard page'),
            ('profile', 'User Profile', 'Personal profile management'),
            ('users', 'User Management', 'Manage system users'),
            ('reports', 'Reports', 'View system reports'),
            ('settings', 'System Settings', 'System configuration'),
            ('servers', 'Servers', 'Server management and monitoring')
        ]
        affected_rows = db_client.execute_many(pages_query, pages_data)
        logger.info(f"Inserted {affected_rows} pages")
        
        # Insert admin role permissions (full access)
        admin_permissions_query = "INSERT IGNORE INTO role_permissions (role_id, page_id, can_access) VALUES (%s, %s, %s)"
        admin_permissions_data = [
            (1, 'dashboard', 1),
            (1, 'profile', 1),
            (1, 'users', 1),
            (1, 'reports', 1),
            (1, 'settings', 1),
            (1, 'servers', 1)
        ]
        affected_rows = db_client.execute_many(admin_permissions_query, admin_permissions_data)
        logger.info(f"Inserted {affected_rows} admin permissions")

        # Insert manager role permissions (elevated access)
        manager_permissions_query = "INSERT IGNORE INTO role_permissions (role_id, page_id, can_access) VALUES (%s, %s, %s)"
        manager_permissions_data = [
            (2, 'dashboard', 1),
            (2, 'profile', 1),
            (2, 'users', 0),
            (2, 'reports', 1),
            (2, 'settings', 0),
            (2, 'servers', 1)
        ]
        affected_rows = db_client.execute_many(manager_permissions_query, manager_permissions_data)
        logger.info(f"Inserted {affected_rows} user permissions")
        
        # Insert user role permissions (limited access)
        user_permissions_query = "INSERT IGNORE INTO role_permissions (role_id, page_id, can_access) VALUES (%s, %s, %s)"
        user_permissions_data = [
            (3, 'dashboard', 1),
            (3, 'profile', 1),
            (3, 'users', 0),
            (3, 'reports', 0),
            (3, 'settings', 0),
            (3, 'servers', 0)
        ]
        affected_rows = db_client.execute_many(user_permissions_query, user_permissions_data)
        logger.info(f"Inserted {affected_rows} user permissions")
        
        # Hash the init_secret for admin password
        if not init_secret:
            raise ValueError("init_secret is required to create admin user")
        
        password_hash = bcrypt.hashpw(init_secret.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insert default admin user
        admin_user_query = "INSERT IGNORE INTO users (user_id, username, email, password_hash, full_name, status) VALUES (%s, %s, %s, %s, %s, %s)"
        admin_user_data = [
            (1, 'sysadmin', 'sysadmin@timo.vn', password_hash, 'System Administrator', 1)            
        ]
        affected_rows = db_client.execute_many(admin_user_query, admin_user_data)
        logger.info(f"Inserted {affected_rows} admin user")
        
        # Assign admin role to admin user
        user_role_query = "INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (%s, %s)"
        user_role_data = [(1, 1)]
        affected_rows = db_client.execute_many(user_role_query, user_role_data)
        logger.info(f"Assigned admin role to admin user")
        
        # Insert default application settings
        settings_query = "INSERT IGNORE INTO app_settings (setting_name, setting_value, setting_group, description) VALUES (%s, %s, %s, %s)"
        settings_data = [
            ('APP_FONT', 'Inter', 'UI', 'Font chữ chính của ứng dụng'),
            ('APP_THEME', 'Light', 'UI', 'Giao diện Sáng (Light) hoặc Tối (Dark)'),
            ('ALERT_SEVERITY_THRESHOLD', 'WARNING', 'System', 'Ngưỡng cảnh báo tối thiểu để hiển thị'),
        ]
        affected_rows = db_client.execute_many(settings_query, settings_data)
        logger.info(f"Inserted {affected_rows} application settings")
        
        # Insert predefined setting options
        options_query = "INSERT IGNORE INTO setting_options (setting_name, option_value, option_label, display_order) VALUES (%s, %s, %s, %s)"
        options_data = [
            ('APP_FONT', 'Inter', 'Inter (Default)', 1),
            ('APP_FONT', 'Roboto', 'Roboto', 2),
            ('APP_FONT', 'Open Sans', 'Open Sans', 3),
            ('APP_FONT', 'Lato', 'Lato', 4),
            ('APP_FONT', 'Poppins', 'Poppins', 5),
            
            ('APP_THEME', 'Light', 'Light (Sáng)', 1),
            ('APP_THEME', 'Dark', 'Dark (Tối)', 2),
            ('APP_THEME', 'Auto', 'Auto (Tự động)', 3),
            
            ('ALERT_SEVERITY_THRESHOLD', 'INFO', 'INFO (Thông tin)', 1),
            ('ALERT_SEVERITY_THRESHOLD', 'WARNING', 'WARNING (Cảnh báo)', 2),
            ('ALERT_SEVERITY_THRESHOLD', 'ERROR', 'ERROR (Lỗi)', 3),
            ('ALERT_SEVERITY_THRESHOLD', 'CRITICAL', 'CRITICAL (Nghiêm trọng)', 4),
        ]
        
        affected_rows = db_client.execute_many(options_query, options_data)
        logger.info(f"Inserted {affected_rows} setting options")
        
        logger.info("Default data inserted successfully")
        
    except Exception as e:
        logger.error(f"Error inserting default data: {e}")
        raise