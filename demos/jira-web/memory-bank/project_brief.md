# Project Brief

## Overview
jira - ## Jira Software Clone - Full Functional Requirements

### CORE FEATURES (All must be working and testable):

**1. Authentication System**
- Login page with email/password
- Demo credentials pre-filled (admin@example.com / Password123!)
- Successful login redirects to Dashboard
- Logout functionality
- Session persistence (refresh page should stay logged in)

**2. Dashboard / Projects List**
- Display all projects as clickable cards
- Each project shows: name, key, description, issue count
- Click project card -> navigate to project view
- Create new project button and form

**3. Project Issues View (THREE VIEW MODES - CRITICAL)**
Each project MUST have three view modes for displaying issues:

  **3a. Board View (Kanban)**
  - Display columns: Backlog, To Do, In Progress, In Review, Done
  - Issue cards show: key, title, assignee avatar, priority badge
  - **DRAG-AND-DROP: Issue cards MUST be draggable between columns**
  - Dragging issue to different column updates its status via API
  - Visual feedback during drag (placeholder, highlight target column)

  **3b. List View**
  - Table format with columns: Key, Title, Status, Priority, Assignee, Created
  - Sortable columns (click header to sort)
  - Inline status dropdown to change status
  - Click row to open issue detail

  **3c. Summary View**
  - Statistics dashboard for the project
  - Issue count by status (pie chart or bars)
  - Recent activity timeline
  - Assignee workload distribution
  - Quick links to filtered issue lists

  **View Toggle:**
  - Toggle buttons/tabs to switch between Board/List/Summary views
  - Current view persists when navigating back to project
  - URL reflects current view (e.g., /projects/PROJ/board, /projects/PROJ/list)

**4. Issue Management**
- Create Issue Modal:
  * Title (required)
  * Description (optional, markdown support)
  * Type dropdown (Bug, Task, Story, Epic)
  * Priority dropdown (Low, Medium, High, Critical)
  * Assignee dropdown (list of users)
  * Labels/Tags multi-select
  * Submit creates issue and shows in current view
- Issue Detail Drawer/Modal:
  * Shows all issue fields
  * Inline editing for all fields
  * Status transition buttons
  * Comments section
  * Activity/history log
  * Attachments section (placeholder OK)

**5. Comments System**
- View comments on issue detail
- Add new comment with text input
- Edit/Delete own comments
- Comments show author avatar, name, timestamp, content
- Markdown support in comments

**6. Search**
- Global search bar in header (always visible)
- Search by issue key, title, or description
- Filter by project, status, assignee
- Results show matching issues with project context
- Click result -> navigate to issue detail

**7. Settings Page**
- User profile display and edit
- **THEME TOGGLE: Dark mode / Light mode switch (CRITICAL)**
- Notification preferences
- Keyboard shortcuts help

### UI/UX REQUIREMENTS:
- **THEME: Both Dark and Light modes MUST work**
- Theme toggle in header or settings
- Theme persists in localStorage
- Responsive layout (collapsible sidebar + main content)
- Loading states for all async operations (skeleton loaders)
- Error states with retry buttons
- Empty states with helpful messages and action buttons
- All buttons must be clickable and functional
- All forms must submit and show feedback
- Smooth animations for drag-and-drop
- Toast notifications for actions (created, updated, deleted)

### DATA REQUIREMENTS:
- Seed data with 3+ projects (ACME, WEBDEV, MOBILE)
- At least 25 issues across projects
- Issues distributed across all statuses
- 5+ users with avatars for assignee selection
- Sample comments on multiple issues
- Test credentials: admin@example.com / Password123!

### VERIFICATION CHECKLIST:
1. Can login with demo credentials
2. Dashboard shows projects after login
3. Can click project to view issues
4. **Board view shows columns with draggable issue cards**
5. **Can drag issue card to different column (status updates)**
6. **List view shows issues in table format**
7. **Summary view shows project statistics**
8. **View toggle switches between Board/List/Summary**
9. Can click issue to see details
10. Can create new issue via modal
11. Issue appears in view after creation
12. Can edit issue fields inline
13. Can add comment to issue
14. Search returns relevant results
15. **Dark/Light theme toggle works**
16. **Theme persists after page refresh**

## Core Requirements
- ## Jira Software Clone - Full Functional Requirements

### CORE FEATURES (All must be working and testable):

**1. Authentication System**
- Login page with email/password
- Demo credentials pre-filled (admin@example.com / Password123!)
- Successful login redirects to Dashboard
- Logout functionality
- Session persistence (refresh page should stay logged in)

**2. Dashboard / Projects List**
- Display all projects as clickable cards
- Each project shows: name, key, description, issue count
- Click project card -> navigate to project view
- Create new project button and form

**3. Project Issues View (THREE VIEW MODES - CRITICAL)**
Each project MUST have three view modes for displaying issues:

  **3a. Board View (Kanban)**
  - Display columns: Backlog, To Do, In Progress, In Review, Done
  - Issue cards show: key, title, assignee avatar, priority badge
  - **DRAG-AND-DROP: Issue cards MUST be draggable between columns**
  - Dragging issue to different column updates its status via API
  - Visual feedback during drag (placeholder, highlight target column)

  **3b. List View**
  - Table format with columns: Key, Title, Status, Priority, Assignee, Created
  - Sortable columns (click header to sort)
  - Inline status dropdown to change status
  - Click row to open issue detail

  **3c. Summary View**
  - Statistics dashboard for the project
  - Issue count by status (pie chart or bars)
  - Recent activity timeline
  - Assignee workload distribution
  - Quick links to filtered issue lists

  **View Toggle:**
  - Toggle buttons/tabs to switch between Board/List/Summary views
  - Current view persists when navigating back to project
  - URL reflects current view (e.g., /projects/PROJ/board, /projects/PROJ/list)

**4. Issue Management**
- Create Issue Modal:
  * Title (required)
  * Description (optional, markdown support)
  * Type dropdown (Bug, Task, Story, Epic)
  * Priority dropdown (Low, Medium, High, Critical)
  * Assignee dropdown (list of users)
  * Labels/Tags multi-select
  * Submit creates issue and shows in current view
- Issue Detail Drawer/Modal:
  * Shows all issue fields
  * Inline editing for all fields
  * Status transition buttons
  * Comments section
  * Activity/history log
  * Attachments section (placeholder OK)

**5. Comments System**
- View comments on issue detail
- Add new comment with text input
- Edit/Delete own comments
- Comments show author avatar, name, timestamp, content
- Markdown support in comments

**6. Search**
- Global search bar in header (always visible)
- Search by issue key, title, or description
- Filter by project, status, assignee
- Results show matching issues with project context
- Click result -> navigate to issue detail

**7. Settings Page**
- User profile display and edit
- **THEME TOGGLE: Dark mode / Light mode switch (CRITICAL)**
- Notification preferences
- Keyboard shortcuts help

### UI/UX REQUIREMENTS:
- **THEME: Both Dark and Light modes MUST work**
- Theme toggle in header or settings
- Theme persists in localStorage
- Responsive layout (collapsible sidebar + main content)
- Loading states for all async operations (skeleton loaders)
- Error states with retry buttons
- Empty states with helpful messages and action buttons
- All buttons must be clickable and functional
- All forms must submit and show feedback
- Smooth animations for drag-and-drop
- Toast notifications for actions (created, updated, deleted)

### DATA REQUIREMENTS:
- Seed data with 3+ projects (ACME, WEBDEV, MOBILE)
- At least 25 issues across projects
- Issues distributed across all statuses
- 5+ users with avatars for assignee selection
- Sample comments on multiple issues
- Test credentials: admin@example.com / Password123!

### VERIFICATION CHECKLIST:
1. Can login with demo credentials
2. Dashboard shows projects after login
3. Can click project to view issues
4. **Board view shows columns with draggable issue cards**
5. **Can drag issue card to different column (status updates)**
6. **List view shows issues in table format**
7. **Summary view shows project statistics**
8. **View toggle switches between Board/List/Summary**
9. Can click issue to see details
10. Can create new issue via modal
11. Issue appears in view after creation
12. Can edit issue fields inline
13. Can add comment to issue
14. Search returns relevant results
15. **Dark/Light theme toggle works**
16. **Theme persists after page refresh**

## Goals
- Build a Jira-like issue tracking system with projects, boards, issues, workflows, and collaboration.
- Provide a runnable dev environment (frontend + backend + database + docker).

## Scope
- In scope: Jira-like UI, REST API, PostgreSQL schema/seed, auth, search, and basic workflows.
- Out of scope: Full enterprise Jira parity, marketplace apps, SSO/SCIM, advanced permissions.

## Success Criteria
- No obvious runtime errors; core flows work end-to-end (create/update issues, move status, comment, search).
- Services start via docker compose and basic smoke tests pass.
