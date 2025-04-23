-- Initialize MySQL database structure for logs

-- Use the logging database
USE logging;

-- Create logs table
CREATE TABLE logs (
                      id BIGINT AUTO_INCREMENT PRIMARY KEY,
                      message TEXT,
                      source VARCHAR(255),
                      container_name VARCHAR(255),
                      service_type VARCHAR(50),
                      timestamp TIMESTAMP,
                      level VARCHAR(20),
                      thread VARCHAR(255),
                      logger_name VARCHAR(255),
                      stack_trace TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_service_type ON logs(service_type);
CREATE INDEX idx_container_name ON logs(container_name);
CREATE INDEX idx_timestamp ON logs(timestamp);

-- Grants for the user
GRANT ALL PRIVILEGES ON logging.* TO 'loguser'@'%';
FLUSH PRIVILEGES;

-- Log a message to confirm initialization
INSERT INTO logs (message, source, container_name, service_type, timestamp)
VALUES ('MySQL logging system initialized', 'mysql-init', 'mysql', 'system', NOW());