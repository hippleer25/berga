# Berga — AGENTS.md

- Berga is a RSS reader with AI-powered recommendations, clustering, and chat (codenamed "Mota").
- Berga is a FOSS project and should be able to run even inside local home servers.
- The ideia is to build a very fast and sophisticated RSS reader powered with AI and algorithm, everything under the control of the user.

## Architecture

- **`backend/`** — Python 3.12 FastAPI app (port 5746). Two processes via supervisord:
  - `uvicorn` API server (`main.py` entrypoint)
  - `arq` background worker (`workers/settings.WorkerSettings`) for feed refresh, clustering, publisher-freq recalc
- **`frontend/`** — SvelteKit 5 + Svelte 5 app with `adapter-static` (SPA mode, fallback `index.html`). Tailwind CSS v4 + DaisyUI v5. LightningCSS transformer.
- **Infrastructure** — Docker Compose: MySQL 8, Qdrant (vector DB), Redis 7 (arq broker + cache), backend, frontend

## Dev Commands

```sh
# Full stack (all services)
docker compose up --build

# Frontend only (local dev, proxies /api → backend:5746)
docker build berga_front

# Backend only (needs MySQL, Qdrant, Redis running)
dobker build berga_api

# Dependency audit (run periodically)
pip-audit -r backend/requirements.lock          # Python vulnerability check
cd frontend && npm audit                         # JS vulnerability check
```


## Key Config & Environment

- All env vars live in `.env` at repo root (loaded by docker-compose for the backend container)
- **Required env vars**: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `QDRANT_HOST`, `QDRANT_PORT`, `REDIS_HOST`, `EMBEDDING_MODEL_NAME`, `SECRET_KEY`
- `EMBEDDING_MODEL_NAME` must be set or the backend crashes at import time (`intelligence/embeddings.py` enforces this)
- `EMBEDDING_DESCRIPTION_CHARS` controls how much of the article description is included in the embedding vector (0 = title only, 200 = recommended). Changing this value after articles are already indexed requires running the `reembed_all` job to update existing vectors.
- LLM calls go through LiteLLM — model and API key set via `CLUSTER_LLM_*` and `CHATBOT_LLM_*` env vars
- Vite dev server proxies `/api` → `API_TARGET` (default `http://backend:5746`), stripping the `/api` prefix

## Backend Structure

| Path | Purpose |
|---|---|
| `main.py` | FastAPI app, all route definitions, lifespan (DB init, arq pool) |
| `auth/` | Registration, login (bcrypt + JWT), token verification |
| `database/init_db.py` | MySQL pool + schema creation (idempotent, auto-migrates) |
| `database/qdrant_utils.py` | Qdrant index helpers, payload indexes, publisher_freq |
| `rss/parser.py` | Feed parsing + storage |
| `rss/schedule.py` | User-scoped feed refresh orchestration |
| `intelligence/recommendations.py` | Three-tier ranking engine (personalised → cold-start → chronological) |
| `intelligence/embeddings.py` | SentenceTransformer singleton (ONNX int8 preferred), Qdrant client singleton |
| `intelligence/cluster.py` | Weekly event clustering via LLM |
| `intelligence/similar.py` | Similar-article search via Qdrant |
| `intelligence/affinity.py` | User affinity analysis and boost controls |
| `mota/chat.py` | AI chat handler — tool calling with search fallback, deep reading |
| `mota/article_resume.py` | Article summarization (streaming SSE) |
| `workers/tasks.py` | arq job definitions + WorkerSettings (cron every 6h for feeds, 6h for events, daily publisher freq) |

## Frontend Structure

- `src/routes/` — SvelteKit pages. Tab-based layout under `(tabs)/`
- `src/lib/components/` — Reusable Svelte components
- `src/lib/stores/` — Svelte stores
- `src/lib/i18n/` — svelte-i18n setup (locales in `src/lib/locales/`)
- `src/lib/tabs/` — Tab navigation components
- Auth cookies: `token` (httponly, samesite=lax) set by `/api/login`

## Gotchas

- **Frontend is SPA, not SSR** — `adapter-static` with `fallback: 'index.html'`. All routes must work client-side.
- **No tests configured** — no test runner or test files found in either frontend or backend.
- **`tt.py`** is a debug helper (prints Qdrant payload keys), called in the `/api/chat` route — not production code.
- **Schema migrations are inline** — `database/init_db.py` auto-creates tables and runs column migrations on startup. No migration files or CLI.
- **`workers/settings.py` defines a duplicate `WorkerSettings`** — the canonical one is at the bottom of `workers/tasks.py` (with cron_jobs). The one in `settings.py` is stale.
- **Root `package.json`** is vestigial (only tailwindcss deps, no scripts). All real frontend work is in `frontend/`.
- **Docker Compose frontend service** uses `node:20-slim` + `npm ci && npm run dev` (dev mode), not the multi-stage Dockerfile. The Dockerfile is for production builds (nginx serving static files).
- **Backend port** is 5746 (not a common port). Frontend dev proxy targets this.
- **API prefix**: Frontend calls `/api/*`, Vite proxy strips `/api` before forwarding to backend (backend routes do NOT have `/api` prefix in their decorators — they already include it).
- **Comments in .env** have spaces around `=`** (e.g. `CACHE_KEY = "weekly_events_cache"`) which may cause parsing issues in some tools — the `docker-compose env_file` directive handles this, but shell sourcing might not.
- **All dependencies are pinned** — `requirements.txt` uses `==` for every package (no `>=`). The full transitive tree is frozen in `requirements.lock` (generated from `pip freeze` inside the Docker image). The Dockerfile installs from `requirements.lock`, not `requirements.txt`. To update a dependency: bump it in `requirements.txt`, rebuild the image, run `pip freeze > requirements.lock` inside the container, and commit the lock file.
- **Frontend deps are pinned** — `package.json` uses exact versions (no `^` or `~`). `npm ci` in Docker reads from `package-lock.json`. To update: change `package.json`, run `npm install`, commit both files.
