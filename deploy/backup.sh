#!/bin/sh
set -eu
umask 077

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
  echo "ERROR: .env is required." >&2
  exit 2
fi

set -a
. ./.env
set +a

BACKUP_DIR=${SONOGA_BACKUP_DIR:-"$PROJECT_DIR/backups"}
RETENTION_DAYS=${SONOGA_BACKUP_RETENTION_DAYS:-14}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST="$BACKUP_DIR/$STAMP"
mkdir -p "$DEST"

DB_FILE="$DEST/sonoga_hms_${STAMP}.dump"
MEDIA_FILE="$DEST/sonoga_media_${STAMP}.tar.gz"
MANIFEST="$DEST/manifest.txt"

printf 'Creating PostgreSQL backup...\n'
docker compose exec -T db pg_dump \
  -U "${POSTGRES_USER:-sonoga}" \
  -d "${POSTGRES_DB:-sonoga_hms}" \
  --format=custom --no-owner --no-acl > "$DB_FILE"

printf 'Creating media backup...\n'
docker compose exec -T web sh -c 'tar -C /app/media -czf - .' > "$MEDIA_FILE"

{
  echo "Sonoga HMS backup"
  echo "created_utc=$STAMP"
  echo "database=${POSTGRES_DB:-sonoga_hms}"
  echo "db_file=$(basename "$DB_FILE")"
  echo "media_file=$(basename "$MEDIA_FILE")"
  sha256sum "$DB_FILE" "$MEDIA_FILE"
} > "$MANIFEST"

find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime "+$RETENTION_DAYS" -exec rm -rf {} + 2>/dev/null || true

printf 'Backup complete: %s\n' "$DEST"
