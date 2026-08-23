# Sonoga HMS Initial Data Import

The first deployment seeds the Sonoga business units, default departments, positions, stores, and expense categories. Use the CSV templates in `data_templates/` to load real operating data after migrations are applied.

## Safety rules

1. Edit copies of the templates. The included rows are examples/placeholders only.
2. Run every file first with `--dry-run`.
3. Imports are idempotent: matching business keys are updated rather than duplicated.
4. If any row fails validation, the entire file is rolled back.
5. Use the exact business unit codes `HOTEL`, `WATER`, and `BREAD`.

## Recommended order

```bash
docker compose exec web python manage.py import_sonoga_data room-types /app/imports/room_types.csv --dry-run
docker compose exec web python manage.py import_sonoga_data rooms /app/imports/rooms.csv --dry-run
docker compose exec web python manage.py import_sonoga_data inventory-items /app/imports/inventory_items.csv --dry-run
docker compose exec web python manage.py import_sonoga_data factory-products /app/imports/factory_products.csv --dry-run
docker compose exec web python manage.py import_sonoga_data recipes /app/imports/recipes.csv --dry-run
docker compose exec web python manage.py import_sonoga_data recipe-lines /app/imports/recipe_lines.csv --dry-run
docker compose exec web python manage.py import_sonoga_data employees /app/imports/employees.csv --dry-run
```

After a successful dry run, repeat each command without `--dry-run`.

## Uploading CSV files to the container

Create an `imports` directory beside `docker-compose.yml`, put the completed CSVs there, and copy them into the running web container:

```bash
docker compose exec web mkdir -p /app/imports
docker cp imports/. "$(docker compose ps -q web)":/app/imports/
```

Then execute the import commands above.

## Final readiness check

```bash
docker compose exec web python manage.py sonoga_readiness --operational
```

Do not treat placeholder prices, salaries, recipes, or stock levels in the sample CSVs as real Sonoga data.
