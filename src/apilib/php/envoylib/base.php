<?php
/*
 * Envoy is more free software. It is licensed under the WTFPL, which
 * allows you to do pretty much anything with it, without having to
 * ask permission. Commercial use is allowed, and no attribution is
 * required. We do politely request that you share your modifications
 * to benefit other developers, but you are under no enforced
 * obligation to do so :)
 * 
 * Please read the accompanying LICENSE document for the full WTFPL
 * licensing text.
 */

namespace EnvoyLib;

class ApiException extends \Exception {} 

class NotFoundException extends ApiException {}
class BadDataException extends ApiException {}
class NotAuthorizedException extends ApiException {}
class NotAuthenticatedException extends ApiException {}
class UnknownException extends ApiException {}
class AlreadyExistsException extends ApiException {}
class InvalidArgumentException extends ApiException {}

require("util.php");

require("api.php");
require("apiobject.php");
require("user.php");
