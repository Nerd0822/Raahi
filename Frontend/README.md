# Raahi frontend

React 19 + Vite. The landing page is prompt-first: a visitor describes a trip,
signs in once, and the generated itinerary appears inline and is saved to Trips.

```bash
npm install
npm run dev     # http://localhost:5173
npm run build
npm run lint
```

The dev server proxies `/api` and `/media` to `http://127.0.0.1:8000`, so run
the Django backend alongside it. See the root `README.md` for backend setup,
environment variables and the AI tool/caching model.

## Layout

- `src/App.jsx` — homepage-first shell and auth handoff
- `src/components/Landing.jsx` — hero, generated result, curated starts, how it
  works, about, destinations, FAQ and footer
- `src/components/Hero.jsx` — prompt form and example trips
- `src/components/Trips.jsx` — saved plan editing and day-by-day stops
- `src/components/Explore.jsx` — Leaflet map, search and routing
- `src/components/Chat.jsx` — AI travel chat drawer
- `src/places.js` — curated landing destinations and starter prompts
- `src/auth.js` — shared authed fetch client with one refresh retry

Container builds, nginx and Compose live at the repo root: `Dockerfile`,
`nginx/nginx.conf` and `docker-compose.yml`. See the root `README.md` for the
Docker run command.
