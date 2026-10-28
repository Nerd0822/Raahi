# Raahi — remaining work

Status: frontend build/lint clean, `api` tests green (35), and the
prompt → auth → itinerary → Trips flow verified live in Firefox at desktop and
390px. AI tools (weather, web search, Wikipedia) are live and cached. The
Compose stack (nginx, Gunicorn, Postgres, Redis) is built and smoke-tested at
`http://localhost:8080`.

## Done

- [x] **Navbar navigation** — Plan a trip / Explore / Trips with active state,
      logo returns home, avatar opens Profile; no dead anchors left
- [x] **Logged-in profile** — `/api/auth/me/` GET/PATCH; avatar upload (image
      validated with Pillow, ≤ 2 MB), full name, bio, birth date; replaced
      avatars deleted, `remove_profile_picture` clears one; `/media/` served
      by Django in dev and nginx in Docker; navbar avatar updates immediately
      and persists
- [x] **Auth** — JWT register / login (email or username) / refresh / me;
      shared `authed()` client with one refresh retry; Login modal wired to
      landing CTA, preset cards and prompt submissions
- [x] **Core models** — `Profile` (extends `AbstractUser`), `Plan`, `PlanItem`,
      `ToolCache` + migrations 0001–0004 (`PlaceInfo` removed)
- [x] **Plans / itinerary API + UI** — owner-scoped plan and stop CRUD (nested
      items, date validation, owner isolation) plus a Trips page: create/edit/
      delete trips, statuses, add/remove stops with time, cost and notes
- [x] **Explore map** — Leaflet + Esri satellite/labels blend slider, place
      search (Nominatim), Directions A→B (OSRM via LRM), map-tap waypoints,
      fit route, clear route, Search/→/Enter submission
- [x] **AI chat shell** — collapsible drawer + floating reopen button,
      auth-gated backend with real provider calls
- [x] **AI client** — OpenAI-compatible `/chat/completions` client
      (`api/llm.py`, stdlib HTTP) wired to `/api/chat/`; env-configured, 503
      when unconfigured, 502 on provider failure
- [x] **AI live** — local Ollama (`http://127.0.0.1:11434/v1`) serving
      `gpt-oss:120b-cloud`; verified through the API, the Explore chat drawer
      and itinerary generation
- [x] **AI tools + cache** — `get_weather` (Open-Meteo), `search_web`
      (DuckDuckGo HTML), `get_wikipedia` (Wikipedia REST); results cached in
      `ToolCache` for 30 min / 1 day / 7 days, empty or failed results not
      cached; max three calls per answer, duplicates rejected, tools removed
      from the final round so the model must answer
- [x] **Prompt-first generation** — `POST /api/plans/generate/` validates the
      model JSON, saves `Plan` + `PlanItem`s with `status=planned`, caps at 14
      days × 8 stops, and returns the saved plan for inline display
- [x] **Landing redesign** — hero prompt with optional start date, auth
      handoff that resumes generation, inline day-by-day result, curated
      starts, how it works, about, popular destinations, FAQ and dark footer;
      preset cards, reset and auth-cancel paths verified; `Cta`/`Planner`,
      `anime.js` and the old hero image removed
- [x] **Backend tests** — register validation/duplicates, email-or-username
      login, chat auth gate, profile update + avatar accept/reject/replace/
      remove, plans CRUD/validation, per-user isolation, plan-item ownership,
      LLM tool loop/limits, tool parsing, Redis/DB cache refill and outage
      tolerance, empty-result handling
- [x] **Docker stack** — `docker/compose.yaml` with Postgres 17, Redis 7,
      Django/Gunicorn and nginx; healthchecks, named volumes, `WEB_PORT`;
      nginx serves the SPA, `/static/`, `/media/` and proxies `/api/` and
      `/admin/`; backend entrypoint migrates and collects static; deployment
      smoke script covers web, data, avatars and AI
- [x] **Deployed E2E** — botcan run through signup, AI itinerary, Trips,
      profile editing and Explore chat at `http://localhost:8080`; avatar
      upload/replace/remove and 390px layout verified separately
- [x] **UI zoning** — no horizontal overflow at 390px, navbar and footer
      targets ≥ 44px, reduced-motion respected for scrolling
- [x] **Docs** — root README covers dev and Docker setup, env, AI tools/cache,
      API and checks; frontend README documents the app layout
- [x] **Feature work committed** — backend and frontend commits for auth,
      explore, profile, trips and media; probe test data reset

## Now

- [ ] **AI memory** — send recent chat turns with each request so follow-ups
      keep context. `/api/chat/` is still single-turn.
- [ ] **Refine a saved plan with AI** — Trips editing is manual; add a prompt
      box that regenerates or adjusts the selected plan while keeping its id
- [ ] **Tool cache pruning** — expired `ToolCache` rows accumulate forever; add
      a management command or periodic cleanup
- [ ] **Frontend routing** — adopt react-router (or URL state) for `/explore`,
      `/trips`, `/profile`; today `page` is component state, so no deep links
      or browser back/forward
- [ ] **Backend tests as features grow** — keep happy/404/validation coverage in
      step with the AI and future place endpoints

## Next

- [ ] **Stop editing UI** — the API supports item PATCH, but the Trips page
      only adds/removes stops; add inline edit for name/time/cost
- [ ] **Profile extras** — change password/email, delete account (nice-to-have)
- [ ] **State management decision** — revisit only if plans/chat make prop
      drilling hurt
- [ ] **CORS config widening** — backend allowlists only `localhost:5173` while
      dev sometimes runs on 5174; align with real dev/prod origins

## Later (before prod)

- [ ] **Rate limiting** — per-user limits on `/api/plans/generate/` and
      `/api/chat/`; each request can trigger several model and network calls
- [ ] **Production settings** — real `ALLOWED_HOSTS`, prod
      `CORS_ALLOWED_ORIGINS`, remove the SECRET_KEY fallback, keep DEBUG off
- [ ] **TLS and backups** — put the Compose stack behind a TLS terminator,
      restrict Postgres/Redis to the internal network, and back up the
      `postgres_data` and `media_data` volumes
- [ ] **Push to GitHub** — `origin` is configured
      (`https://github.com/Nerd0822/Raahi.git`) and `main` tracks
      `origin/master`, but the push is still pending because this machine has
      no stored GitHub credentials. Run `git push` from the repo root.

## Notes

- Dev flow: `cd Backend && uv run manage.py runserver` +
  `cd Frontend && npm run dev`
- Docker flow: `docker compose -f docker/compose.yaml up -d --build` from the
  repo root, then `http://localhost:8080`
- Secrets: `Backend/.env` (see `.env.example`); Compose settings in
  `docker/.env` (see `docker/.env.example`)
- Dev-scale free services: Nominatim (search), OSRM demo (routing),
  Open-Meteo (weather), DuckDuckGo HTML (search), Wikipedia REST — cache or
  self-host before real traffic
- Tool results are cached, not permanently stored per plan; `ToolCache` rows
  are disposable
