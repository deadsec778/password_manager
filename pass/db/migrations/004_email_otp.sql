-- Migration 004: Email OTPs table for registration verification and password reset / one-time login
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
  CONSTRAINT `email_otps_user_fk` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
