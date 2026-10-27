# Raahi

Your travel buddy, always one step ahead — routes, buses, hotels and food
spots, plus an AI companion that chats with you while you explore.

## Stack

| Layer    | Tech                                    |
| -------- | --------------------------------------- |
| Frontend | React 19 + Vite (oxlint)                |
| Backend  | Django 6 + Django REST Framework        |
| Packages | `npm` (frontend), `uv` (backend)        |

## Project structure

```
Raahi/
├── Backend/       # Django + DRF
│   ├── home/      #   project config (settings, urls)
│   ├── api/       #   the API app
│   └── .env       #   secrets — never committed
└── Frontend/      # React + Vite
    └── src/       #   components, pages
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

## How the frontend talks to the backend

In dev, Vite proxies `/api` → `http://127.0.0.1:8000` (see
`Frontend/vite.config.js`), so the app just calls relative paths like
`fetch("/api/home/")` and no CORS is involved. CORS is also configured on the
backend (`django-cors-headers`, allowlisting `localhost:5173`) for cases where
the browser hits the backend directly — mobile dev, separate deployments.

## Environment

`Backend/.env` (gitignored — see `Backend/.gitignore` for required keys):

```
SECRET_KEY=   # generate: uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=        # True in dev; never True in prod
```

## Checkpoints

- Backend API health: `curl http://127.0.0.1:8000/api/home/` → `{"message": "hello from backend"}`
