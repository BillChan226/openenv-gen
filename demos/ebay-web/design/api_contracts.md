# API Contracts (Mock Express)

Base URL: `/api`

Auth: `Authorization: Bearer <token>` (mock JWT). Protected endpoints return `401` if missing/invalid token.

QA / test environment note (this repo's automated QA tooling limitation):
- Some automated tooling cannot send `Authorization` headers and may redact JWTs in fixtures/logs.
- This backend supports **cookie-based JWT sessions** for QA and browser flows:
  - `POST /api/auth/login` and `POST /api/auth/register` set an **HttpOnly** cookie: `access_token=<jwt>`.
  - Protected endpoints accept JWT from either:
    - `Authorization: Bearer <token>` header (all envs)
    - `access_token` cookie (all envs)
- In **non-production** environments only (`NODE_ENV !== 'production'`), protected endpoints also accept token via:
  - Query param: `?access_token=<token>`
  - Request body field: `{ "token": "<token>" }` (used by `POST /api/auth/me`)
- In **production**, query/body fallbacks are disabled.


Offline / demo mode note:
- The frontend may fall back to local seeded data for **public** browsing pages when the API is unreachable.
- This fallback **does not** bypass auth: protected endpoints still require a valid Bearer token and will return **401** when missing/invalid.
- If the API is unreachable, protected features (account, wishlist, orders) should be treated as unavailable and the UI should prompt the user to sign in / try again later (see `design/spec.json#auth_and_offline_rules`).

Error shape (all non-2xx):
```json
{ "error": { "code": "STRING", "message": "Human readable", "details": null } }
```

Pagination: `limit` (default 24, max 100) and `offset` (default 0). Responses include `meta: {limit, offset, total}`.

---

## Health
### GET `/health`
Purpose: Health check.

Responses:
- **200** OK

Example 200:
```json
{ "status": "ok", "uptime": 123, "version": "1.0.0", "env": "development", "db": "demo" }
```

---

## Auth / Session

Auth endpoints are available at both:
- `/api/auth/*` (preferred)
- `/auth/*` (backward-compatible alias)

### POST `/auth/register`
Purpose: Creates a mock user and returns a session.
Auth: none

Request body:
```json
{
  "email": "alex@example.com",
  "password": "x",
  "firstName": "Alex",
  "lastName": "Shopper",
  "newsletterSubscribed": true
}
```

Responses:
- **201** Session
- **400** Validation error

Example 201:
```json
{
  "token": "jwt.mock.token",
  "user": {
    "id": "u_1",
    "firstName": "Alex",
    "lastName": "Shopper",
    "email": "alex@example.com",
    "newsletterSubscribed": true,
    "defaultBillingAddressId": null,
    "defaultShippingAddressId": null,
    "addresses": [],
    "wishlistProductIds": [],
    "orderSummaries": [],
    "createdAt": "2025-01-01T00:00:00.000Z"
  }
}
```

Example 400:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "email and password are required",
    "details": { "fields": { "email": "required", "password": "required" } },
    "requestId": "req_123"
  }
}
```

### POST `/auth/login`
Purpose: Mock login. Accepts any non-empty `email` and `password`.
Auth: none

Request body:
```json
{ "email": "alex@example.com", "password": "anything" }
```

Responses:
- **200** Session
- **401** Unauthenticated (missing/empty credentials)

Example 200:
```json
{
  "token": "jwt.mock.token",
  "user": {
    "id": "u_1",
    "firstName": "Alex",
    "lastName": "Shopper",
    "email": "alex@example.com",
    "newsletterSubscribed": true,
    "defaultBillingAddressId": null,
    "defaultShippingAddressId": null,
    "addresses": [],
    "wishlistProductIds": [],
    "orderSummaries": [],
    "createdAt": "2025-01-01T00:00:00.000Z"
  }
}
```

Example 401:
```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "message": "email and password are required",
    "details": null,
    "requestId": "req_124"
  }
}
```

### GET `/auth/me` (auth required)
Purpose: Returns current user.
Auth: required

Responses:
- **200** User
- **401** Unauthenticated

Example 200:
```json
{
  "user": {
    "id": "u_1",
    "firstName": "Alex",
    "lastName": "Shopper",
    "email": "alex@example.com",
    "newsletterSubscribed": true,
    "defaultBillingAddressId": null,
    "defaultShippingAddressId": null,
    "addresses": [],
    "wishlistProductIds": [],
    "orderSummaries": [],
    "createdAt": "2025-01-01T00:00:00.000Z"
  }
}
```

Example 401:
```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "message": "Missing or invalid bearer token",
    "details": null,
    "requestId": "req_125"
  }
}
```

### POST `/auth/me` (QA only; non-production)
Purpose: Returns current user by verifying a token provided in the request body.
Auth: token in body (non-production only)

Request body:
```json
{ "token": "jwt.mock.token" }
```

Responses:
- **200** User
- **400** Validation error
- **401** Unauthenticated
- **404** Not found (in production)



### POST `/auth/logout` (auth required)
Purpose: Best-effort logout (token invalidation in mock).
Auth: required

Request body: none

Responses:
- **204** No Content
- **401** Unauthenticated

---

## Categories

### GET `/categories`
Purpose: Returns the full 3-level category tree.
Auth: none

Query params:
- `depth=1|2|3` (default 3)

Responses:
- **200** Category tree

Example 200:
```json
{
  "data": [
    {
      "id": "c_beauty",
      "slug": "beauty-personal-care",
      "name": "Beauty & Personal Care",
      "level": 1,
      "parentId": null,
      "path": [{ "slug": "beauty-personal-care", "name": "Beauty & Personal Care" }],
      "children": []
    }
  ]
}
```

### GET `/categories/:slug`
Purpose: Returns a single category node with `path` and `children`.
Auth: none

Responses:
- **200** CategoryNode
- **404** Not found

Example 404:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Category not found",
    "details": { "slug": "unknown-slug" },
    "requestId": "req_200"
  }
}
```

---

## Products

### GET `/products`
Purpose: List products.
Auth: none

Query params:
- `category=<slug>` (optional; level 1/2/3)
- `q=<keyword>` (optional)
- `minPrice`, `maxPrice` (optional)
- `sort=price,-rating` (optional)
- `limit`, `offset`

Responses:
- **200** Product list

Example 200:
```json
{ "data": [], "meta": { "limit": 24, "offset": 0, "total": 60 } }
```

Empty case:
```json
{ "data": [], "meta": { "limit": 24, "offset": 0, "total": 0 } }
```

### GET `/products/:id`
Purpose: Product detail.
Auth: none

Responses:
- **200** Product
- **404** Not found

Example 404:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Product not found",
    "details": { "id": "p_999" },
    "requestId": "req_300"
  }
}
```

---

## Advanced Search

### POST `/search/advanced`
Purpose: Search products by multiple fields.
Auth: none

Query params:
- `limit` (default 24, max 100)
- `offset` (default 0)

Request body (all fields optional; at least one must be provided):
```json
{
  "name": "headphones",
  "sku": "SKU-123",
  "description": "wireless",
  "shortDescription": "bluetooth",
  "minPrice": 10,
  "maxPrice": 200
}
```

Validation rules:
- At least one search field must be present.
- If provided, `minPrice` and `maxPrice` must be numbers >= 0.
- If both provided, `minPrice` must be <= `maxPrice`.

Responses:
- **200** Search results (paged)
- **200** Empty results (paged)
- **400** Validation error

Example 200:
```json
{
  "data": [
    {
      "id": "p_1",
      "title": "Wireless Headphones",
      "price": { "currency": "USD", "amount": 59.99 },
      "rating": 4.6,
      "reviewCount": 128,
      "imageUrl": "https://example.com/p_1.jpg"
    }
  ],
  "meta": { "limit": 24, "offset": 0, "total": 1 }
}
```


### GET `/search/advanced`
Purpose: Compatibility search endpoint using query params.
Auth: none

Query params (all optional):
- `q` or `query` (maps to `name`)
- `name`, `sku`, `description`, `shortDescription`
- `minPrice`, `maxPrice`
- `limit`, `offset`, `sort`

Response shape: same as POST `/search/advanced`.


Empty case 200:
```json
{ "data": [], "meta": { "limit": 24, "offset": 0, "total": 0 } }
```

Example 400:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "At least one search field is required",
    "details": { "fields": { "name": "required_if_all_empty" } },
    "requestId": "req_410"
  }
}
```

---

## Cart (auth required)

Implementation note:
- In this repo, cart endpoints are protected and require auth.
- For QA/browser flows, authenticate via the `access_token` HttpOnly cookie set by `/api/auth/login`.

### GET `/cart`
Purpose: Returns the current cart.
Auth: none

Responses:
- **200** Cart

Example 200:
```json
{
  "data": {
    "id": "cart_anon_1",
    "userId": null,
    "items": [{ "productId": "p_1", "quantity": 2, "addedAt": "2025-01-01T00:00:00.000Z" }],
    "currency": "USD",
    "subtotal": { "currency": "USD", "amount": 39.98 },
    "itemCount": 2,
    "updatedAt": "2025-01-01T00:00:00.000Z"
  }
}
```

Empty case:
```json
{
  "data": {
    "id": "cart_anon_1",
    "userId": null,
    "items": [],
    "currency": "USD",
    "subtotal": { "currency": "USD", "amount": 0 },
    "itemCount": 0,
    "updatedAt": "2025-01-01T00:00:00.000Z"
  }
}
```

### POST `/cart/items`
Purpose: Add item; increments quantity if exists.
Auth: none

Request body:
```json
{ "productId": "p_1", "quantity": 1 }
```

Responses:
- **200** Updated cart
- **400** Validation error
- **404** Product not found

Example 200:
```json
{
  "data": {
    "id": "cart_anon_1",
    "userId": null,
    "items": [{ "productId": "p_1", "quantity": 3, "addedAt": "2025-01-01T00:00:00.000Z" }],
    "currency": "USD",
    "subtotal": { "currency": "USD", "amount": 59.97 },
    "itemCount": 3,
    "updatedAt": "2025-01-01T00:00:00.000Z"
  }
}
```

Example 400:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "quantity must be >= 1",
    "details": { "fields": { "quantity": ">=1" } },
    "requestId": "req_400"
  }
}
```

Example 404:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Product not found",
    "details": { "id": "p_999" },
    "requestId": "req_401"
  }
}
```

### PATCH `/cart/items/:productId`
Purpose: Set quantity. `quantity=0` removes item.
Auth: none

Request body:
```json
{ "quantity": 3 }
```

Responses:
- **200** Updated cart
- **400** Validation error
- **404** Product not found

### DELETE `/cart/items/:productId`
Purpose: Remove item.
Auth: none

Responses:
- **204** No Content
- **404** Product not in cart

Example 404:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Product not in cart",
    "details": { "productId": "p_2" },
    "requestId": "req_420"
  }
}
```

### POST `/cart/clear`
Purpose: Clears cart.
Auth: none

Responses:
- **204** No Content

---

## Wishlist (auth required)

### GET `/wishlist`
Purpose: Returns wishlist product ids.
Auth: required

Responses:
- **200** Wishlist
- **401** Unauthenticated

Example 200:
```json
{ "data": { "productIds": ["p_1", "p_9"] } }
```

Example 401:
```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "message": "Missing or invalid bearer token",
    "details": null,
    "requestId": "req_500"
  }
}
```

### POST `/wishlist/items`
Purpose: Add product.
Auth: required

Request body:
```json
{ "productId": "p_9" }
```

Responses:
- **201** Wishlist
- **401** Unauthenticated

Notes:
- Idempotent: adding an existing product keeps it in the wishlist.
- Alias: `POST /wishlist/toggle` toggles presence (add/remove).

### POST `/account/me` (QA only; non-production)
Purpose: Returns account user object by verifying a token provided in the request body.
Auth: token in body (non-production only)

Request body:
```json
{ "token": "jwt.mock.token" }
```

Response shape: same as GET `/api/account/me`.



### DELETE `/wishlist/items/:productId`
Purpose: Remove product.
Auth: required

Responses:
- **200** Wishlist
- **401** Unauthenticated

Notes:
- Alias: `DELETE /wishlist/items` with JSON body `{ "productId": "..." }` (backward-compatible).

---

## Account (auth required)

### GET `/account`
Purpose: Returns current account user object.
Auth: required

Notes:
- Canonical entry endpoint for account data.
- Alias: `GET /account/me` returns the same payload.

Responses:
- **200** User
- **401** Unauthenticated

### GET `/account/summary`
Purpose: Returns user + default addresses + recent orders.
Auth: required

Responses:
- **200** Summary
- **401** Unauthenticated

Example 200:
```json
{
  "user": { "id": "u_1", "email": "alex@example.com" },
  "defaultBillingAddress": null,
  "defaultShippingAddress": null,
  "recentOrders": []
}
```

### GET `/account/orders`
Purpose: List orders for the current user.
Auth: required

Relationship note:
- Orders are owned by a user via `Order.userId` (required).
- The user object may include `orderSummaries` for convenience, but the canonical list is this endpoint.

Query params:
- `limit`, `offset`

Responses:
- **200** Orders list
- **401** Unauthenticated

Example 200:
```json
{ "data": [], "meta": { "limit": 10, "offset": 0, "total": 3 } }
```
