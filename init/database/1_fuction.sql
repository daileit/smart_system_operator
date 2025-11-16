-- ===== ACTIONS TABLE =====
CREATE TABLE IF NOT EXISTS actions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    action_name VARCHAR(100) NOT NULL UNIQUE,
    action_type ENUM('command_execute', 'command_get', 'http') NOT NULL,
    description TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (action_type),
    INDEX idx_active (is_active)
);

-- ===== SERVERS TABLE =====
CREATE TABLE IF NOT EXISTS servers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    port INT DEFAULT 22,
    username VARCHAR(50) NOT NULL,
    ssh_key_path VARCHAR(500) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT,
    FOREIGN KEY (created_by) REFERENCES users(user_id),
    UNIQUE KEY unique_server (ip_address, port),
    INDEX idx_created_by (created_by)
);

-- ===== COMMAND CONFIGS TABLE =====
CREATE TABLE IF NOT EXISTS command_configs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    action_id INT NOT NULL,
    command_template TEXT NOT NULL,
    timeout_seconds INT DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_action (action_id)
);

-- ===== HTTP CONFIGS TABLE =====
CREATE TABLE IF NOT EXISTS http_configs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    action_id INT NOT NULL,
    http_method ENUM('GET', 'POST', 'PUT', 'DELETE', 'PATCH') NOT NULL,
    http_url VARCHAR(500) NOT NULL,
    http_headers JSON,
    http_body TEXT,
    parameters JSON,
    timeout_seconds INT DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_action (action_id)
);

-- ===== SERVER ALLOWED ACTIONS TABLE (WITH AUTOMATIC FLAG) =====
CREATE TABLE IF NOT EXISTS server_allowed_actions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    server_id INT NOT NULL,
    action_id INT NOT NULL,
    automatic BOOLEAN DEFAULT FALSE, -- FALSE = advisory only, TRUE = auto execute
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
    FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_server_action (server_id, action_id),
    INDEX idx_server_auto (server_id, automatic),
    INDEX idx_action_auto (action_id, automatic)
);

-- ===== EXECUTION LOGS TABLE (WITH EXECUTION TYPE) =====
CREATE TABLE IF NOT EXISTS execution_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    server_id INT NOT NULL,
    action_id INT NOT NULL,
    execution_type ENUM('executed', 'recommended') NOT NULL, -- executed = actually ran, recommended = AI suggested only
    ai_reasoning TEXT, -- AI's reasoning for this action
    execution_details TEXT, -- Command/request details
    execution_result TEXT, -- Response/output (NULL for recommendations)
    status ENUM('success', 'failed', 'timeout', 'recommended') NOT NULL,
    error_message TEXT,
    execution_time DECIMAL(8,3), -- NULL for recommendations
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES servers(id),
    FOREIGN KEY (action_id) REFERENCES actions(id),
    INDEX idx_server_date (server_id, executed_at),
    INDEX idx_action_date (action_id, executed_at),
    INDEX idx_execution_type (execution_type),
    INDEX idx_status_date (status, executed_at)
);