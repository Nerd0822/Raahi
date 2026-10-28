# Raahi

Plan a trip in a sentence. Raahi turns a prompt into a day-by-day itinerary
with stops, timings and rough costs, saves it to your trips, and keeps an AI
travel companion that can check live weather, search the web and pull in
historical context. India-first, but it plans international trips too.

## What it does

- **Prompt-first landing** — describe the trip, optionally add a start date,
  and get the itinerary inline. Signed-out visitors write the prompt first;
  sign-in opens once and generation resumes automatically.
- **AI itineraries** — every generated plan is saved immediately as a `Plan`
  with ordered `PlanItem`s and `status=planned`, then opens in Trips for
  editing.
- **Trips** — create, edit and delete trips; change status and notes; add or
  remove stops with time, cost and day labels.
- **Explore** — Leaflet map with place search (Nominatim), A→B directions
  (OSRM), waypoints and a route fit.
- **AI chat** — ask about a destination; the model can call weather, search
  and Wikipedia tools before answering.
- **Profile** — name, bio, birth date and avatar. Uploads are checked with
  Pillow, capped at 2 MB, replaced files are deleted, and the avatar can be
  removed.

## Stack

| Layer     | Tech                                                                 |
| --------- | -------------------------------------------------------------------- |
| Frontend  | React 19 + Vite (oxlint)                                             |
| Backend   | Django 6 + Django REST Framework                                     |
| AI        | Any OpenAI-compatible `/chat/completions` endpoint; the default setup is local Ollama serving `gpt-oss:120b-cloud` |
| Data      | SQLite for local dev; Postgres 17 in Docker; Redis 7 as the cache L1 |
| Packaging | `npm` (frontend), `uv` (backend), Docker Compose + nginx             |

## Project structure

```
Raahi/
├── Backend/          # Django + DRF
│   ├── home/         #   project config (settings, urls)
│   ├── api/          #   API app
│   │   ├── llm.py    #     provider client, tool loop, itinerary prompt
│   │   ├── tools.py  #     weather / search / Wikipedia + cache
│   │   └── models.py #     Profile, Plan, PlanItem, ToolCache
│   └── .env          #   secrets — never committed
├── Frontend/         # React + Vite
│   └── src/          #   components, places, shared API client
└── docker/           # Compose, Dockerfiles, nginx and .env.example
```

## Development setup

**Backend**

```bash
cd Backend
uv sync                          # create/sync .venv from pyproject+uv.lock
cp .env.example .env             # then edit — see "Environment" below
uv run manage.py migrate
uv run manage.py runserver       # http://127.0.0.1:8000
```

**Frontend**

```bash
cd Frontend
npm install
npm run dev                      # http://localhost:5173
```

## Run with Docker

The whole stack — nginx, Gunicorn, Postgres and Redis — runs from `docker/`.

```bash
cp Backend/.env.example Backend/.env   # once, then edit
cp docker/.env.example docker/.env
docker compose -f docker/compose.yaml up -d --build
# http://localhost:8080
```

- **nginx** serves the built SPA, `/static/` and `/media/`, and proxies
  `/api/` and `/admin/` to Django.
- **backend** runs migrations and `collectstatic` on start, then Gunicorn.
- **db** is Postgres 17; **redis** is Redis 7. Database, uploaded media and
  collected static files live in named volumes.
- Change the public port with `WEB_PORT` in `docker/.env`.

Stop the stack with `docker compose -f docker/compose.yaml down`. Add `-v`
only when you also want to delete the database and uploaded files.

**AI in Docker:** containers reach Ollama on the host through
`host.docker.internal`, so run Ollama with `OLLAMA_HOST=0.0.0.0`. The Compose
file defaults `LLM_BASE_URL` to `http://host.docker.internal:11434/v1`; set
`LLM_BASE_URL` in `docker/.env` for a remote provider. Model and key still
come from `Backend/.env`.

## How the frontend talks to the backend

In dev, Vite proxies `/api` and `/media` → `http://127.0.0.1:8000` (see
`Frontend/vite.config.js`), so the app calls relative paths like
`fetch("/api/home/")` and no CORS is involved. CORS is also configured on the
backend (`django-cors-headers`, allowlisting `localhost:5173`) for cases where
the browser hits the backend directly — mobile dev, separate deployments. In
Docker, nginx does the same proxying.

## Environment

`Backend/.env` (gitignored — see `Backend/.env.example` for every key):

```
SECRET_KEY=   # generate: uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=        # True in dev; never True in prod
LLM_API_KEY=  # optional for local servers
LLM_BASE_URL= # any OpenAI-compatible /v1 endpoint
LLM_MODEL=    # required for the AI features
```

The default local setup is Ollama with the cloud model `gpt-oss:120b-cloud`:

```
LLM_API_KEY=
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL=gpt-oss:120b-cloud
```

OpenAI, OpenRouter, Groq, Together and other compatible providers work by
changing the URL, model and key. Without `LLM_MODEL`, AI endpoints return 503
and the UI reports that the guide is unavailable.

Docker Compose injects `POSTGRES_*`, `REDIS_URL`, `ALLOWED_HOSTS` and
`CSRF_TRUSTED_ORIGINS`. For local overrides, the backend also reads
`POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_PORT` and `REDIS_URL` from `Backend/.env`; with no `POSTGRES_HOST`
it uses SQLite.

## AI tools and caching

The model can call three keyless sources:

| Tool            | Source              | Cache TTL |
| --------------- | ------------------- | --------- |
| `get_weather`   | Open-Meteo          | 30 min    |
| `search_web`    | DuckDuckGo HTML     | 1 day     |
| `get_wikipedia` | Wikipedia REST API  | 7 days    |

Results are cached in `ToolCache` (unique on `tool` + normalized query) so
repeated questions about the same place do not hit the network. Redis is an
L1 cache in front of the database cache when `REDIS_URL` is set; a Redis
outage falls back to `ToolCache`. Failed and empty lookups are not cached.
Answers use at most three tool calls; repeated calls are rejected and the
final round removes tools so the model has to answer with what it already has.

Weather and search currently rely on the public Open-Meteo and DuckDuckGo
endpoints — fine for dev-scale traffic, but they should be cached/self-hosted
before production load.

## API

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/home/` | Health check |
| POST | `/api/auth/register/`, `/api/auth/login/`, `/api/auth/refresh/` | JWT auth |
| GET/PATCH | `/api/auth/me/` | Current profile, avatar upload/replace/remove |
| GET/POST | `/api/plans/` | List / create trips |
| GET/PATCH/DELETE | `/api/plans/:id/` | Read / edit / delete a trip |
| POST | `/api/plans/generate/` | Generate and save an itinerary from `prompt` + optional `start_date` |
| GET/POST/PATCH/DELETE | `/api/plan-items/` | Stops within a trip |
| POST | `/api/chat/` | Destination-aware AI chat |

Everything except `/api/home/` and the auth entry points requires a bearer
token. Send `remove_profile_picture=true` as multipart data to clear an
avatar.

## Checks

```bash
cd Backend && uv run python manage.py test api   # 35 tests
cd Frontend && npm run build && npm run lint
docker compose -f docker/compose.yaml config
bash docker/smoke.sh                             # deployed stack, incl. avatar + AI
```

Browser flows verified in Firefox at desktop and 390px: landing → prompt →
auth handoff → inline itinerary → open in Trips, preset cards, reset,
auth-cancel, mobile navbar/itinerary layouts, and avatar upload, replacement
and removal. The Compose stack was smoke-tested at `http://localhost:8080`
for the SPA, API, admin assets, Postgres migrations, Redis, media uploads and
AI calls, including a botcan-driven run through signup, itinerary generation,
Trips, profile editing and Explore chat.
