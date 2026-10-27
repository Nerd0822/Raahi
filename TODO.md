# Raahi — remaining work

## Now

- [ ] **Navbar** — the `#features` link is dead; add real links/pages once routes exist
- [ ] **API client module** — replace the raw fetch in `Hero.jsx` with one shared `src/api.js` so every endpoint call looks the same
- [ ] **Design core models** — what the app actually tracks (users, routes/outlets?, hotels, food spots) + migrations
- [ ] **First real endpoints** — list + detail views with DRF serializers/viewsets/urls for those models

## Next

- [ ] **Auth groundwork** — token or session auth wiring in DRF so an accounts app can build on it (deliberately deferred in setup)
- [ ] **Frontend routing** — react-router (or tabs) once there's more than one page
- [ ] **State management decision** — only if the fetch-in-component pattern starts hurting
- [ ] **AI companion** — the "chat while you explore" feature; backend endpoint + frontend chat UI
- [ ] **Backend tests** — `api/tests.py` is empty; at minimum test each endpoint happy+404 path

## Later (before prod)

- [ ] **Production settings** — `DEBUG` from env already works, but need real `ALLOWED_HOSTS`, prod `CORS_ALLOWED_ORIGINS`, SECRET_KEY discipline
- [ ] **Deployment story** — Vite `build/` output served via Django (or CDN) + gunicorn + whitenoise
- [ ] **Remote repo** — no origin configured yet; push to GitHub
- [ ] **Lint/arch cleanup** — `README.md` in Frontend is still the Vite template text; App.css holds leftover template junk

## Notes

- Dev flow today: `cd Backend && uv run manage.py runserver` + `cd Frontend && npm run dev`
- Secrets: `Backend/.env` (see `.env.example`)
