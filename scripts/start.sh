#!/bin/sh
# Docker entrypoint — substitutes $PORT into nginx config then starts supervisord.
# Railway (and other PaaS) injects PORT at runtime. Default: 80.
set -e

PORT=${PORT:-80}
export PORT

# Substitute $PORT placeholder in nginx config template
envsubst '$PORT' < /etc/nginx/templates/app.conf.template \
                > /etc/nginx/conf.d/app.conf

# Remove default nginx site if present
rm -f /etc/nginx/conf.d/default.conf /etc/nginx/sites-enabled/default 2>/dev/null || true

echo "Starting platform on port $PORT ..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
