-- Run this in MySQL Workbench or phpMyAdmin

CREATE DATABASE IF NOT EXISTS smart_home CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_home;

-- Devices table
CREATE TABLE IF NOT EXISTS devices (
    device_id INT AUTO_INCREMENT PRIMARY KEY,
    device_name VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'OFF',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Voice commands table
CREATE TABLE IF NOT EXISTS voice_commands (
    command_id INT AUTO_INCREMENT PRIMARY KEY,
    command_text TEXT NOT NULL,
    language VARCHAR(20),
    recognized_command VARCHAR(100),
    device_name VARCHAR(50),
    action VARCHAR(20),
    confidence FLOAT,
    is_executed BOOLEAN DEFAULT FALSE,
    executed_action VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Device logs table
CREATE TABLE IF NOT EXISTS device_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    device_name VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    source VARCHAR(20) DEFAULT 'manual',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User habits table (for ML)
CREATE TABLE IF NOT EXISTS user_habits (
    habit_id INT AUTO_INCREMENT PRIMARY KEY,
    device_name VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    hour_of_day INT NOT NULL,
    day_of_week INT NOT NULL,
    frequency INT DEFAULT 1,
    last_executed TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert default devices with initial status
INSERT INTO devices (device_name, status) VALUES 
('light', 'OFF'),
('fan', 'OFF'),
('door_lock', 'LOCKED');