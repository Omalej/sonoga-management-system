#!/bin/sh
set -eu

DOMAIN="${1:-manage.sonogahotels.com}"
FAILED=0

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "OK: $1"
    else
        echo "MISSING: $1"
        FAILED=1
    fi
}

echo "Sonoga HMS server precheck for $DOMAIN"
check_command docker
if docker compose version >/dev/null 2>&1; then
    echo "OK: docker compose"
else
    echo "MISSING: docker compose plugin"
    FAILED=1
fi
check_command nginx
check_command certbot
check_command curl
check_command openssl

if getent ahostsv4 "$DOMAIN" >/dev/null 2>&1; then
    echo "OK: DNS resolves for $DOMAIN"
    getent ahostsv4 "$DOMAIN" | awk '{print "  -> " $1}' | sort -u
else
    echo "MISSING: DNS does not resolve for $DOMAIN"
    FAILED=1
fi

if [ "$FAILED" -ne 0 ]; then
    echo
    echo "Server precheck failed. Install the missing prerequisites and/or fix DNS before go-live."
    exit 1
fi

echo
 echo "Server precheck passed."
