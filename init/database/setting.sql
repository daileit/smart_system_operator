
CREATE TABLE IF NOT EXISTS app_settings (
    setting_id INT AUTO_INCREMENT PRIMARY KEY,
    setting_name VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    setting_group VARCHAR(50) DEFAULT 'General',
    description VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX (setting_name),
    INDEX (setting_group)
);

CREATE TABLE IF NOT EXISTS setting_options (
    option_id INT AUTO_INCREMENT PRIMARY KEY,
    setting_id INT NOT NULL,
    option_value VARCHAR(255) NOT NULL,
    option_label VARCHAR(255) NOT NULL,
    is_default TINYINT(1) DEFAULT 0,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (setting_id) REFERENCES app_settings(setting_id) ON DELETE CASCADE,
    INDEX (setting_id),
    UNIQUE KEY unique_setting_option (setting_id, option_value)
);
