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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== SERVERS TABLE =====
CREATE TABLE IF NOT EXISTS servers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    port INT DEFAULT 22,
    username VARCHAR(50) NOT NULL,
    ssh_private_key TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT,
    FOREIGN KEY (created_by) REFERENCES users(user_id),
    UNIQUE KEY unique_server (ip_address, port),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== COMMAND CONFIGS TABLE =====
CREATE TABLE IF NOT EXISTS command_configs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    action_id INT NOT NULL,
    command_template TEXT NOT NULL,
    timeout_seconds INT DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_action (action_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== COMMAND EXECUTE ACTIONS =====
INSERT IGNORE INTO actions (action_name, action_type, description) VALUES
('reboot_system', 'command_execute', 'Reboot the server system immediately. Use when system is unresponsive or after critical updates. HIGH RISK - causes downtime.'),
('restart_service', 'command_execute', 'Restart a specific systemd service. Useful for applying configuration changes or recovering from service failures. MEDIUM RISK - brief service interruption.'),
('stop_service', 'command_execute', 'Stop a specific systemd service. Use to halt misbehaving services or for maintenance. MEDIUM RISK - service becomes unavailable.'),
('start_service', 'command_execute', 'Start a specific systemd service. Use to bring services online after maintenance or failures. LOW RISK - restores service availability.'),
('block_ip_firewalld', 'command_execute', 'Block a specific IP address using firewalld. Use to prevent access from malicious or problematic IPs. MEDIUM RISK - may block legitimate traffic.'),
('unblock_ip_firewalld', 'command_execute', 'Unblock a previously blocked IP address using firewalld. Use to restore access after resolving issues. LOW RISK - restores access.'),
('kill_process', 'command_execute', 'Terminate processes matching a specific name pattern. Use to stop runaway or problematic processes. HIGH RISK - may kill critical processes.'),
('cleanup_temp_files', 'command_execute', 'Remove temporary files older than specified days. Use to free up disk space and maintain system cleanliness. LOW RISK - removes old temp files.');

INSERT IGNORE INTO command_configs (action_id, command_template, timeout_seconds) VALUES
((SELECT id FROM actions WHERE action_name = 'reboot_system'), 'sudo reboot', 60),
((SELECT id FROM actions WHERE action_name = 'restart_service'), 'sudo systemctl restart ${service_name}', 30),
((SELECT id FROM actions WHERE action_name = 'stop_service'), 'sudo systemctl stop ${service_name}', 30),
((SELECT id FROM actions WHERE action_name = 'start_service'), 'sudo systemctl start ${service_name}', 30),
((SELECT id FROM actions WHERE action_name = 'block_ip_firewalld'), 'sudo firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=${ip_address} drop" && sudo firewall-cmd --reload', 15),
((SELECT id FROM actions WHERE action_name = 'unblock_ip_firewalld'), 'sudo firewall-cmd --permanent --remove-rich-rule="rule family=ipv4 source address=${ip_address} drop" && sudo firewall-cmd --reload', 15),
((SELECT id FROM actions WHERE action_name = 'kill_process'), 'sudo pkill -f ${process_name}', 10),
((SELECT id FROM actions WHERE action_name = 'cleanup_temp_files'), 'sudo find /tmp -type f -mtime +${days} -delete', 20);

-- ===== COMMAND GET ACTIONS =====
INSERT IGNORE INTO actions (action_name, action_type, description) VALUES
('get_service_status', 'command_get', 'Check the current status of a systemd service including active state and recent logs. Safe information gathering.'),
('get_disk_usage', 'command_get', 'Get disk space usage for a specific path showing used, available, and percentage. Safe system monitoring.'),
('get_cpu_usage', 'command_get', 'Get current CPU usage percentage across all cores. Safe performance monitoring.'),
('get_memory_usage', 'command_get', 'Get current memory usage percentage including used and available memory. Safe resource monitoring.'),
('get_top_processes', 'command_get', 'Get top CPU and memory consuming processes. Safe resource usage analysis.');
-- ('get_network_connections', 'command_get', 'Show active network connections on a specific port including connection states. Safe network monitoring.'),
-- ('get_system_load', 'command_get', 'Get system load averages for 1, 5, and 15 minute intervals. Safe system health check.'),
-- ('get_uptime', 'command_get', 'Get system uptime and boot time information. Safe system information gathering.'),
-- ('get_failed_services', 'command_get', 'List all systemd services that are in failed state. Safe service health monitoring.'),
-- ('get_process_list', 'command_get', 'List all running processes matching a specific name pattern with resource usage. Safe process monitoring.'),

INSERT IGNORE INTO command_configs (action_id, command_template, timeout_seconds) VALUES
((SELECT id FROM actions WHERE action_name = 'get_service_status'), 'sudo systemctl status ${service_name} --no-pager', 10),
((SELECT id FROM actions WHERE action_name = 'get_disk_usage'), 'df -h ${path}', 5),
((SELECT id FROM actions WHERE action_name = 'get_cpu_usage'), 'top -bn1 | grep "Cpu(s)" | sed "s/.*, *\\([0-9.]*\\)%* id.*/\\1/" | awk \'{print 100 - $1"%"}\'', 5),
((SELECT id FROM actions WHERE action_name = 'get_memory_usage'), 'free -m | awk \'NR==2{printf "Memory Usage: %s/%sMB (%.2f%%)", $3,$2,$3*100/$2 }\'', 5),
((SELECT id FROM actions WHERE action_name = 'get_top_processes'), 'ps aux --sort=-%cpu | head -10', 5);
-- ((SELECT id FROM actions WHERE action_name = 'get_process_list'), 'ps aux | grep ${process_name} | grep -v grep', 5),
-- ((SELECT id FROM actions WHERE action_name = 'get_network_connections'), 'ss -tuln | grep ${port}', 5),
-- ((SELECT id FROM actions WHERE action_name = 'get_system_load'), 'uptime', 5),
-- ((SELECT id FROM actions WHERE action_name = 'get_uptime'), 'uptime -p && uptime -s', 5),
-- ((SELECT id FROM actions WHERE action_name = 'get_failed_services'), 'sudo systemctl list-units --state=failed --no-pager', 10),
