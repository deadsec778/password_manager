-- ==============================================================================
-- Migration 005: Seamless Upgrade from previous master branch
-- Ensures all newer columns and tables exist without crashing if already present
-- ==============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Ensure google_db table exists
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

-- 2. Ensure email_otps table exists
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

SET FOREIGN_KEY_CHECKS = 1;
