# API Contracts (Jira Clone)

Source of truth: `jira/design/spec.api.json` (this document is a human-readable extraction).

## Local database (PostgreSQL via Docker Compose)

This repo includes a runnable PostgreSQL environment for initializing the schema + seed data and for running verification queries.

### Start the database

From the repo root:

```bash
./scripts/docker-preflight.sh

docker compose -f jira/docker/docker-compose.yml up -d --build db
docker compose -f jira/docker/docker-compose.yml ps
docker compose -f jira/docker/docker-compose.yml logs --no-color db
```

Default connection settings (as defined in `jira/docker/docker-compose.yml`):

- Host: `localhost`
- Port: `5432`
- Database: `jira`
- User: `jira`
- Password: [REDACTED]

## Authentication

Most API routes require authentication.

- Auth mechanism: `Authorization: Bearer <token>`
- If missing/invalid: `401` with the standard error envelope.

### POST /api/auth/login

- Public (no admin-only restriction)
- Body:

```json
{ "email": "user@example.com", "password": "..." }
```

### POST /api/auth/test-login

- Public helper for local/dev usage (no admin-only restriction)

## Issues

### GET /api/issues

List issues for a project.

Query params:

- `projectId` (required): project key (e.g. `DEMO`)
  - Alias: `projectKey` is accepted and treated the same as `projectId`
- `status` (optional)
- `assigneeId` (optional)
  - Alias: `assignee` is accepted and treated the same as `assigneeId`
- `q` (optional): text search
- `type` (optional)
- `priority` (optional)
- `labels` (optional): comma-separated list or repeated query params
- `sort` (optional): `created | priority | status | key`
- `order` (optional): `asc | desc`
- `page` (optional)
- `pageSize` (optional)


### POST /api/issues

Create an issue in a project.

Auth: required.

Request body:

```json
{
  "projectKey": "ACME",
  "summary": "Test issue",
  "description": "Optional markdown/text",
  "type": "task",
  "priority": "medium",
  "status": "todo",
  "labels": ["backend", "api"],
  "assigneeId": "00000000-0000-0000-0000-000000000002",
  "reporterId": "00000000-0000-0000-0000-000000000002"
}
```

Notes:
- `projectKey` is required. Alias: `projectId` is accepted and treated the same.
- `summary` is required.
- `description` is optional.
- `labels` is optional; can be an array of strings or a comma-separated string.
- `assigneeId` is optional.
- `reporterId` defaults to the authenticated user if omitted.
- Enum values are case-insensitive and normalized by the API.

Allowed enum values (normalized):
- `status`: `BACKLOG | TODO | IN_PROGRESS | IN_REVIEW | DONE`
- `priority`: `LOW | MEDIUM | HIGH | CRITICAL`
- `type`: `TASK | STORY | BUG | EPIC`

Response:
- `201 Created`
- Body: `{ "issue": { ... } }`

## Search

### GET /api/search

Global issue search.

Query params:
- `q` (required)
- `projectId` (optional) OR `projectKey` (optional)
- `status` (optional)
- `assigneeId` (optional)
  - Alias: `assignee`
- `limit` (optional, default 20, max 50)
- `offset` (optional, default 0)

### POST /api/search

Same as GET, but accepts JSON body (preferred for complex filters).

Request body:

```json
{
  "q": "onboarding",
  "projectKey": "ACME",
  "status": "todo",
  "assigneeId": "00000000-0000-0000-0000-000000000002",
  "limit": 20,
  "offset": 0
}
```

## Settings

### GET /api/settings

- Auth required
- Returns the current user's profile and settings.

Response envelope:

```json
{
  "ok": true,
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "name": "User",
      "role": "user",
      "avatarUrl": null
    },
    "settings": {
      "theme": "light",
      "notifications": {
        "email": true,
        "inApp": true
      }
    }
  }
}
```

### PATCH /api/settings

- Auth required
- Partial update; supported fields:
  - `theme`: `light | dark`
  - `notifications.email`: boolean
  - `notifications.inApp`: boolean

### PUT /api/settings

- Auth required
- Full replace (missing fields are reset to defaults)

## Comments

### PATCH /api/comments/:id

- Auth required
- Only the comment owner may edit
- If authenticated but not owner: `403`

### DELETE /api/comments/:id

- Auth required
- Only the comment owner may delete
- If authenticated but not owner: `403`
