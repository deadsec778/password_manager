-- ==============================================================================
-- Password Manager - Master Full Schema Migration (000_full_blank_schema.sql)
-- Complete, Idempotent Database Initialization for Blank Databases & Fresh Setups
-- Compatible with MariaDB 10.5+ and MySQL 8.0+ / 5.7+
-- ==============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------------------------
-- 1. Table: users
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `user_id` INT(11) NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(100) NOT NULL,
  `email` VARCHAR(150) NOT NULL,
  `master_password_hash` VARCHAR(255) NOT NULL,
  `salt` VARCHAR(255) DEFAULT NULL,
  `role` ENUM('admin', 'user') NOT NULL DEFAULT 'user',
  `status` ENUM('active', 'disabled') NOT NULL DEFAULT 'active',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `last_login` DATETIME DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `idx_users_username` (`username`),
  UNIQUE KEY `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 2. Table: vaults
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `vaults` (
  `vault_id` INT(11) NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `vault_name` VARCHAR(100) NOT NULL,
  `description` VARCHAR(255) DEFAULT NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`vault_id`),
  KEY `idx_vaults_user_id` (`user_id`),
  CONSTRAINT `fk_vaults_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 3. Table: passwords
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `passwords` (
  `password_id` INT(11) NOT NULL AUTO_INCREMENT,
  `vault_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `service_name` VARCHAR(150) NOT NULL,
  `username` VARCHAR(150) DEFAULT NULL,
  `password_encrypted` TEXT DEFAULT NULL,
  `password_user_enc` TEXT DEFAULT NULL,
  `password_admin_enc` TEXT DEFAULT NULL,
  `enc_salt` VARCHAR(255) DEFAULT NULL,
  `enc_nonce` VARCHAR(64) DEFAULT NULL,
  `url` VARCHAR(255) DEFAULT NULL,
  `notes` TEXT DEFAULT NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `last_accessed` DATETIME DEFAULT NULL,
  PRIMARY KEY (`password_id`),
  KEY `idx_passwords_vault_id` (`vault_id`),
  KEY `idx_passwords_user_id` (`user_id`),
  CONSTRAINT `fk_passwords_vault` FOREIGN KEY (`vault_id`) REFERENCES `vaults` (`vault_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_passwords_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 4. Table: google_db (Google OAuth SSO Linkings)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `google_db` (
  `google_id` INT(11) NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `google_subject` VARCHAR(255) NOT NULL,
  `google_email` VARCHAR(255) NOT NULL,
  `google_name` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `last_login` DATETIME DEFAULT NULL,
  PRIMARY KEY (`google_id`),
  UNIQUE KEY `idx_google_subject` (`google_subject`),
  UNIQUE KEY `idx_google_email` (`google_email`),
  KEY `idx_google_user_id` (`user_id`),
  CONSTRAINT `fk_google_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 5. Table: email_otps (Email OTP Verification & Password Resets)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `email_otps` (
  `otp_id` INT(11) NOT NULL AUTO_INCREMENT,
  `email` VARCHAR(150) NOT NULL,
  `user_id` INT(11) DEFAULT NULL,
  `otp_hash` VARCHAR(255) NOT NULL,
  `purpose` ENUM('registration', 'password_reset', 'one_time_login') NOT NULL,
  `payload` TEXT DEFAULT NULL,
  `attempts` INT(11) NOT NULL DEFAULT 0,
  `max_attempts` INT(11) NOT NULL DEFAULT 5,
  `is_used` TINYINT(1) NOT NULL DEFAULT 0,
  `expires_at` DATETIME NOT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`otp_id`),
  KEY `idx_email_purpose` (`email`, `purpose`),
  KEY `idx_expires` (`expires_at`),
  KEY `idx_otp_user_id` (`user_id`),
  CONSTRAINT `fk_email_otps_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 6. Table: activity_logs
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `activity_logs` (
  `log_id` INT(11) NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `action` VARCHAR(100) NOT NULL,
  `details` TEXT DEFAULT NULL,
  `ip_address` VARCHAR(50) DEFAULT NULL,
  `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`),
  KEY `idx_activity_user_id` (`user_id`),
  CONSTRAINT `fk_activity_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 7. Table: encryption_keys
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `encryption_keys` (
  `key_id` INT(11) NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `salt` VARCHAR(255) NOT NULL,
  `encryption_key_hash` VARCHAR(255) NOT NULL,
  `algorithm` VARCHAR(50) DEFAULT 'AES-256',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`key_id`),
  KEY `idx_encryption_user_id` (`user_id`),
  CONSTRAINT `fk_encryption_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 8. Table: sessions
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `sessions` (
  `session_id` VARCHAR(128) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `token` VARCHAR(255) NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `ip_address` VARCHAR(50) DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`session_id`),
  KEY `idx_sessions_user_id` (`user_id`),
  CONSTRAINT `fk_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
