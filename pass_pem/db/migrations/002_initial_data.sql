/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-11.8.3-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: password
-- ------------------------------------------------------
-- Server version	11.8.3-MariaDB-1+b1 from Debian

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Dumping data for table `activity_logs`
--

LOCK TABLES `activity_logs` WRITE;
/*!40000 ALTER TABLE `activity_logs` DISABLE KEYS */;
set autocommit=0;
/*!40000 ALTER TABLE `activity_logs` ENABLE KEYS */;
UNLOCK TABLES;
commit;

--
-- Dumping data for table `encryption_keys`
--

LOCK TABLES `encryption_keys` WRITE;
/*!40000 ALTER TABLE `encryption_keys` DISABLE KEYS */;
set autocommit=0;
/*!40000 ALTER TABLE `encryption_keys` ENABLE KEYS */;
UNLOCK TABLES;
commit;

--
-- Dumping data for table `passwords`
--

LOCK TABLES `passwords` WRITE;
/*!40000 ALTER TABLE `passwords` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `passwords` VALUES
(8,2,5,'password Database ','password','gAAAAABpIvoJuWnAmdH_fQSiAnE3HjmxaJlJIvRWDWUtKyGX9QXinm4-LsXJivvdeH4pexCpdug8ego1ZEy3CJV1nITD6iiIrw==',NULL,NULL,NULL,NULL,'127.0.0.1:3306','db=password ','2025-11-23 17:41:53','2025-11-23 19:00:34',NULL,1),
(9,3,2,'asfa','asfasf',NULL,'gAAAAABpIwRCJFvjSaBTXyOpcANqsk3JdlXSDD-9zj3shQUULtY_cPbQqQ7qkmUw3mXD6brNsy-vs5nKsNJji5vSGVypm4DhQw==','gAAAAABpIwRCMCZWCpdin84_vs2s1P23VXUhEFwm6uKR6vRoUqPrISBrKLcXVu9geRcTDBTAr_wNE-J_m9KchYE3e_raQceg0g==',NULL,NULL,'asfasf','asfasf','2025-11-23 18:25:30','2025-11-24 01:27:16',NULL,1),
(10,2,5,'asfasf','asdfgasdg',NULL,'gAAAAABpIwRbgjKaNtnsQxym2tLw8cRns596TeP9XN9HiOXhUauRWCkp3TkIKOAQbYFNz3M1OceN4c9LyI-u11hMcgryT2GviQ==','gAAAAABpIwRbVXqJOoVxf-6gSBMeexQKbXQM3zW8eSiIm4z-E87XIVE9_osNofyBn61D6UWSZQ-M_c1RzCYInMAd6qOsGD3s_A==',NULL,NULL,'adfsgasdg','asdfgasdg','2025-11-23 18:25:55','2025-11-23 19:00:35',NULL,1),
(11,2,5,'boo','boo',NULL,'gAAAAABpJLWqEtKYh-tSuwlLb3eKXHIIN3IV5pHDQkoIRhRThkXQmiied8R3jlK9qGuYPnf4DVmdMC3cXQ5Bl_z5jugRsb7Kjg==','gAAAAABpJLWqDD4PSxLKexmIz3defErCGBwhdCjdsuaRsKECtyFBCq3qDqLQ3TgVzBR0RLQOufTNXVUpHBI9FafFLv7unmJdpw==',NULL,NULL,'www.pemlix.in','pemlix','2025-11-25 01:14:42',NULL,NULL,0);
/*!40000 ALTER TABLE `passwords` ENABLE KEYS */;
UNLOCK TABLES;
commit;

--
-- Dumping data for table `sessions`
--

LOCK TABLES `sessions` WRITE;
/*!40000 ALTER TABLE `sessions` DISABLE KEYS */;
set autocommit=0;
/*!40000 ALTER TABLE `sessions` ENABLE KEYS */;
UNLOCK TABLES;
commit;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `users` VALUES
(2,'admin','admin@example.com','$2b$12$8/TSMbP2nQahjr6gNzRXj.cDliFO2o8SR4EpplYRfMoDKxXQpII1.','a6e6dee70c64ae08fb57a91f8fbf06da','2025-11-23 16:00:05','2025-11-25 01:36:35','active',0,'admin'),
(5,'sayan','sayan@example.com','$2b$12$z61yzew7SPz9ssmYrFX09etLxOUdokSO9sFDf9oHL25f5feZKhnBy','0d6939556e3bdad3ea46f78e72ba8409','2025-11-23 16:04:23','2025-11-25 01:14:13','active',0,'user'),
(6,'aanan','aanan@pemlix.in','$2b$12$.Mx5KNu1uie98IjiWf4kX.132WfoKa5RmR3xD9QRPh0Y5RtiBISTC','7314b8fb80d99e1c307f795e4e2902ee','2025-11-25 01:05:05','2025-11-25 01:05:30','active',0,'user'),
(7,'moumita','mou@pemlix.in','$2b$12$qeV6rvtZaGAQJmjQ0PSoeuYla0Ii6gJAwhTDNXpx6PsmscdPMdJMq',NULL,'2025-11-25 01:48:05',NULL,'active',0,'user');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
commit;

--
-- Dumping data for table `vaults`
--

LOCK TABLES `vaults` WRITE;
/*!40000 ALTER TABLE `vaults` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `vaults` VALUES
(2,5,'Office','Created to Store Office passwords','2025-11-23 17:33:37',NULL,0),
(3,2,'admin','admin','2025-11-23 18:16:02',NULL,0);
/*!40000 ALTER TABLE `vaults` ENABLE KEYS */;
UNLOCK TABLES;
commit;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2025-11-25 12:16:50
