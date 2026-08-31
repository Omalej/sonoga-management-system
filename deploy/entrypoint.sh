#!/bin/sh
set -eu

APP_MIGRATION_TARGETS="accounts organization hr hotel inventory factory commercial procurement finance payroll control"

python - <<'PY'
import os
import time
import psycopg

params = {
    "dbname": os.getenv("POSTGRES_DB", "sonoga_hms"),
    "user": os.getenv("POSTGRES_USER", "sonoga"),
    "password": os.getenv("POSTGRES_PASSWORD", "change-me"),
    "host": os.getenv("POSTGRES_HOST", "db"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}

for attempt in range(30):
    try:
        with psycopg.connect(**params) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        print("PostgreSQL is ready.")
        break
    except Exception as exc:
        if attempt == 29:
            raise
        print(f"Waiting for PostgreSQL ({attempt + 1}/30): {exc}")
        time.sleep(2)
PY

AUTO_MIGRATIONS="${SONOGA_AUTO_MAKEMIGRATIONS:-False}"

case "$(printf '%s' "$AUTO_MIGRATIONS" | tr '[:upper:]' '[:lower:]')" in
  1|true|yes|on)
    echo "Generating Sonoga migrations because SONOGA_AUTO_MAKEMIGRATIONS is enabled."
    python manage.py makemigrations $APP_MIGRATION_TARGETS --noinput
    ;;
  *)
    python - <<'PY'
from pathlib import Path

apps = "accounts organization hr hotel inventory factory commercial procurement finance payroll control".split()
missing = []

for app in apps:
    migration_dir = Path(app) / "migrations"
    migrations = list(migration_dir.glob("0*.py")) if migration_dir.exists() else []
    if not migrations:
        missing.append(app)

if missing:
    joined = ", ".join(missing)
    raise SystemExit(
        "Initial application migrations are missing for: " + joined
    )

print("Application migration files detected.")
PY
    ;;
esac

python manage.py migrate --noinput

python manage.py bootstrap_sonoga

python manage.py seed_sonoga_defaults

python manage.py create_receptionist

python manage.py collectstatic --noinput

python manage.py sonoga_readiness

exec "$@"

python manage.py create_receptionist
