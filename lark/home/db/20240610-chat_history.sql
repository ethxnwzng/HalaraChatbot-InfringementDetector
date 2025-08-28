--create chat history database if it doesn't exist
CREATE DATABASE IF NOT EXISTS lark_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

--switch to the chat history database
USE lark_chat;

--create chat messages table
CREATE TABLE IF NOT EXISTS chat_msg (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    msg_id VARCHAR(64) NOT NULL UNIQUE,
    direction VARCHAR(16) NOT NULL,
    msg_type VARCHAR(16) NOT NULL,
    chat_type VARCHAR(16) NOT NULL,
    chat_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    parent_id VARCHAR(64),
    root_id VARCHAR(64),
    content JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_chat_id (chat_id),
    INDEX idx_user_id (user_id),
    INDEX idx_parent_id (parent_id),
    INDEX idx_root_id (root_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--create chat context table (row = every time new user sends a message)
CREATE TABLE IF NOT EXISTS chat_context (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    context_key VARCHAR(64) NOT NULL,
    context_value TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    INDEX idx_user_context (user_id, context_key),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;