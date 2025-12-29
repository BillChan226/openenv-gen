# eBay-Style Shopping Website

Build a responsive web shopping website similar to the classic eBay storefront. The goal is to simulate realistic e-commerce navigation and flows (browse → search/filter → product cards → cart/wishlist → account pages). Use clean, production-quality structure and mock data only (no real backend required).

---

## 1. Global Layout & Navigation (All Pages)

### Header (Sticky)
- Top utility bar (right aligned):
  - Links: **My Account**, **My Wish List**, **Sign In / Sign Out**
  - If signed in, display: “Welcome, {FirstName LastName}!”
- Main header row:
  - Left: brand logo (text or logo, “eBay”-style)
  - Center/right: **Search bar** with placeholder “Search entire store here…”
  - Cart icon with item-count badge
  - **Advanced Search** link routing to `/advanced-search`
- Primary category navigation (horizontal):
  - Categories:
    - Beauty & Personal Care
    - Sports & Outdoors
    - Clothing, Shoes & Jewelry
    - Home & Kitchen
    - Office Products
    - Tools & Home Improvement
    - Health & Household
    - Patio, Lawn & Garden
    - Electronics
    - Cell Phones & Accessories
    - Video Games
    - Grocery & Gourmet Food
  - Hover opens a dropdown/mega menu:
    - Left column: subcategories
    - Right column: deeper subcategories
  - Clicking routes to `/category/:slug` or nested paths

### Footer
- Links:
  - Privacy and Cookie Policy
  - Search Terms
  - Advanced Search
  - Orders and Returns
  - Contact Us
- Newsletter subscribe input + Subscribe button (demo only)

---

## 2. Mock Data Models

Create mock JSON data for:
- **Products**: id, name, price, rating, reviewCount, image, categoryPath, sku, shortDescription, description
- **Categories**: hierarchical (category → subcategory → leaf)
- **User**:
  - name, email
  - billing & shipping addresses
  - recent orders
  - wishlist items

Use in-memory state and optional localStorage persistence.

---

## 3. Core Features & State

### Cart
- Add to cart from product cards
- Cart icon shows item count
- Maintain quantities and subtotal
- Mini cart or `/cart` page (either is acceptable)

### Wish List
- Heart icon toggles wishlist state
- Dedicated “My Wish List” page with empty and populated states

### Authentication (Mock)
- Sign In accepts any non-empty credentials
- On sign-in, create a mock session
- Sign Out clears session
- Account pages require sign-in

---

## 4. Required Pages

### A. Home (`/`)
- Product showcase grid (8–12 items)
- Product cards include:
  - Image
  - Name
  - Rating + review count
  - Price
  - **Add to Cart** button
  - Wishlist icon

---

### B. Advanced Search (`/advanced-search`)
- Form fields:
  - Product Name
  - SKU
  - Description
  - Short Description
  - Price range (min / max, USD)
- “Search” button filters products
- Display results or “No results found”

---

### C. Login (`/login`)
- Two columns:
  - **Registered Customers**:
    - Email
    - Password
    - Show password checkbox
    - Sign In button
    - Forgot password link (non-functional)
  - **New Customers**:
    - Info text
    - Create Account button (stub)

---

### D. My Account (`/account`)
- Left sidebar navigation:
  - My Account
  - My Orders
  - My Downloadable Products (stub)
  - My Wish List
  - Address Book
  - Account Information
  - Stored Payment Methods (stub)
  - My Product Reviews (stub)
  - Newsletter Subscriptions (stub)
- Main content:
  - Account information (name, email)
  - Default billing & shipping addresses
  - Newsletter status
  - Recent orders table:
    - Order #
    - Date
    - Ship To
    - Order Total
    - Status
    - Actions: View Order, Reorder

---

### E. My Wish List (`/account/wishlist`)
- Empty state message if no items
- Product list/grid if populated
- Remove and Add to Cart actions

---

### F. Category Pages (`/category/:slug`)
- Breadcrumb navigation
- Category title
- Left filter rail:
  - “Shop By”
  - Price ranges with item counts
- Top controls:
  - Items count text (e.g., “Items 1–12 of N”)
  - Sort by: Position, Price (Low→High, High→Low), Rating
- Product grid:
  - Image, name, rating, price, Add to Cart, wishlist icon
- Pagination (simple next/prev or page numbers)

---

## 5. Visual & UX Guidelines

- Clean white background
- Light gray separators
- Blue primary buttons (“Add to Cart”)
- Classic storefront look (not ultra-minimal)
- Fully responsive:
  - Desktop: sidebar + multi-column grid
  - Mobile: stacked layout, collapsible filters

---

## 6. Acceptance Criteria

- Home page shows product grid with cart and wishlist actions
- Category dropdown navigation works
- Advanced Search filters products correctly
- Login enables account pages
- My Account shows user info, addresses, and orders
- Wish List supports empty and populated states
- Category pages support filtering, sorting, and pagination

---

End goal: a realistic, navigable e-commerce demo environment suitable for UI/UX testing and agent interaction.
