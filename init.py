import database as db
import config as env_config
import jsonlog
import bcrypt

logger = jsonlog.setup_logger("init")

mysql_config = env_config.Config(group="MYSQL")

def check_database_connection() -> db.MySQLClient:
    """Check if the database connection can be established."""
    db_client = db.MySQLClient(config={
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

def check_database_setup(db_client: db.MySQLClient):
    """Check if essential database tables exist."""
    required_tables = ["users", "roles", "pages", "user_roles", "role_permissions"]
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

def initialize_database(db_client: db.MySQLClient, init_secret: str = ""):
    """Initialize the database with required tables and default data."""
    try:
        # Read SQL file
        sql_file_path = "./init/database/system.sql"
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        with db_client.get_connection() as conn:
            cursor = conn.cursor()
            
            # Split the script into individual statements
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
            
            # Execute each statement
            for statement in statements:
                cursor.execute(statement)
            
            conn.commit()
            logger.info("Database initialized successfully from system.sql")
            
        # Insert default data after successful initialization
        insert_default_data(db_client=db_client, init_secret=init_secret)
        
    except FileNotFoundError:
        logger.error(f"SQL file not found: {sql_file_path}")
        raise
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def insert_default_data(db_client: db.MySQLClient, init_secret: str = ""):
    """Insert default data into the database."""
    try:
        # Insert predefined roles
        roles_query = "INSERT IGNORE INTO roles (role_id, role_name, description) VALUES (%s, %s, %s)"
        roles_data = [
            (1, 'admin', 'Administrator with full system access'),
            (2, 'user', 'Regular user with limited access')
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
            ('analytics', 'Analytics', 'Data analytics and insights')
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
            (1, 'analytics', 1)
        ]
        affected_rows = db_client.execute_many(admin_permissions_query, admin_permissions_data)
        logger.info(f"Inserted {affected_rows} admin permissions")

        # Insert manager role permissions (limited access)
        manager_permissions_query = "INSERT IGNORE INTO role_permissions (role_id, page_id, can_access) VALUES (%s, %s, %s)"
        manager_permissions_data = [
            (2, 'dashboard', 1),
            (2, 'profile', 1),
            (2, 'users', 0),
            (2, 'reports', 1),
            (2, 'settings', 0),
            (2, 'analytics', 1)
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
            (3, 'analytics', 0)
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
        
        logger.info("Default data inserted successfully")
        
    except Exception as e:
        logger.error(f"Error inserting default data: {e}")
        raise