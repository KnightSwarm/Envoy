<?php
/* Copyright 2013 by Sven Slootweg <admin@cryto.net>
 * 
 * This file is part of Envoy.
 * 
 * Envoy is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * Envoy is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with Envoy.  If not, see <http://www.gnu.org/licenses/>. */

if(!isset($_APP)) { die("Unauthorized."); }

$_CPHP = true;
$_CPHP_CONFIG = "../../config.json";
require("cphp/base.php");

/* TODO: I'm sure this autoloader stuff could be done nicer. */

function autoload_class($class_name) 
{
	global $_APP;
	
	$class_name = str_replace("\\", "/", strtolower($class_name));
	
	if(file_exists("classes/{$class_name}.php"))
	{
		require_once("classes/{$class_name}.php");
	}
}

spl_autoload_register('autoload_class');

/* Adapted from: https://github.com/php-fig/fig-standards/blob/master/accepted/PSR-0.md */
function autoload_psr0($className)
{
	$className = ltrim($className, '\\');
	$fileName  = '';
	$namespace = '';
	
	if ($lastNsPos = strrpos($className, '\\'))
	{
		$namespace = substr($className, 0, $lastNsPos);
		$className = substr($className, $lastNsPos + 1);
		$fileName  = str_replace('\\', DIRECTORY_SEPARATOR, $namespace) . DIRECTORY_SEPARATOR;
	}
	
	$fileName .= str_replace('_', DIRECTORY_SEPARATOR, $className) . '.php';

	include_once("lib" . DIRECTORY_SEPARATOR . $fileName);
}

spl_autoload_register('autoload_psr0');

use Monolog\Logger;
use Monolog\ErrorHandler;
use Monolog\Handler\StreamHandler;
use Monolog\Processor;

$log_level = empty($cphp_config->debug) ? Logger::INFO : Logger::DEBUG;

$logger = new Logger("api");
$logger->pushHandler(new StreamHandler("/etc/envoy/api.log", $log_level));
$logger->pushProcessor(new Processor\IntrospectionProcessor());
$logger->pushProcessor(new Processor\WebProcessor());
$logger->pushProcessor(new Processor\UidProcessor());
ErrorHandler::register($logger); /* Sets this logger as the default target for uncaught exceptions and errors */

require("include/exceptions.php");
require("include/signing.php");
require("lib/pbkdf2.php");
