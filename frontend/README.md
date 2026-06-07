# frontend/

**What:** React dashboard for exploring POI scores and property features.  
**Why:** Gives analysts a map-based UI on top of the same REST API as external clients.

Stack: React 18, Vite, TypeScript, Leaflet.

---

## Tabs

| Tab | Component | API calls |
|-----|-----------|-----------|
| **Single** | `SingleView` | `GET/POST /api/v1/scores`, `GET /api/v1/pois` |
| **Batch** | `BatchView` | `POST /api/v1/scores/batch` |
| **Properties** | `PropertiesView` | `/api/v1/properties/*` (map, stats, detail) |

Clicking a batch row or property opens that location in the Single tab (`App.tsx` coordinates via `goToSingleWithLocation`).

---

## Project structure

```
frontend/
├── src/
│   ├── App.tsx              # Tab shell and navigation
│   ├── api.ts               # Backend client and TypeScript types
│   ├── constants.ts         # Shared UI constants
│   ├── components/
│   │   ├── SingleView.tsx   # Map + metrics + POI panel
│   │   ├── BatchView.tsx    # CSV/JSON upload and results table
│   │   ├── PropertiesView.tsx
│   │   ├── MapView.tsx      # Leaflet map (shared)
│   │   ├── MetricsPanel.tsx
│   │   └── RightPanel.tsx   # POI list
│   └── test/setup.ts
├── vite.config.ts           # Dev server + API proxy
└── package.json
```

---

## Development

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

The API must be running on port 8000 (Docker or local uvicorn).

### API base URL

[`src/api.ts`](src/api.ts) resolves the backend URL:

- **Dev (default):** relative `/api` — Vite proxy forwards to `http://localhost:8000`
- **Override:** set `VITE_API_URL=http://your-api:8000` in `frontend/.env`

Proxy config in [`vite.config.ts`](vite.config.ts): `/api`, `/health`, `/ready`.

---

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run test` | Vitest unit tests |
| `npm run lint` | ESLint |
| `npm run format:check` | Prettier check |

CI runs all of the above — see [CONTRIBUTING.md](../CONTRIBUTING.md).

---

## Single tab behaviour

- Enter coordinates or **double-click** the map to analyze a point.
- Metrics panel shows density, diversity, accessibility, nearest distances.
- Map draws 1 km / 400 m circles and POI markers; right panel lists POIs within 1 km.
- Filter POIs by clicking metric rows; **Show all** clears the filter.

## Batch tab behaviour

- Paste coordinates or upload CSV/JSON (max 500 locations — `BATCH_MAX` in `api.ts`).
- Export results as CSV; click a row to jump to Single tab.

## Properties tab behaviour

- Map of properties with precomputed features from `production.property_features`.
- Hierarchy drill-down via admin UIDs; click a property for detail and jump to Single.

---

## Further reading

| Doc | Topic |
|-----|-------|
| [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) | API and data flows |
| [../backend/app/features/scores/README.md](../backend/app/features/scores/README.md) | Score fields returned by API |
| [../backend/app/features/properties/README.md](../backend/app/features/properties/README.md) | Properties endpoints |
| [../docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md) | Full local setup |
