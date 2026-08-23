#!/bin/sh
set -eu

usage() {
  echo "Usage: $0 --database /path/to/backup.dump [--media /path/to/media.tar.gz] --confirm" >&2
  exit 2
}

DB_DUMP=""
MEDIA_ARCHIVE=""
CONFIRM=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --database) [ "$#" -ge 2 ] || usage; DB_DUMP=$2; shift 2 ;;
    --media) [ "$#" -ge 2 ] || usage; MEDIA_ARCHIVE=$2; shift 2 ;;
    --confirm) CONFIRM=yes; shift ;;
    *) usage ;;
  esac
done

[ -n "$DB_DUMP" ] && [ -f "$DB_DUMP" ] || usage
[ "$CONFIRM" = yes ] || { echo "ERROR: --confirm is required because restore replaces the live database." >&2; exit 3; }
if [ -n "$MEDIA_ARCHIVE" ] && [ ! -f "$MEDIA_ARCHIVE" ]; then
  echo "ERROR: media archive not found: $MEDIA_ARCHIVE" >&2
  exit 2
fi

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
[ -f .env ] || { echo "ERROR: .env is required." >&2; exit 2; }
set -a
. ./.env
set +a

DB_NAME=${POSTGRES_DB:-sonoga_hms}
DB_USER=${POSTGRES_USER:-sonoga}

echo "Stopping application traffic..."
docker compose stop nginx web || true
docker compose up -d db

echo "Replacing PostgreSQL database: $DB_NAME"
docker compose exec -T db psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();"
docker compose exec -T db dropdb -U "$DB_USER" --if-exists "$DB_NAME"
docker compose exec -T db createdb -U "$DB_USER" "$DB_NAME"
cat "$DB_DUMP" | docker compose exec -T db pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl --exit-on-error

if [ -n "$MEDIA_ARCHIVE" ]; then
  echo "Restoring media files..."
  cat "$MEDIA_ARCHIVE" | docker compose run --rm --no-deps -T --entrypoint sh web \
    -c 'find /app/media -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar -C /app/media -xzf -'
fi

echo "Starting Sonoga HMS..."
docker compose up -d

docker compose exec web python manage.py migrate --noinput
docker compose exec web python manage.py sonoga_readiness

echo "Restore completed. Verify /ready/ and key business records before reopening staff access."
