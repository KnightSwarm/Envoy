#!/bin/bash
sass --watch scss/:Envoy\ Client/Resources/css/ > sasswatch.log 2> sasswatch.err &
echo $! > sasswatch.pid
