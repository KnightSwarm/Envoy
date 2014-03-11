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

if($sApiKeypair->HasServiceAdministrativeAccess())
{
	/* Return a list of all the FQDNs. */
	$result = Fqdn::CreateFromQuery("SELECT * FROM fqdns");
	$sFqdns = array();
	
	foreach($result as $sFqdn)
	{
		$sFqdns[] = array(
			"id" => $sFqdn->sId,
			"fqdn" => $sFqdn->sFqdn /* The FQDN 'hostname' */
		);
	}
	
	$sResponse = $sFqdns;
}
else
{
	/* The user does not have administrative access. We'll only return
	 * the FQDN that the user belongs to himself. */
	$sResponse = array(
		array(
			"id" => $sApiKeypair->sUser->sFqdn->sId,
			"fqdn" => $sApiKeypair->sUser->sFqdn->sFqdn
		)
	);
}
