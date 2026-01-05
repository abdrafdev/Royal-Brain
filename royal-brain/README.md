# Royal BrAIn™ — Monorepo
Day 1 deliverable: a sovereign foundation (deterministic backend core, explicit authority, auditable actions) that can later host the four interoperable engines and a future trust layer.

## Repo layout
- `backend/` — FastAPI sovereign core (auth, RBAC, audit)
- `frontend/` — Minimal institutional console (Next.js)
- `docs/` — Architecture, authority model, glossary

## Environment separation
This repo uses explicit environment files:
- `.env.dev`
- `.env.staging`

Set `RB_ENV` to select the environment.

## Backend quickstart (dev)
PowerShell:
1) Create venv and install deps:
   - `py -3.12 -m venv backend\\.venv`
   - `backend\\.venv\\Scripts\\python -m pip install -r backend\\requirements.txt`
2) Run migrations:
   - `$env:RB_ENV = "dev"`
   - `backend\\.venv\\Scripts\\alembic -c backend\\alembic.ini upgrade head`
3) Start API:
   - `$env:RB_ENV = "dev"`
   - `backend\\.venv\\Scripts\\uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload`

Health check: `GET http://127.0.0.1:8000/health`

### Default dev authority (bootstrap admin)
In `.env.dev` the backend can bootstrap an initial ADMIN on startup:
- Email: `admin@royalbrain.dev`
- Password: `change-me-now`

Change these values immediately for any non-local usage.

## Frontend quickstart (dev)
1) Install deps:
   - `cd frontend`
   - `npm install`
2) Start:
   - `$env:RB_ENV = "dev"`
   - `npm run dev`

Open: `http://localhost:3000`

## Docs
See `docs/architecture.md` and `docs/authority-model.md`.
