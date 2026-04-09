# TechPrep — CLAUDE.md

See PROJECT_CONTEXT.md for full vision, architecture, DB schema, and dev roadmap.

## Running the backend
```bash
cd /Users/victornessi/TechPrep
uvicorn backend.main:app --reload
```

## Migrations (Alembic)
```bash
# Apply all pending migrations
alembic upgrade head

# Generate a new migration after changing models.py
alembic revision --autogenerate -m "short description"

# Roll back one step
alembic downgrade -1
```

## Conventions
- All API routes prefixed with `/api/`
- Auth: JWT bearer tokens (7-day expiry), `SECRET_KEY` in `.env`
- DB session injected via `Depends(get_db)` from `backend.database`
- Current user injected via `Depends(get_current_user)` from `backend.auth`
- Every resource is scoped to `user_id` — never return another user's data
- Agent endpoints stream or return full JSON; no plain text responses
