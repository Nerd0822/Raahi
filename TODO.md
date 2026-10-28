# Raahi — remaining work

Status: frontend build/lint clean, `api` tests green (10), explore/profile/trips
flows verified live in Firefox.

## Done

- [x] **Navbar navigation** — Explore / Trips / Profile links with active state,
      logo returns to the app, avatar opens Profile; no dead anchors left
- [x] **Logged-in profile** — `/api/auth/me/` GET/PATCH; avatar upload (image
      only, ≤ 2 MB), full name, bio, birth date; `/media/` served by Django and
      proxied by Vite; navbar avatar updates immediately and persists
- [x] **Auth** — JWT register / login (email or username) / refresh / me;
      shared `authed()` client with one refresh retry; Login modal wired to
      landing CTA
- [x] **Core models** — `Profile` (extends `AbstractUser`), `Plan`, `PlanItem`,
      `PlaceInfo` + migrations 0001/0002
- [x] **First endpoints** — `/api/home/`, auth endpoints, `/api/chat/` stub,
      `/api/plans/` + `/api/plan-items/`
- [x] **Plans / itinerary API + UI** — owner-scoped plan and stop CRUD (nested
      items, date validation, owner isolation) plus a Trips page: create/edit/
      delete trips, statuses, add/remove stops with time, cost and notes
- [x] **Explore map** — Leaflet + Esri satellite/labels blend slider, place
      search (Nominatim), Directions A→B (OSRM via LRM), map-tap waypoints,
      fit route, clear route, Search/→/Enter submission
- [x] **AI chat shell** — collapsible drawer + floating reopen button, auth-gated
      backend stub with canned replies (real AI pending)
- [x] **Backend tests** — register validation/duplicates, email-or-username
      login, chat auth gate, profile update + avatar accept/reject, plans CRUD/
      validation, per-user isolation, plan-item ownership
- [x] **Landing page** — Navbar, Hero, CTA band + Login modal, Planner
      (anime.js), Footer
- [x] **UI zoning** — no overlapping controls (measured), 44px targets,
      mobile card width, reduced-motion respected
- [x] **Template cleanup** — `App.css`, React/Vite logos, `icons.svg` removed
- [x] **Feature work committed** — backend and frontend commits for auth,
      explore, profile, trips and media; probe test data/avatar reset and
      `Backend/media/` ignored

## Now

- [ ] **Real AI companion** — replace the canned `/api/chat/` stub
      (`ponytail:` marker) with a provider call; use `PlaceInfo` as the cache
      (model currently unused)
- [ ] **Frontend routing** — adopt react-router (or URL state) for `/explore`,
      `/trips`, `/profile`; today `page` is component state, so no deep links
      or browser back/forward
- [ ] **API client consolidation** — `auth.js` is the shared authed client, but
      `Login.jsx` and the `Footer` health ping still call `fetch` directly
- [ ] **Backend tests as features grow** — keep happy/404/validation coverage in
      step with the AI and future place endpoints

## Next

- [ ] **Stop editing UI** — the API supports item PATCH, but the Trips page
      only adds/removes stops; add inline edit for name/time/cost
- [ ] **Logged-out navbar links** — landing page shows only the logo; add
      section links (Places, Planner, About) or routes as the page grows
- [ ] **Profile extras** — change password/email, delete account (nice-to-have)
- [ ] **State management decision** — revisit only if plans/chat make prop
      drilling hurt
- [ ] **Docs refresh** — root README mentions only the `/api` proxy and
      frontend README is still Vite template text. Document `/media`, auth and
      plan endpoints, explore/profile/trips pages
- [ ] **CORS config widening** — backend allowlists only `localhost:5173` while
      dev sometimes runs on 5174; align with real dev/prod origins

## Later (before prod)

- [ ] **Production settings** — real `ALLOWED_HOSTS`, prod
      `CORS_ALLOWED_ORIGINS`, remove the SECRET_KEY fallback, keep DEBUG off
- [ ] **Media in production** — dev-only serving today; use object storage
      (S3) or nginx for `/media/`
- [ ] **Deployment story** — Vite `build/` via Django/CDN + gunicorn (+
      whitenoise for static)
- [ ] **Remote repo** — no origin configured yet; push to GitHub

## Notes

- Dev flow: `cd Backend && uv run manage.py runserver` +
  `cd Frontend && npm run dev`
- Secrets: `Backend/.env` (see `.env.example`)
- Dev-scale free services: Nominatim (search), OSRM demo (routing) — both need
  caching/self-hosting before real traffic
