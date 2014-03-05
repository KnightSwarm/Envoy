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

function sign_request($signing_key, $verb, $uri, $get_data, $post_data)
{
	$sts = ""; /* Start out with an empty STS. */
	$sts .= strtoupper($verb) . "\n"; /* Append the request method (HTTP verb) in uppercase, and append a newline. */
	$uri = ends_with($uri, "/") ? substr($uri, 0, strlen($uri) - 1) : $uri; /* Remove the trailing slash from the URI if it exists. */
	$sts .= $uri . "\n"; /* Append the requested URI, in the form /some/thing, and append a newline. */
	
	/* GET data is a little more complicated... We need to sort the POST data by
	 * array key initially - however, if multiple values exist for a key (as is the case
	 * for GET field arrays), the second sorting criterium is the value. All sorting
	 * should be case-insensitive. After sorting, a query string should be built from
	 * the sorted GET data. Spaces are encoded as +. A newline is appended
	 * afterwards. */
	
	uksort($get_data, function($a, $b) { return strcasecmp($a, $b); });
	foreach($get_data as $key => &$values)
	{
		if(is_array($values))
		{
			usort($values, function($a, $b) { return strcasecmp($a, $b); });
		}
	}
	$sts .= http_build_query($get_data) . "\n";
	
	/* POST data is handled basically the same way. Don't forget the trailing
	 * newline! */
	uksort($post_data, function($a, $b) { return strcasecmp($a, $b); });
	foreach($post_data as $key => &$values)
	{
		if(is_array($values))
		{
			usort($values, function($a, $b) { return strcasecmp($a, $b); });
		}
	}
	$sts .= http_build_query($post_data) . "\n";
	
	/* When done building the STS, we sign it and return the base64-encoded version.
	 * HMAC + SHA512 is to be used. */
	return base64_encode(hash_hmac("sha512", $sts, $signing_key, true));
}

function verify_request($authorization_string, $signing_key, $verb, $uri, $get_data, $post_data)
{
	return ($authorization_string === sign_request($signing_key, $verb, $uri, $get_data, $post_data));
}
