# Component Inventory & Responsibility Map

This document maps UI components to responsibilities, UI states, and API usage.

- **Source of truth for routes/UX/persistence**: `design/spec.json`
- **Supporting reference for schemas/endpoints**: `design/spec.api.json` (non-authoritative; must not contradict `design/spec.json`)
- **Contract format**: Each required component below includes **Purpose**, **Props**, **Events/Callbacks**, **State ownership**, and **UX states**.

## Relationship Notes (User ↔ Orders)

- **Canonical linkage**: `Order.userId` (required) links an order to its owning user.
- **User payload**: `User.orderSummaries` may be included as a lightweight convenience field.
- **Canonical fetch**: Orders list for the signed-in user is fetched via `GET /api/account/orders`.
- **Why**: Avoids large `User` payloads while still satisfying the requirement that a user includes orders.


---

## Layouts

### `AppShell`
- **Owns state**: SessionStore, CartStore, WishlistStore, Categories cache
- **Renders**: `Header`, route outlet, `Footer`, `ToastHost`
- **API**: Hydrates categories (`GET /categories`), cart (`GET /cart`), session (`localStorage` then `GET /auth/me` if token)

### `Header` (sticky)
- **Sections** (matches reference):
  1) Utility bar (right): My Account, My Wish List, Sign In/Out, Welcome message when signed in
  2) Main header row: logo, search bar, cart icon w/ badge, Advanced Search link
  3) Category navigation: top-level categories with hover mega-menu
- **Key behaviors**:
  - Sticky at top; shadowless; subtle bottom border
  - Search submit navigates to canonical search results route: `/search?q=<encoded query>` (category browsing remains `/category/:slug`).
  - Cart badge reflects `CartStore.itemCount`

### `Footer`
- Links: Privacy and Cookie Policy, Search Terms, Advanced Search, Orders and Returns, Contact Us
- Newsletter subscribe input (demo only)

#### Global layout behavior (explicit)
- **Header**: sticky on all breakpoints (`position: sticky; top: 0; z-index: 1000`).
- **Footer**: **standard footer (NOT sticky)**.
  - Footer sits after main content.
  - On short pages, use a flex column shell to push footer to bottom (`min-height: 100vh; main { flex: 1 }`).
  - Do **not** use `position: fixed` for footer (avoids covering content on mobile).

### `AccountLayout`
- 2-column desktop: left nav + content
- Mobile: nav collapses to select/accordion

---

## Feature Components

### `MegaMenu`
- **Input**: `rootCategory: CategoryNode` (level 1)
- **Desktop behavior**:
  - Opens on hover or click (supports touch/trackpad)
  - Left column: level-2 children
  - Right column: level-3 children for highlighted level-2
  - Escape closes; arrow keys move selection
- **Mobile behavior (required)**:
  - Category navigation becomes a **hamburger** that opens a **drawer**.
  - Inside the drawer, categories are presented as an **accordion**:
    - Level 1: accordion headers
    - Level 2: nested accordion under an expanded level 1
    - Level 3: links inside expanded level 2
  - **Tap rule** for top-level items on mobile: **first tap expands**, **second tap navigates** (prevents accidental navigation when trying to browse).
  - Close behavior: X button, tap outside on backdrop, and Esc key.
  - Accessibility: on open, focus moves to the close button; focus is trapped within the drawer until closed.
- **Navigation**: click routes to `/category/:slug`

### `ProductCard`
- **Displays**: image, name, rating+reviewCount, price
- **Actions**:
  - View details: clicking image/title navigates to `/product/:id`
  - Add to Cart: calls `CartStore.add(productId)` → `POST /cart/items`
  - Wishlist toggle:
    - If signed in: `WishlistStore.toggle(productId)` → `POST/DELETE /wishlist/items`
    - If signed out: redirect to `/login?next=<current>`
- **States**: disabled if out_of_stock; show small inline label

---

## Required Component Contracts (Props / Events / State Ownership)

> Naming convention: component names here must match implementation component names.

### `Breadcrumbs`
**Purpose**: Show hierarchical navigation (e.g., Home → Category → Subcategory) and allow navigating back up the hierarchy.

**Props**
- `items` (**required**): `Array<{ label: string; href?: string; id?: string }>`
  - `label` (**required**): display text
  - `href` (optional): if present, clicking navigates (or is passed to callback)
  - `id` (optional): stable identifier for analytics/testing; if omitted, consumer may use index
- `currentId` (optional): `string`
  - If provided, marks the crumb with matching `id` as the current page (render as non-link).
- `separator` (optional): `string` (default: "/")

**Events/Callbacks**
- `onCrumbClick` (optional): `(item: {label:string; href?:string; id?:string}, index: number) => void`
  - Fired when a non-current crumb is clicked.
  - If provided, component should **not** hard-navigate; parent decides navigation.

**State ownership**
- **Owned by parent/router**: `items`, `currentId`.
- **Internal**: none (pure presentational).

**UX states**
- Empty: if `items.length === 0`, render nothing.

---

### `SortBar`
**Purpose**: Display result count/range and allow changing sort order.

**Props**
- `sortKey` (**required**): `string` (current selected sort key)
- `options` (**required**): `Array<{ key: string; label: string }>`
- `total` (optional): `number` (total results)
- `range` (optional): `{ start: number; end: number }`
  - Used to render “Items {start}–{end} of {total}”.
- `disabled` (optional): `boolean` (default: `false`)

**Events/Callbacks**
- `onChange` (**required**): `(nextSortKey: string) => void`
  - Fired when user selects a different sort option.

**State ownership**
- **Owned by parent/page**: `sortKey`, `total`, `range` (derived from query/pagination).
- **Internal**: none.

**UX states**
- Loading: parent may pass `disabled=true` while results refetch.

---

### `Pagination`
**Purpose**: Navigate between pages of results; optionally change page size.

**Props**
- `page` (**required**): `number` (1-based)
- `pageSize` (**required**): `number`
- `total` (**required**): `number` (total number of items)
- `pageSizeOptions` (optional): `number[]` (default: `[12, 24, 48]`)
- `disabled` (optional): `boolean` (default: `false`)

**Events/Callbacks**
- `onPageChange` (**required**): `(nextPage: number) => void`
  - Fired when user clicks next/prev or a page number.
- `onPageSizeChange` (optional): `(nextPageSize: number) => void`
  - If provided, component renders a page-size control.

**State ownership**
- **Owned by parent/page**: `page`, `pageSize`, `total` (and URL query sync).
- **Internal**: none.

**UX states**
- If `total <= pageSize`, hide pagination controls.

---

### `FiltersRail`
**Purpose**: Show available filter buckets (e.g., price ranges) and allow selecting filters. Desktop left rail; mobile drawer/accordion.

**Props**
- `availableBuckets` (**required**):
  `Array<{ key: string; label: string; options: Array<{ value: string; label: string; count?: number }> }>`
  - Example:
    - `{ key: "price", label: "Price", options: [{ value: "0-25", label: "$0 - $25", count: 12 }] }`
- `selected` (**required**): `Record<string, string[] | string>`
  - Keys correspond to bucket keys.
  - Values are either a single selection (`string`) or multi-select (`string[]`) depending on bucket.
- `disabled` (optional): `boolean` (default: `false`)
- `variant` (optional): `'desktop' | 'mobile'` (default: `'desktop'`)

**Events/Callbacks**
- `onChange` (**required**): `(nextSelected: Record<string, string[] | string>) => void`
  - Fired when any bucket selection changes.
- `onClearAll` (optional): `() => void`
  - Fired when user clicks “Clear filters”.

**State ownership**
- **Owned by parent/page**: `availableBuckets` (from API), `selected` (from URL query / store).
- **Internal**: UI-only expanded/collapsed sections (accordion open state) may be internal.

**UX states**
- Empty: if `availableBuckets.length === 0`, render a minimal “No filters available”.
- Loading: parent may render skeleton or pass `disabled=true`.

---

### `CartSummary`
**Purpose**: Show cart totals and primary checkout action.

**Props**
- `totals` (**required**):
  `{ subtotal: number; shipping?: number; tax?: number; total: number; currency: string }`
- `canCheckout` (optional): `boolean` (default: `true`)
- `checkoutLabel` (optional): `string` (default: `"Proceed to checkout"`)

**Events/Callbacks**
- `onCheckout` (**required**): `() => void`
  - Fired when user clicks checkout button.

**State ownership**
- **Owned by parent/store**: `totals`, `canCheckout`.
- **Internal**: none.

**UX states**
- If cart empty, parent should not render CartSummary (or render disabled state).

---

### `WishlistGrid`
**Purpose**: Display wishlist items in a grid with remove and add-to-cart actions.

**Props**
- `items` (**required**):
  `Array<{ id: string; title: string; price: number; currency: string; imageUrl?: string }>`
- `loading` (optional): `boolean` (default: `false`)

**Events/Callbacks**
- `onRemove` (**required**): `(id: string) => void`
- `onAddToCart` (**required**): `(id: string) => void`
- `onItemClick` (optional): `(id: string) => void`

**State ownership**
- **Owned by parent/page/store**: `items`, `loading`.
- **Internal**: none.

**UX states**
- Empty: if `items.length === 0`, render requirements-compliant empty message + CTA.

---

### `OrdersTable`
**Purpose**: Display a list of orders with actions to view details or reorder.

**Props**
- `orders` (**required**):
  `Array<{ id: string; placedAt: string; status: string; total: number; currency: string; itemCount: number }>`
- `loading` (optional): `boolean` (default: `false`)

**Events/Callbacks**
- `onView` (**required**): `(orderId: string) => void`
- `onReorder` (**required**): `(orderId: string) => void`

**State ownership**
- **Owned by parent/page**: `orders`, `loading`.
- **Internal**: none.

**UX states**
- Empty: show “No orders yet” with link to browse.
- Loading: show table skeleton rows.

---

## Pages & Route Responsibilities

### `/` HomePage
- **Renders**: Product showcase grid (8–12)
- **API**: `GET /products?limit=12`
- **States**: loading skeleton, empty, error

### `/advanced-search` AdvancedSearchPage
- **Renders**: form + results list
- **API**: `POST /search/advanced`
- **States**: loading, empty results, error; responsive stacked on mobile

### `/login` LoginPage
- **API**: `POST /auth/login`
- **Behavior**: redirect to `next` param or `/account`

### `/account` AccountOverviewPage (protected)
- **API**: `GET /account/summary`
- **Renders**: account info, addresses, newsletter status, recent orders table

### `/account/wishlist` WishlistPage (protected)
- **API**: `GET /wishlist` then fetch product details (implementation choice)
- **States**: empty vs populated

### `/account/orders` OrdersPage (protected)
- **API**: `GET /account/orders`
- **Renders**: `OrdersTable` with pagination
- **States**: loading skeleton rows, empty state, error w/ retry


### `/category/:slug` CategoryPage
- **Renders**: breadcrumbs, title, filters rail, sort bar, product grid, pagination
- **API**: `GET /categories/:slug` + `GET /products?category=:slug&minPrice&maxPrice&sort&limit&offset`

### `/product/:id` ProductDetailPage
- **API**: `GET /products/:id`
- **Renders**: gallery, title, price, description, buy box (qty + add-to-cart), wishlist toggle
- **States**: loading skeleton, not-found/error, add-to-cart toast

### `/cart` CartPage
- **API**: `GET /cart`, `PATCH /cart/items/:productId`, `DELETE /cart/items/:productId`, `POST /cart/clear`
- **Header cart behavior**: no mini-cart in MVP; cart icon navigates directly to `/cart`

---

## State Ownership Summary

- **SessionStore**: token + user; hydrates from localStorage; validates via `/auth/me`
- **CartStore**: anonymous or user cart; persisted in localStorage; merges on login
- **WishlistStore**: signed-in only; mirrored to localStorage; cleared on logout
- **CatalogStore**: products + categories; in-memory cache; categories optionally persisted

---

## UX States Checklist (All Pages)

Each page must handle:
- Loading: skeletons aligned to final layout
- Empty: friendly message + navigation
- Error: inline error with Retry
- Signed-out vs signed-in: wishlist/account guarding
- Responsive: desktop 2-column where applicable; mobile collapsible filters/nav
