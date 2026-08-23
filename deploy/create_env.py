#!/usr/bin/env python3
"""Create a production .env with generated secrets; never overwrites an existing file."""
from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / ".env"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="manage.sonogahotels.com")
    args = parser.parse_args()

    if TARGET.exists():
        raise SystemExit(".env already exists; refusing to overwrite it.")

    host = args.host.strip()
    if not host:
        raise SystemExit("Host cannot be empty.")

    values = {
        "DJANGO_ENV": "production",
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
        "DJANGO_DEBUG": "False",
        "DJANGO_ALLOWED_HOSTS": host,
        "DJANGO_CSRF_TRUSTED_ORIGINS": f"https://{host}",
        "DJANGO_LOG_LEVEL": "INFO",
        "POSTGRES_DB": "sonoga_hms",
        "POSTGRES_USER": "sonoga",
        "POSTGRES_PASSWORD": secrets.token_urlsafe(36),
        "POSTGRES_HOST": "db",
        "POSTGRES_PORT": "5432",
        "POSTGRES_CONN_MAX_AGE": "60",
        "DJANGO_SECURE_SSL_REDIRECT": "True",
        "DJANGO_SESSION_COOKIE_SECURE": "True",
        "DJANGO_CSRF_COOKIE_SECURE": "True",
        "DJANGO_TRUST_X_FORWARDED_PROTO": "True",
        "DJANGO_SECURE_HSTS_SECONDS": "31536000",
        "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS": "False",
        "DJANGO_SECURE_HSTS_PRELOAD": "False",
        "SONOGA_WORDPRESS_API_KEY": secrets.token_urlsafe(48),
        "SONOGA_WORDPRESS_USER": "wordpress-sync",
        "SONOGA_WORDPRESS_REQUIRE_SIGNATURE": "True",
        "SONOGA_WORDPRESS_SIGNATURE_TOLERANCE": "300",
        "SONOGA_WORDPRESS_ALLOWED_IPS": "",
        "SONOGA_WORDPRESS_TRUST_PROXY_IP_HEADERS": "True",
        "SONOGA_AUTO_MAKEMIGRATIONS": "False",
        "SONOGA_HTTP_PORT": "8080",
        "SONOGA_BACKUP_RETENTION_DAYS": "14",
    }
    TARGET.write_text("\n".join(f"{k}={v}" for k, v in values.items()) + "\n", encoding="utf-8")
    os.chmod(TARGET, 0o600)
    print(f"Created {TARGET}")
    print("Keep this file private. The WordPress webhook secret is SONOGA_WORDPRESS_API_KEY in this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
