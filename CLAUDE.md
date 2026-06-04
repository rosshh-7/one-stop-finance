# One Stop Finance — Claude Code Instructions

This file is automatically read by Claude Code. Follow every rule here exactly. These patterns exist for consistency across all contributors.

---

## Project Overview

Subscription-based financial intelligence platform. Phase 1-2 uses exclusively free APIs (yfinance, SEC EDGAR, feedparser). All 5 features are currently free — the feature flag system allows moving any feature to Pro with a single config line.

**Running services (Docker):**
```bash
docker-compose up --build   # first time
docker-compose up           # subsequent starts
```

**Ports:** Frontend `:3000` · API `:8000` · API docs `:8000/docs`

---

## Git Rules

- **All commits belong to the human developer — never add `Co-Authored-By` or any Claude attribution to commit messages**
- Commit messages follow conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`
- Always run `npx tsc --noEmit` (frontend) and `pytest` (backend) before committing
- Push to `main` only after verifying both pass

---

## Backend Architecture

### Strict Pattern — Every Feature = 4 Files

Every feature lives in `backend/app/features/<name>/` and must have exactly these files:

```
router.py      # FastAPI routes only — no business logic
service.py     # Business logic — calls repo + integrations
repository.py  # DB + Redis only — no business logic
schemas.py     # Pydantic v2 request/response models
```

**Never put DB queries in a router. Never put business logic in a repository.**

### Adding a New Feature

1. Create `backend/app/features/<name>/` with all 4 files
2. Register the router in `backend/app/main.py`
3. Add a feature flag entry in `backend/app/core/feature_flags.py`
4. Create an Alembic migration if new DB tables are needed: `docker exec osf_api alembic revision --autogenerate -m "add_<name>"`
5. Apply migration: `docker exec osf_api alembic upgrade head`

### Response Envelope

Every API response must use the response builders from `app/core/response.py`:

```python
from app.core.response import build_response, build_paginated_response

# Single item / list
return build_response({"themes": data})

# Paginated
return build_paginated_response(items, page=1, per_page=20, total=100)
```

All responses have the shape `{ data, error, meta }` — never return raw dicts from routes.

### Feature Flags

```python
# backend/app/core/feature_flags.py
FEATURE_FLAGS: dict[str, str] = {
    "theme_intelligence": "free",   # change to "pro" to gate it
    "options_chain":      "free",
    ...
}
```

Gate a route with:
```python
@router.get("/endpoint", dependencies=[Depends(require_feature("options_chain"))])
```

### Integrations (Data Sources)

All external API calls live in `backend/app/integrations/`. Never call yfinance, SEC EDGAR, or any external API directly from a router or service — always go through the integration layer.

yfinance calls are blocking — always wrap them with `asyncio.to_thread()`:
```python
async def fetch_something() -> list[dict]:
    return await asyncio.to_thread(_fetch_something_sync)
```

### Celery Workers

Workers are pollers — they run on a schedule via Celery Beat and write to Redis or PostgreSQL. The API reads from cache, never waiting on external APIs during a request.

Worker files live in `backend/app/workers/`. Register new beat schedules in `backend/app/celery_app.py`.

### Redis Caching Pattern

```python
CACHE_KEY = "namespace:key"
TTL = 60  # seconds

async def get_data(redis: Redis):
    cached = await redis.get(CACHE_KEY)
    if cached:
        return json.loads(cached)
    data = await fetch_from_source()
    if data:
        await redis.setex(CACHE_KEY, TTL, json.dumps(data))
    return data
```

### Database Migrations

```bash
# After changing any model file:
docker exec osf_api alembic revision --autogenerate -m "describe_the_change"
docker exec osf_api alembic upgrade head
```

Always commit migration files to git. Never edit an already-applied migration — create a new one.

### Naming Conventions (Python)

| Thing | Convention | Example |
|---|---|---|
| Files / functions | `snake_case` | `stock_service.py`, `get_quote()` |
| Classes | `PascalCase` | `StockService`, `InsiderScorer` |
| API routes | `/api/v1/kebab-case` plural | `/api/v1/insider-trades` |
| DB tables | `snake_case` plural | `watchlist_items` |
| Redis keys | `resource:id:field` | `quote:AAPL`, `public:market-indices` |
| Env vars | `SCREAMING_SNAKE_CASE` | `STRIPE_SECRET_KEY` |

---

## Frontend Architecture

### Directory Structure

```
src/
├── features/<name>/     # All logic for a feature (hooks, components, types)
├── pages/               # Route-level components only — thin wrappers
├── components/
│   ├── ui/              # Generic reusable components (Button, Card, Badge)
│   └── layout/          # AppShell, Sidebar, Topbar
├── stores/              # Zustand global state
├── lib/                 # api-client, query-client, utils
└── config/              # feature-flags.ts
```

### Adding a New Page

1. Create `src/pages/<Name>Page.tsx`
2. Create `src/features/<name>/` with hooks and components
3. Add the route in `src/App.tsx`
4. Add the nav link in `src/components/layout/Sidebar.tsx`

### Data Fetching — Always TanStack Query

Never use `useEffect` + `useState` for server data. Always use `useQuery`:

```typescript
// src/features/<name>/hooks.ts
export function useThemes() {
  return useQuery({
    queryKey: ['themes'],
    queryFn: () => apiClient.get('/themes').then(r => r.data.data),
    staleTime: 30_000,
  })
}
```

For live data that needs to refresh: add `refetchInterval`.

### Feature Gating

```tsx
import { ProGate } from '@/features/subscription/components/ProGate'

// Blur the content with an upgrade overlay
<ProGate feature="options_chain" mode="blur">
  <OptionsChart />
</ProGate>

// Show a lock card instead of content
<ProGate feature="options_chain" mode="lock">
  <OptionsChart />
</ProGate>

// Inline lock icon (for table rows)
<ProGate feature="options_chain" mode="inline">
  <span>{value}</span>
</ProGate>
```

The `feature` prop must match a key in `src/config/feature-flags.ts`.

### API Client

Always use the shared Axios client — never use `fetch` directly:

```typescript
import { apiClient } from '@/lib/api-client'

const res = await apiClient.get('/public/market-summary')
const res = await apiClient.post('/themes', { name: '...' })
```

The client automatically attaches the JWT Bearer token and handles 401 token refresh.

### Naming Conventions (TypeScript)

| Thing | Convention | Example |
|---|---|---|
| Component files | `PascalCase` | `StockChart.tsx` |
| Hook files / functions | `camelCase` with `use` prefix | `useStockQuote.ts` |
| Lib / config files | `kebab-case` | `api-client.ts` |
| Zustand stores | `camelCase` with `.store.ts` suffix | `auth.store.ts` |
| CSS variables | `--color-*` | `var(--color-accent-blue)` |

### Styling

Use the CSS variables defined in `src/index.css` — never hardcode hex colors:

```tsx
// ✅ correct
className="text-[var(--color-text-primary)] bg-[var(--color-bg-card)]"

// ❌ wrong
className="text-slate-100 bg-gray-800"
```

---

## What NOT To Do

- Never install a new npm package or Python dependency without checking if the functionality already exists in the project
- Never call external APIs (yfinance, SEC EDGAR) from inside FastAPI route handlers — use workers + cache
- Never write raw SQL — use SQLAlchemy ORM
- Never add `Co-Authored-By` or any AI attribution to commits
- Never hardcode localhost URLs or file paths — use env vars
- Never skip migrations — if you change a model, always generate and apply a migration
- Never use `useEffect` for data fetching — use TanStack Query
- Never use hardcode hex color values in Tailwind classes — use CSS variables
