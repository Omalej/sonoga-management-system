#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
    echo "ERROR: .env does not exist."
    echo "Create it first with: python deploy/create_env.py"
    exit 2
fi

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.migrations.yml"
APPS="accounts organization hr hotel inventory factory commercial procurement finance payroll control"

echo "[1/6] Running source preflight..."
python deploy/preflight.py

echo "[2/6] Building the Django image..."
$COMPOSE build web

echo "[3/6] Generating initial migration files into the project..."
$COMPOSE run --rm --entrypoint python web manage.py makemigrations $APPS --noinput

echo "[4/6] Verifying migration files..."
python deploy/preflight.py --require-migrations

echo "[5/6] Starting PostgreSQL, Django and nginx..."
docker compose up -d --build

echo "[6/6] Running Django and Sonoga readiness checks..."
docker compose exec web python manage.py check --deploy
docker compose exec web python manage.py sonoga_readiness

echo
echo "First deployment bootstrap completed."
echo "Next: docker compose exec web python manage.py createsuperuser"
