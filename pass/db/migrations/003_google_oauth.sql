CREATE TABLE IF NOT EXISTS `google_db` (
  `google_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `google_subject` varchar(255) NOT NULL,
  `google_email` varchar(255) NOT NULL,
  `google_name` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `last_login` datetime DEFAULT NULL,
  PRIMARY KEY (`google_id`),
  UNIQUE KEY `google_subject` (`google_subject`),
  UNIQUE KEY `google_email` (`google_email`),
  CONSTRAINT `google_db_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
