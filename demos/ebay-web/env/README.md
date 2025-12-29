# ebay-web OpenEnv Adapter

A thin automation adapter (FastAPI) that exposes stable, structured endpoints for agent testing of core storefront journeys:

- Browse categories / products
- Advanced search
- Sign in/out (stores token in adapter memory)
- Add/remove cart items, read cart summary
- Toggle wishlist, read wishlist
- Fetch account summary

## Configuration

The adapter needs to know where your services are running:

- `EBAY_WEB_BACKEND_URL` (default: `http://localhost:18000`) – docker-compose maps backend `8000` to host `18000`
- `EBAY_WEB_FRONTEND_URL` (default: `http://localhost:3000`) – docker-compose maps frontend to host `3000`

You can also use `BACKEND_URL` / `FRONTEND_URL` as aliases.

## Run

```bash
python3 -m pip install -r env/requirements.txt

# in one terminal: docker compose up -d
# in another terminal:
EBAY_WEB_BACKEND_URL=http://localhost:18000 \
EBAY_WEB_FRONTEND_URL=http://localhost:3000 \
python3 -m uvicorn env.openenv_adapter:app --host 0.0.0.0 --port 8077
```

## Endpoints (high level)

- `GET /health`
- `POST /navigate` `{ "route": "/" }`
- `GET /session`
- `POST /auth/sign-in` `{ "email": "demo@example.com", "password": "demo" }`
- `POST /auth/sign-out`
- `GET /catalog/categories`
- `GET /catalog/products?limit=12&offset=0`
- `GET /catalog/category/{slug}/products?limit=12&offset=0&sort=position`
- `POST /search/advanced`
- `GET /cart`
- `POST /cart/items/add`
- `POST /cart/items/remove`
- `GET /wishlist`
- `POST /wishlist/toggle`
- `GET /account/summary`

## Example curl

```bash
curl -s http://localhost:8077/health | jq

curl -s -X POST http://localhost:8077/auth/sign-in \
  -H 'content-type: application/json' \
  -d '{"email":"demo@example.com","password":"demo"}' | jq

curl -s http://localhost:8077/catalog/products | jq

curl -s -X POST http://localhost:8077/cart/items/add \
  -H 'content-type: application/json' \
  -d '{"productId":"p-1001","quantity":1}' | jq

curl -s http://localhost:8077/cart | jq
```
