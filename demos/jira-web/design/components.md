# Component Inventory (Jira Clone)

Source of truth: `jira/design/spec.ui.json` (tokens/layout patterns) and `jira/design/spec.project.json` (flows).

This document enumerates the expected frontend component structure for acceptance criteria and verification.

## Pages (routes)

### `LoginPage` (`/login`)
- **Responsibility:** login form, validation, token persistence, redirect.
- **Key states:** idle, submitting, error banner.
- **Interactions:** calls `POST /api/auth/login`.

### `RegisterPage` (`/register`)
- **Responsibility:** create account.
- **Key states:** submitting, validation errors.
- **Interactions:** calls `POST /api/auth/register`.

### `DashboardPage` (`/dashboard`)
- **Responsibility:** list projects, create project CTA.
- **Key states:** loading skeleton grid, empty state, error with retry.
- **Interactions:** `GET /api/projects`, `POST /api/projects`.

### `ProjectBoardPage` (`/projects/:projectKey/board`)
- **Responsibility:** kanban board with drag-and-drop, board toolbar.
- **Key states:** loading columns, empty board, error banner.
- **Interactions:** `GET /api/projects/:projectKey/issues`, `POST /api/issues/:issueId/move`.

### `ProjectListPage` (`/projects/:projectKey/list`)
- **Responsibility:** table/list view of issues with sorting/filtering.
- **Key states:** loading table, empty results, error.
- **Interactions:** `GET /api/projects/:projectKey/issues` with query params.

### `ProjectSummaryPage` (`/projects/:projectKey/summary`)
- **Responsibility:** project stats, activity timeline.
- **Key states:** loading, empty activity.

### `SearchPage` (`/search` or global overlay)
- **Responsibility:** global search results with filters.
- **Key states:** empty query, loading, no results.
- **Interactions:** `GET /api/search?q=...`.

### `SettingsPage` (`/settings`)
- **Responsibility:** user profile/preferences (theme + notifications).
- **Key states:** loading current settings, saving, save error.
- **Interactions:** `GET /api/settings/me`, `PUT /api/settings/me`.

---

## Reference Screenshot Mapping (design → implementation)

The following mappings explicitly tie the selected reference screenshots in `jira/screenshots/` to the layouts/pages/components in this project. Each entry lists concrete layout/interaction cues to implement.

### App shell / global navigation

#### `AppShell`, `TopHeader`, `SidebarNav`
- **Reference:** `screenshots/jira_ticketing.png`
- **Cues to incorporate:**
  - Persistent left sidebar with primary navigation; main content to the right.
  - Compact top header with breadcrumbs/project context on the left and user controls on the right.
  - Header/side chrome uses subtle borders/dividers rather than heavy shadows.
  - Content area uses generous padding and a light neutral background.

### Project board (kanban)

#### `ProjectBoardPage`, `Board`, `BoardColumn`, `IssueCard`, `BoardToolbar`
- **Reference:** `screenshots/jira_example.png`
- **Cues to incorporate:**
  - Columns are equal-width vertical stacks with a sticky/visible column header (status + count).
  - Cards are compact with clear hierarchy: issue key/title first, metadata (priority/assignee) secondary.
  - Board toolbar sits above columns and contains search/filter controls aligned horizontally.
  - Drag affordance: card elevation/outline while dragging; drop targets highlight subtly.

### Issue detail overlay

#### `IssueDetailDrawer` (or `IssueDetailModal`), `IssueFieldsPanel`, `CommentsList`, `CommentEditor`
- **Reference:** `screenshots/click_todo_item.png`
- **Cues to incorporate:**
  - Overlay opens from the side (drawer) or as a focused modal; background is dimmed and non-interactive.
  - Prominent close action in the top-right; Escape closes.
  - Two-zone layout: primary content (title/description/comments) and a secondary metadata panel (status/assignee/priority).
  - Inline editing: click-to-edit fields with clear focus state and save/cancel behavior.

### Create issue flow

#### `CreateIssueModal` (or `CreateIssuePage`)
- **Reference:** `screenshots/jira_ticketing.png` (overall form density) and `screenshots/jira_example.png` (issue field ordering cues)
- **Cues to incorporate:**
  - Modal form uses a clear vertical rhythm: title first, then description, then structured fields.
  - Primary CTA (Create) is visually dominant; secondary cancel is less prominent.
  - Validation appears inline under fields; submit disabled while invalid/submitting.

### Assignee picker / user display

#### `Avatar`, `UserPicker` (part of `IssueFieldsPanel`)
- **Reference:** `screenshots/jira_example.png`
- **Cues to incorporate:**
  - Assignee shown as avatar + name; unassigned state is explicit (e.g., “Unassigned”).
  - Picker is searchable and optimized for quick selection (typeahead).
  - Selected user is reflected immediately in the field (optimistic UI), then persisted via API.

---


## Layouts

### `AppShell`
- **Responsibility:** global layout wrapper: sidebar + header + main content.
- **Props:** `children`.
- **Key states:** authenticated vs unauthenticated rendering.

### `AuthLayout`
- **Responsibility:** centered card layout for login/register.

---

## Global UI Components

### `SidebarNav`
- **Responsibility:** navigation groups (Dashboard, Projects, Settings).
- **States:** collapsed/expanded (optional).

### `TopHeader`
- **Responsibility:** breadcrumbs/project name, global search entry, user avatar menu.
- **Interactive elements:**
  - Global search input (opens overlay or navigates to search page)
  - Avatar menu (logout)

### `Tabs` / `ProjectViewTabs`
- **Responsibility:** switch between Board/List/Summary for a project.
- **Props:** `active`, `onChange`, `tabs[]`.

### `Button`, `IconButton`
- **Responsibility:** consistent button styling (primary/secondary/danger).
- **States:** disabled, loading.

### `Input`, `Select`, `Textarea`
- **Responsibility:** form controls with validation messaging.

### `Chip` / `Badge`
- **Responsibility:** status/priority/label chips.

### `Avatar`
- **Responsibility:** user avatar circle (image or initials).

### `Modal` and/or `Drawer`
- **Responsibility:** overlay container with focus trap.
- **States:** open/close animations.

### `ToastProvider`
- **Responsibility:** global notifications for success/error.

### `Skeleton`
- **Responsibility:** loading placeholders for cards/rows.

---

## Feature Components

### DnD Board (AC-required)

#### `Board`
- **Responsibility:** render columns and issue cards; orchestrate drag context.
- **Props:** `columns`, `issuesByStatus`, `onMoveIssue`.
- **States:** loading, empty, error.

#### `BoardColumn`
- **Responsibility:** column header + droppable area.
- **Props:** `status`, `label`, `count`, `children`.

#### `IssueCard`
- **Responsibility:** compact issue representation.
- **Props:** `issue`.
- **States:** dragging (elevated), normal.

#### `BoardToolbar`
- **Responsibility:** search/filter within project board.
- **Props:** `query`, `onQueryChange`, `filters`, `onFilterChange`.

### Issue create (modal)

#### `CreateIssueModal`
- **Responsibility:** create issue form.
- **Props:** `projectKey`, `open`, `onClose`, `onCreated`.
- **States:** submitting, validation errors.

### Issue detail drawer/modal (AC-required)

#### `IssueDetailDrawer` (or `IssueDetailModal`)
- **Responsibility:** show issue details + inline editing + comments.
- **Props:** `issueId`, `open`, `onClose`.
- **States:** loading issue, saving field edits, error.

#### `IssueFieldsPanel`
- **Responsibility:** editable fields (title, description, status, priority, assignee, labels).

#### `InlineEditableText`
- **Responsibility:** click-to-edit pattern for title/description.
- **Props:** `value`, `onSave`, `placeholder`.
- **States:** editing, saving, error.

### Comments

#### `CommentsList`
- **Responsibility:** render comments.
- **Props:** `issueId`.
- **States:** loading, empty.

#### `CommentEditor`
- **Responsibility:** markdown composer for new/edit comment.
- **Props:** `initialValue`, `onSubmit`, `onCancel`.
- **States:** submitting.

---

## Hooks / Data Layer

### `useAuth`
- **Responsibility:** token persistence, current user, login/logout.
- **Exposes:** `user`, `token`, `login()`, `logout()`, `register()`.

### `useProjects`
- **Responsibility:** fetch/create projects.

### `useIssues`
- **Responsibility:** list/search issues, create/update/move.

### `useComments`
- **Responsibility:** CRUD comments.

### `useSettings`
- **Responsibility:** read/write user settings.

---

## Stores (optional)

If using a global store (Context/Zustand/Redux):

- `authStore`: token + user
- `uiStore`: theme, modal/drawer state
- `projectStore`: current project metadata

---

## Key UX States (must be handled)

- **Loading:** skeletons for dashboard cards, board columns, list rows, issue detail.
- **Empty:**
  - no projects
  - no issues in project
  - no search results
  - no comments
- **Error:** inline error panels with retry for fetch failures.
- **Optimistic updates:** DnD move should update UI immediately and revert on API failure.

---

## Mapping to Acceptance Criteria

- **DnD board:** `Board` + `BoardColumn` + `IssueCard` + `POST /api/issues/:issueId/move`
- **Issue detail drawer/modal:** `IssueDetailDrawer/Modal` with inline editing + comments
- **Global search:** `TopHeader` search + `SearchPage`/overlay + `GET /api/search`
- **Settings view/save:** `SettingsPage` + `useSettings` + `GET/PUT /api/settings/me`
