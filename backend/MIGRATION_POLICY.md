# Migration policy (Stage 2)

## Rule
All new schema changes (tables, columns, indexes, constraints) **must** be introduced via Alembic revisions under `backend/alembic/versions/`.

## Temporary backward-compat
`backend/main.py` still runs startup SQL fallbacks for old environments. This is temporary and will be removed after migration rollout is complete.

## Standard workflow
1. Create revision:
   ```bash
   cd backend
   alembic revision -m "describe change"
   ```
2. Implement `upgrade()` / `downgrade()`.
3. Apply locally:
   ```bash
   cd backend
   alembic upgrade head
   ```
4. Deploy only after migration passes in CI/staging.
