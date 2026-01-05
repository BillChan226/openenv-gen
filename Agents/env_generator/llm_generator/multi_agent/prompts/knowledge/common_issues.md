# Common Issues and Solutions Knowledge Base

This document captures recurring issues observed during multi-agent code generation and their solutions. Use this knowledge to prevent or quickly resolve similar issues.

---

## 1. Database Issues

### 1.1 Seed Data Not Loading
**Symptoms:**
- `users` table row_count=0
- Login fails with 401 for seeded credentials
- Postgres logs show: "Database directory appears to contain a database; Skipping initialization"

**Root Cause:**
PostgreSQL only runs `/docker-entrypoint-initdb.d/*.sql` on first initialization. If DB already exists, seed scripts are skipped.

**Solution:**
- Create `dbBootstrap.js` in backend that runs seed SQL on startup when `SEED_DB=true`
- Use `ON CONFLICT DO NOTHING` in INSERT statements for idempotency
- Example:
```javascript
// app/backend/src/utils/dbBootstrap.js
const fs = require('fs');
const path = require('path');
const { pool } = require('../db');

async function bootstrap() {
  if (process.env.SEED_DB !== 'true') return;
  const seedPath = path.join(__dirname, '../../database/init/02_seed.sql');
  if (fs.existsSync(seedPath)) {
    const sql = fs.readFileSync(seedPath, 'utf8');
    await pool.query(sql);
  }
}
module.exports = { bootstrap };
```

### 1.2 Column Name Mismatch
**Symptoms:**
- API returns 500 with "column X does not exist"
- Common mismatches: `depart_time` vs `departure_at`, `nightly_price` vs `nightly_base_price_cents`, `daily_price` vs `daily_rate_cents`

**Root Cause:**
Backend routes use different column names than actual database schema.

**Solution:**
- **ALWAYS** use `db_schema()` tool to verify column names before writing routes
- Read `design/spec.database.json` first
- Use naming conventions: `*_at` for timestamps, `*_cents` for money, `*_id` for foreign keys

### 1.3 pg-pool TypeError
**Symptoms:**
- `TypeError: Cannot read properties of undefined (reading 'Promise')`
- All DB-backed endpoints return 500

**Root Cause:**
Incorrect export/import of pg Pool instance.

**Solution:**
```javascript
// WRONG - db.js
const pool = new Pool(config);
module.exports = { query: pool.query };  // Loses context!

// CORRECT - db.js
const { Pool } = require('pg');
const pool = new Pool(config);
module.exports = {
  query: (text, params) => pool.query(text, params),
  pool
};
```

### 1.4 Duplicate Key Constraint Violation
**Symptoms:**
- `ERROR: duplicate key value violates unique constraint "users_email_key"`

**Solution:**
- Use unique emails in seed data
- Use `ON CONFLICT (email) DO NOTHING` or `DO UPDATE`
- Example:
```sql
INSERT INTO users (email, ...) VALUES ('admin@example.com', ...)
ON CONFLICT (email) DO NOTHING;
```

---

## 2. Docker Issues

### 2.1 Stale Container Reference
**Symptoms:**
- `Error response from daemon: No such container: <hash>`
- Container shows as "Created" but cannot be started

**Root Cause:**
Old containers from previous compose runs with different project names.

**Solution:**
```bash
# Clean up stale containers
docker compose -p <project> down --remove-orphans
docker system prune -f

# Use unique project name
docker compose -p expedia_v2 up -d --build
```

### 2.2 Build Context Path Errors
**Symptoms:**
- `failed to solve: failed to read dockerfile`
- Build context paths wrong (`./app/*` instead of `../app/*`)

**Root Cause:**
docker-compose.yml build context relative to wrong directory.

**Solution:**
```yaml
# WRONG (docker-compose.yml in docker/)
services:
  backend:
    build: ./app/backend

# CORRECT
services:
  backend:
    build:
      context: ../app/backend
      dockerfile: Dockerfile
```

### 2.3 Port Mapping Mismatch
**Symptoms:**
- `ERR_CONNECTION_RESET` on frontend
- Service unreachable despite container running

**Root Cause:**
Host port mapped to wrong container port (e.g., 3001:80 when service runs on 3001).

**Solution:**
- Match container port to actual service listening port
- For Vite dev server: `3001:3001`
- For nginx: `80:80` or `3001:80`
- Add `EXPOSE` in Dockerfile

### 2.4 Version Attribute Warning
**Symptoms:**
- `the attribute 'version' is obsolete, it will be ignored`

**Solution:**
Remove `version: "3.8"` from docker-compose.yml (not needed in modern Docker Compose).

---

## 3. Frontend Issues

### 3.1 Missing Entry Component
**Symptoms:**
- `500 for /src/main.jsx`
- Vite error: cannot resolve import `./App.jsx`

**Root Cause:**
`src/main.jsx` imports `./App.jsx` but file doesn't exist.

**Solution:**
Create `src/App.jsx`:
```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
// ... other imports

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        {/* ... */}
      </Routes>
    </BrowserRouter>
  );
}
```

### 3.2 SPA Direct Navigation 404
**Symptoms:**
- Direct navigation to `/login`, `/flights` returns 404
- Works when navigating from home page

**Root Cause:**
Server doesn't handle SPA history fallback.

**Solution for Nginx:**
```nginx
# nginx.conf
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Solution for Vite dev:**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    historyApiFallback: true
  }
});
```

### 3.3 Missing Accessible Labels
**Symptoms:**
- Accessibility warnings: "inputs missing labels"

**Solution:**
```jsx
// WRONG
<input type="text" placeholder="Search" />

// CORRECT
<label htmlFor="search" className="sr-only">Search</label>
<input id="search" type="text" placeholder="Search" />
```

---

## 4. Backend Issues

### 4.1 Port Configuration Mismatch
**Symptoms:**
- API not reachable on documented port
- Health check fails

**Root Cause:**
Different PORT values in server.js, Dockerfile, docker-compose.yml.

**Solution:**
- Use environment variable consistently
- Match EXPOSE in Dockerfile
- Match ports mapping in docker-compose.yml

```javascript
// server.js
const PORT = process.env.PORT || 8081;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on port ${PORT}`);
});
```

### 4.2 ES Module vs CommonJS
**Symptoms:**
- `SyntaxError: Cannot use import statement outside a module`

**Solution:**
```javascript
// WRONG (in CommonJS project)
import bcrypt from 'bcryptjs';

// CORRECT
const bcrypt = require('bcryptjs');
```

Or add `"type": "module"` to package.json and use `.mjs` extension.

### 4.3 bcrypt Native Module Error (CRITICAL!)
**Symptoms:**
- `Error loading shared library bcrypt_lib.node: Exec format error`
- Backend container crashes immediately on startup
- Error mentions "ERR_DLOPEN_FAILED"

**Root Cause:**
The `bcrypt` package has native C++ bindings that are compiled for a specific architecture (e.g., macOS arm64). When Docker runs on Linux x86_64, the pre-compiled binary doesn't work.

**Solution - Use bcryptjs instead:**
```javascript
// In auth.js - ALWAYS use bcryptjs (pure JavaScript, no native bindings)
const bcrypt = require('bcryptjs');  // NOT 'bcrypt'!
```

```json
// In package.json
"bcryptjs": "^2.4.3"  // NOT "bcrypt"!
```

**Prevention:** NEVER use `bcrypt` in generated code. ALWAYS use `bcryptjs`.

### 4.4 Missing refresh_tokens Table
**Symptoms:**
- Login returns `relation "refresh_tokens" does not exist`
- Auth works until token refresh is attempted

**Root Cause:**
Database schema (01_schema.sql) doesn't include the refresh_tokens table required for JWT refresh token storage.

**Solution:**
Ensure 01_schema.sql includes:
```sql
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
```

**Prevention:** Database agent should ALWAYS include refresh_tokens table when users table exists.

### 4.3 Missing Route Handler
**Symptoms:**
- UI button doesn't work
- 404 on expected endpoint

**Solution:**
- Add route in server.js
- Create route file in `src/routes/`
- Mount route: `app.use('/api/trips', tripsRoutes);`

---

## 5. Integration Issues

### 5.1 CORS Errors
**Symptoms:**
- Frontend API calls fail with CORS error

**Solution:**
```javascript
// server.js
const cors = require('cors');
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:3001',
  credentials: true
}));
```

### 5.2 API Proxy Not Working
**Symptoms:**
- Frontend can't reach backend API
- Network errors in browser console
- `/api/*` requests return 404 or connection refused

**Solution for Vite (dev mode):**
```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://backend:8081',
        changeOrigin: true
      }
    }
  }
});
```

**Solution for Nginx (production):**
```nginx
# nginx.conf
server {
    listen 80;
    root /usr/share/nginx/html;
    
    # SPA history fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://backend:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Important:** When using nginx for production, must include BOTH history fallback AND API proxy.

---

## 6. PostgreSQL Specific

### 6.1 Array Literal Syntax
**Symptoms:**
- `syntax error at or near "["`

**Root Cause:**
Using JavaScript array syntax in PostgreSQL.

**Solution:**
```sql
-- WRONG
INSERT INTO table (tags) VALUES (['tag1', 'tag2']);

-- CORRECT (for ARRAY type)
INSERT INTO table (tags) VALUES (ARRAY['tag1', 'tag2']);

-- CORRECT (for JSONB)
INSERT INTO table (tags) VALUES (jsonb_build_array('tag1', 'tag2'));
```

### 6.2 Password Hash Format
**Symptoms:**
- Auth fails even with correct password

**Solution:**
Use proper bcrypt hash in seed data:
```sql
-- Generate with: require('bcryptjs').hashSync('admin123', 10)
INSERT INTO users (email, password_hash) VALUES 
('admin@example.com', '$2a$10$N9qo8uLOickgx2ZMRZoMy.MqrqRjC0hBHPfVH3YWkz3KlM3TrPdQy');
```

---

## 7. Docker Rebuild After Code Changes (CRITICAL)

### The #1 Reason Fixes Don't Work
**Symptoms:**
- Fixed the code (db.js, auth.js, etc.) but errors persist
- Same 500/404 errors after multiple fix attempts
- Logs show old error messages even after code fix

**Root Cause:**
Docker containers run the code from when they were built. Modifying source files does NOT automatically update running containers!

**Solution - MUST rebuild after code changes:**
```bash
# After fixing backend code (db.js, routes, etc.)
docker compose -f docker/docker-compose.yml build --no-cache backend
docker compose -f docker/docker-compose.yml up -d backend

# After fixing frontend code (nginx.conf, etc.)
docker compose -f docker/docker-compose.yml build --no-cache frontend
docker compose -f docker/docker-compose.yml up -d frontend

# Or rebuild everything
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d --build
```

**WHEN TO REBUILD:**
- After modifying `db.js`, `server.js`, any routes ➜ rebuild backend
- After modifying `nginx.conf` ➜ rebuild frontend
- After fixing any 500/TypeError ➜ rebuild affected service
- After ANY backend/frontend source code change ➜ rebuild

**IMPORTANT:** Always call `docker_build()` or `docker compose build` AFTER fixing code, BEFORE testing!

---

## 8. Tool Usage Best Practices

### 7.1 Always Check Schema First
```
1. view("design/spec.database.json")
2. db_schema()  -- if DB is running
3. THEN write routes
```

### 7.2 Lint After Every File Change
```
1. write_file() or str_replace_editor()
2. lint()
3. Fix any errors
```

### 7.3 Test API After Route Changes
```
1. Save file
2. Rebuild/restart container
3. test_api() to verify
```

---

## Quick Reference: Common Column Mappings

| Design Name | Actual DB Column |
|-------------|------------------|
| `depart_time` | `departure_at` |
| `arrive_time` | `arrival_at` |
| `nightly_price` | `nightly_base_price_cents` |
| `daily_price` | `daily_rate_cents` |
| `created` | `created_at` |
| `updated` | `updated_at` |

---

## Prevention Checklist

Before generation:
- [ ] Clean up old Docker containers
- [ ] Verify port availability
- [ ] Check for existing database volumes

During generation:
- [ ] Read spec.database.json before writing routes
- [ ] Use db_schema() to verify columns
- [ ] Lint all files after changes
- [ ] Test APIs after backend changes

After generation:
- [ ] Run full docker-compose up --build
- [ ] Test all critical paths (auth, CRUD)
- [ ] Check browser console for errors

