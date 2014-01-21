UPDATE user SET `host` = '%' WHERE `user` = 'root' AND `host` = 'localhost';
FLUSH PRIVILEGES;
