SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

CREATE TABLE IF NOT EXISTS `affiliations` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `UserId` bigint(20) unsigned NOT NULL,
  `RoomId` bigint(20) unsigned NOT NULL,
  `Affiliation` tinyint(3) unsigned NOT NULL,
  PRIMARY KEY (`Id`),
  UNIQUE KEY `Id` (`Id`),
  KEY `UserId` (`UserId`,`RoomId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `api_keys` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `UserId` bigint(20) unsigned NOT NULL,
  `Type` tinyint(3) unsigned NOT NULL,
  `Description` varchar(300) CHARACTER SET latin1 NOT NULL,
  `ApiId` varchar(16) CHARACTER SET latin1 NOT NULL,
  `ApiKey` varchar(24) CHARACTER SET latin1 NOT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `api_permissions` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ApiKeyId` bigint(20) unsigned NOT NULL,
  `FqdnId` bigint(20) unsigned NOT NULL,
  `Type` int(11) NOT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `fqdns` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `UserId` bigint(20) unsigned NOT NULL,
  `Fqdn` varchar(256) CHARACTER SET latin1 NOT NULL,
  `Name` varchar(150) CHARACTER SET latin1 NOT NULL,
  `Description` varchar(550) CHARACTER SET latin1 NOT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `fqdn_settings` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `FqdnId` bigint(20) unsigned NOT NULL,
  `Key` varchar(50) NOT NULL,
  `Value` varchar(150) NOT NULL,
  `LastModified` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `log_events` (
  `Id` varchar(36) NOT NULL,
  `Type` tinyint(3) unsigned NOT NULL,
  `Sender` varchar(1514) NOT NULL,
  `Recipient` varchar(1514) DEFAULT NULL,
  `Date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `Event` smallint(5) unsigned NOT NULL,
  `Extra` varchar(512) DEFAULT NULL,
  `Stanza` text,
  `OrderId` bigint(20) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`Id`),
  UNIQUE KEY `OrderId` (`OrderId`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `log_messages` (
  `Id` varchar(36) NOT NULL,
  `Type` smallint(5) unsigned NOT NULL,
  `Sender` varchar(1514) NOT NULL,
  `Recipient` varchar(1514) NOT NULL,
  `Date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `Message` mediumtext NOT NULL,
  `Stanza` text,
  `OrderId` bigint(20) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`Id`),
  UNIQUE KEY `OrderId` (`OrderId`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `presences` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `UserId` bigint(20) unsigned NOT NULL,
  `Resource` varchar(1023) NOT NULL,
  `RoomId` bigint(20) unsigned NOT NULL,
  `Nickname` varchar(1023) NOT NULL,
  `Role` tinyint(3) unsigned NOT NULL,
  `FqdnId` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`Id`),
  KEY `FqdnId` (`FqdnId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `presences_old` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `UserJid` varchar(1514) NOT NULL,
  `RoomJid` varchar(1514) NOT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `rooms` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `Node` varchar(80) NOT NULL,
  `Description` text NOT NULL,
  `OwnerId` bigint(20) unsigned NOT NULL,
  `FqdnId` bigint(20) unsigned NOT NULL,
  `LastUserCount` mediumint(8) unsigned NOT NULL,
  `IsPrivate` tinyint(1) NOT NULL,
  `IsArchived` tinyint(1) NOT NULL,
  `CreationDate` timestamp NULL DEFAULT NULL,
  `ArchivalDate` timestamp NULL DEFAULT NULL,
  `Name` varchar(80) NOT NULL,
  PRIMARY KEY (`Id`),
  KEY `FqdnId` (`FqdnId`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `users` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `Username` varchar(256) CHARACTER SET latin1 NOT NULL,
  `Fqdn` varchar(256) CHARACTER SET latin1 NOT NULL,
  `Hash` varchar(44) CHARACTER SET latin1 NOT NULL,
  `Salt` varchar(32) CHARACTER SET latin1 NOT NULL,
  `Active` tinyint(1) NOT NULL,
  `FqdnId` bigint(20) unsigned NOT NULL,
  `Nickname` varchar(64) CHARACTER SET latin1 NOT NULL,
  `EmailAddress` varchar(320) CHARACTER SET latin1 NOT NULL,
  `FirstName` varchar(50) CHARACTER SET latin1 NOT NULL,
  `LastName` varchar(50) CHARACTER SET latin1 NOT NULL,
  `JobTitle` varchar(50) CHARACTER SET latin1 NOT NULL,
  `MobileNumber` varchar(45) CHARACTER SET latin1 NOT NULL,
  `Status` tinyint(4) NOT NULL,
  `StatusMessage` varchar(200) NOT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `user_permissions` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `UserId` bigint(20) unsigned NOT NULL,
  `FqdnId` bigint(20) unsigned NOT NULL,
  `Type` int(11) NOT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `user_settings` (
  `Id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `UserId` bigint(20) unsigned NOT NULL,
  `Key` varchar(50) NOT NULL,
  `Value` varchar(150) NOT NULL,
  `LastModified` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
