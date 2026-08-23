#!/bin/sh
set -eu

DOMAIN="${SONOGA_DOMAIN:-manage.sonogahotels.com}"
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BOOTSTRAP_CONF="/etc/nginx/sites-available/sonoga-hms"
ENABLED_CONF="/etc/nginx/sites-enabled/sonoga-hms"

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: run this script as root because it configures host Nginx and Certbot."
    exit 2
fi

cd "$PROJECT_DIR"

./deploy/server_precheck.sh "$DOMAIN"

if [ ! -f .env ]; then
    echo "Creating production .env for $DOMAIN..."
    python3 deploy/create_env.py --host "$DOMAIN"
fi

# The application stack must be healthy on localhost before TLS is requested.
./deploy/first_deploy.sh

# Start with an HTTP-only config so Nginx can load before a certificate exists.
sed "s/manage\.sonogahotels\.com/$DOMAIN/g" deploy/host_nginx_http_bootstrap.conf.example > "$BOOTSTRAP_CONF"
ln -sfn "$BOOTSTRAP_CONF" "$ENABLED_CONF"
nginx -t
systemctl reload nginx

# Certbot edits the active Nginx virtual host and enables redirect to HTTPS.
certbot --nginx --redirect -d "$DOMAIN"

nginx -t
systemctl reload nginx

python3 deploy/post_deploy_verify.py --base-url "https://$DOMAIN"

echo
echo "Sonoga HMS HTTPS activation completed for https://$DOMAIN"
echo "Create the first Super Admin if not already created:"
echo "  docker compose exec web python manage.py createsuperuser"
echo "Then load real Sonoga operating data and run:"
echo "  docker compose exec web python manage.py sonoga_readiness --operational"
