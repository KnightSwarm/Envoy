SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

INSERT INTO `api_keys` (`Id`, `UserId`, `Type`, `Description`, `ApiId`, `ApiKey`) VALUES
(1, 0, 0, 'Testing key', 'test', 'test');

INSERT INTO `api_permissions` (`Id`, `ApiKeyId`, `FqdnId`, `Type`) VALUES
(1, 1, 1, 100);

INSERT INTO `fqdns` (`Id`, `UserId`, `Fqdn`, `Name`, `Description`) VALUES
(1, 32, 'envoy.local', 'Envoy', 'Local Envoy testing FQDN.');

INSERT INTO `rooms` (`Id`, `Node`, `Description`, `OwnerId`, `FqdnId`, `LastUserCount`, `IsPrivate`, `IsArchived`, `CreationDate`, `ArchivalDate`, `Name`) VALUES
(1, 'testingroom13', 'Testing room.', 1, 1, 0, 0, 0, '2013-10-08 19:11:16', NULL, 'TestingRoom13'),
(2, 'sometest', '', 0, 1, 0, 1, 0, '2013-10-15 13:13:27', NULL, 'Some Testing Room'),
(3, 'sometest2', '', 32, 1, 0, 1, 0, '2013-10-15 14:46:59', NULL, 'Some Testing Room'),
(4, 'sometest3', 'Testing description for this newly created room...', 32, 1, 0, 0, 0, '2013-10-15 14:47:37', NULL, 'Another testing room!'),
(5, 'sometest4', 'Testing description for this newly created room...', 32, 1, 0, 1, 0, '2013-10-15 19:10:41', NULL, 'Some Testing Room'),
(6, 'sometest5', 'Testing description for this newly created room...', 32, 1, 0, 1, 0, '2013-10-15 19:13:00', NULL, 'Some Testing Room');

INSERT INTO `users` (`Id`, `Username`, `Fqdn`, `Hash`, `Salt`, `Active`, `FqdnId`, `Nickname`, `EmailAddress`, `FirstName`, `LastName`, `JobTitle`, `MobileNumber`, `Status`, `StatusMessage`) VALUES
(32, 'testuser', 'envoy.local', 'xg2UsUkCz4WGfPvfBMbPzfzQSlAb59IOlY0QTC7IjkQ=', 'yXnvvTcGgLAWIkSoNQZAqPXeO+c8J2Ss', 1, 1, 'testuser', 'testuser@cryto.net', 'Test', 'User', 'Dummy', '0031612345678', 4, ''),
(33, 'testuser2', 'envoy.local', 'Ag2mjqaE4w+8Nj2erVGxNmbylwMMz5u3VKCqGyEYhOU=', 'jTOyki+W7V9jlA5I+JGU9VfRxls7QONR', 1, 1, 'testuser2', 'testuser2@cryto.net', 'Second', 'User', 'Dummy', '0031612345678', 4, ''),
(34, 'asdfasdfasdf', '', '', '', 1, 2, 'asdf', '', '', '', '', '', 0, '');

INSERT INTO `user_permissions` (`Id`, `UserId`, `FqdnId`, `Type`) VALUES
(1, 32, 1, 100);
