# Deployment — Morocco Spatial Dashboard

How to run the stack for development and production-like environments.

## Development (local)

1. **Database and backend**
   ```bash
   cp .env.example .env
   docker compose up -d
   ```
   For local dev, optionally restore a POI dump (see [RUNBOOK.md](RUNBOOK.md)). Then open API docs: http://localhost:8000/docs

2. **Dashboard**
   ```bash
   cd frontend && npm install && npm run dev
   ```
   Open http://localhost:3000

3. **Optional: backend without Docker**
   ```bash
   docker compose up -d db
   # Optionally restore dump for local data, then:
   cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
   ```
   Set `DATABASE_URL` in `.env` (e.g. `postgresql://poi_user:poi_password@localhost:5432/poi_db`).

## Production-like (Docker)

- **Backend + DB:** `docker compose up -d` runs both. Ensure `DATABASE_URL` points to your Postgres. In production the DB is already set up (no restore); for local dev you may restore a dump once.
- **Frontend:** Build and serve the React app (e.g. `cd frontend && npm run build`), then serve the `dist/` folder with nginx or another static server. Configure the server so the app can call the backend API (same origin or CORS). Set `VITE_API_URL` at build time to the public API URL so the dashboard calls the correct host.
- **CORS:** Set `CORS_ORIGINS` in the backend env to the origin(s) of the dashboard (e.g. `https://dashboard.example.com`). See `.env.example`.

## Environment summary

| Variable       | Used by   | Description |
|----------------|-----------|-------------|
| `DATABASE_URL` | Backend   | Postgres connection string. Production: existing DB; local: match Postgres (and optional dump). |
| `LOG_LEVEL`    | Backend   | Log level (info, debug, etc.). |
| `CORS_ORIGINS` | Backend   | Comma-separated allowed origins for the API. |
| `VITE_API_URL` | Frontend  | Optional; API base URL at build time (e.g. `https://api.example.com`). |

No secrets in the repo; provide real values via `.env` (not committed) or the deployment platform’s config.
