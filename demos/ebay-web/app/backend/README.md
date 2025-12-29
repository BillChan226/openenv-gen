# ebay-web backend

Express API for the eBay-style demo storefront.

## Requirements
- Node.js 18+
- (Optional) PostgreSQL via docker compose at repo root

## Environment
Copy and edit:

```bash
cp .env.example .env
```

Key vars:
- `PORT` (default 8000)
- `DATABASE_URL` (optional; if missing/unreachable, server falls back to in-memory demo data)
- `JWT_SECRET`
- `DEMO_MODE=true` to force in-memory mode

## Run locally

```bash
npm install
npm run dev
```

Health check:

```bash
curl http://localhost:8000/health
```

## API quick notes
- Auth: `POST /auth/login` returns `{token, user}`. Use `Authorization: Bearer <token>` for protected endpoints.
- Catalog: `/api/products`, `/api/categories/tree`, `/api/search/advanced`
- Cart: `/api/cart/*` (protected)
- Wishlist: `/api/wishlist/*` (protected)
- Account: `/api/account/*` (protected)
