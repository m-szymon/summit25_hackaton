#!/bin/sh
: "${BACKEND_URL:=http://localhost:5000}"
export BACKEND_URL
echo "Using backend URL: $BACKEND_URL"
envsubst < proxy.conf.template.json > proxy.conf.json
exec ng serve "$@"