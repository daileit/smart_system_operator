
CREATE TABLE IF NOT EXISTS app_settings (
    setting_name VARCHAR(100) NOT NULL,
    setting_value TEXT,
    setting_group VARCHAR(50) DEFAULT 'General',
    description VARCHAR(255) NULL,
    PRIMARY KEY (setting_name),
    INDEX (setting_group)
);


INSERT IGNORE INTO app_settings (setting_name, setting_value, setting_group, description) 
VALUES
('APP_FONT', 'Inter', 'UI', 'Font chữ chính của ứng dụng'),
('APP_THEME', 'Light', 'UI', 'Giao diện Sáng (Light) hoặc Tối (Dark)'),
('AI_MODEL', 'gpt-4o-mini', 'Gemini', 'Plexity'),
('ALERT_SEVERITY_THRESHOLD', 'WARNING', 'System', 'Ngưỡng cảnh báo tối thiểu để hiển thị');
