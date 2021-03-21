#!/usr/bin/bash
set -e

podman build -f Dockerfile -t bcs_api .

podman run -d \
  --publish '58080:8080' \
  --restart 'always' \
  --name prod_bcs_api \
  bcs_api


API_IP=$( podman inspect prod_bcs_api --format '{{.NetworkSettings.IPAddress}}')

podman run -d \
  --publish '50080:80' \
  --volume './default.nginx:/etc/nginx/conf.d/default.conf' \
  --volume './html:/var/www' \
  --restart 'always' \
  --add-host "api:${API_IP}" \
  --name prod_bcs_nginx \
  nginx:1.19.6-alpine

