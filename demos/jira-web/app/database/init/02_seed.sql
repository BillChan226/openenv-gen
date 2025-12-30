-- 02_seed.sql
-- Jira Software Clone - Seed data
--
-- Includes:
-- * 6 users (1 admin, 4 members, 1 viewer)
-- * 3 projects (ACME, WEBDEV, MOBILE)
-- * 30 issues across all statuses
-- * project-scoped labels + issue-label joins
-- * comments on multiple issues
-- * activity events
-- * attachments placeholder metadata
-- * user settings (theme + notification prefs)

BEGIN;

-- -----------------------------------------------------------------------------
-- Users
-- Password for all seeded users: Password123!
-- bcrypt hash (cost 10) for "Password123!":
-- $2b$10$du5Gla0d.le46o5LzpKTjeFInMl.w6oozMQ9NBEiAkQWSbEnxNv.y
-- -----------------------------------------------------------------------------

INSERT INTO app_user (id, email, password_hash, name, role, avatar_url, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000001', 'admin@example.com', '$2b$10$du5Gla0d.le46o5LzpKTjeFInMl.w6oozMQ9NBEiAkQWSbEnxNv.y', 'Admin User', 'admin',  'https://i.pravatar.cc/150?img=12', NOW() - INTERVAL '120 days', NOW() - INTERVAL '1 day'),
  ('00000000-0000-0000-0000-000000000002', 'alice@example.com', '$2b$10$du5Gla0d.le46o5LzpKTjeFInMl.w6oozMQ9NBEiAkQWSbEnxNv.y', 'Alice Chen', 'member', 'https://i.pravatar.cc/150?img=47', NOW() - INTERVAL '110 days', NOW() - INTERVAL '2 days'),
  ('00000000-0000-0000-0000-000000000003', 'bob@example.com',   '$2b$10$du5Gla0d.le46o5LzpKTjeFInMl.w6oozMQ9NBEiAkQWSbEnxNv.y', 'Bob Rivera', 'member',  'https://i.pravatar.cc/150?img=33', NOW() - INTERVAL '105 days', NOW() - INTERVAL '3 days'),
  ('00000000-0000-0000-0000-000000000004', 'carol@example.com', '$2b$10$du5Gla0d.le46o5LzpKTjeFInMl.w6oozMQ9NBEiAkQWSbEnxNv.y', 'Carol Singh', 'member', 'https://i.pravatar.cc/150?img=5',  NOW() - INTERVAL '100 days', NOW() - INTERVAL '1 day'),
  ('00000000-0000-0000-0000-000000000005', 'dave@example.com',  '$2b$10$du5Gla0d.le46o5LzpKTjeFInMl.w6oozMQ9NBEiAkQWSbEnxNv.y', 'Dave Patel', 'member',  'https://i.pravatar.cc/150?img=22', NOW() - INTERVAL '95 days',  NOW() - INTERVAL '4 days'),
  ('00000000-0000-0000-0000-000000000006', 'viewer@example.com','$2b$10$du5Gla0d.le46o5LzpKTjeFInMl.w6oozMQ9NBEiAkQWSbEnxNv.y', 'Violet Viewer', 'viewer','https://i.pravatar.cc/150?img=65', NOW() - INTERVAL '90 days',  NOW() - INTERVAL '10 days')
ON CONFLICT (id) DO NOTHING;

-- QA test user (matches automated test instructions)
-- Password: password123

-- Password: password123
-- bcrypt hash (cost 10) for "password123":
-- $2b$10$LSDxHfZtQLfpzf0NWEj1teczqSDSsg29nRuPxBu5/aiWwf8P6l0X6
INSERT INTO app_user (id, email, password_hash, name, role, avatar_url, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000007', 'test@example.com', '$2b$10$LSDxHfZtQLfpzf0NWEj1teczqSDSsg29nRuPxBu5/aiWwf8P6l0X6', 'Test User', 'admin', 'https://i.pravatar.cc/150?img=13', NOW() - INTERVAL '30 days', NOW() - INTERVAL '1 day')
ON CONFLICT (id) DO NOTHING;

-- bcrypt hash (cost 10) for "password123":
-- $2b$10$BbrC7HrTAeWwoDy46j19XOrOUBzICX8Qo4Fo32dARHS/n4rKwEgfK
INSERT INTO app_user (id, email, password_hash, name, role, avatar_url, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000007', 'test@example.com', '$2b$10$BbrC7HrTAeWwoDy46j19XOrOUBzICX8Qo4Fo32dARHS/n4rKwEgfK', 'Test User', 'member', 'https://i.pravatar.cc/150?img=68', NOW() - INTERVAL '30 days', NOW() - INTERVAL '1 day')
ON CONFLICT (id) DO NOTHING;


-- User settings (theme + notification prefs)
INSERT INTO user_settings (user_id, theme, notifications_email, notifications_in_app, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000001', 'dark',  true,  true,  NOW() - INTERVAL '120 days', NOW() - INTERVAL '1 day'),
  ('00000000-0000-0000-0000-000000000002', 'light', true,  true,  NOW() - INTERVAL '110 days', NOW() - INTERVAL '2 days'),
  ('00000000-0000-0000-0000-000000000003', 'dark',  false, true,  NOW() - INTERVAL '105 days', NOW() - INTERVAL '3 days'),
  ('00000000-0000-0000-0000-000000000004', 'light', true,  false, NOW() - INTERVAL '100 days', NOW() - INTERVAL '1 day'),
  ('00000000-0000-0000-0000-000000000005', 'light', false, false, NOW() - INTERVAL '95 days',  NOW() - INTERVAL '4 days'),
  ('00000000-0000-0000-0000-000000000006', 'light', false, true,  NOW() - INTERVAL '90 days',  NOW() - INTERVAL '10 days')
ON CONFLICT (user_id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Projects
-- -----------------------------------------------------------------------------
INSERT INTO project (id, key, name, description, lead_user_id, is_archived, created_at, updated_at) VALUES
  ('aaaaaaaa-0000-0000-0000-000000000001', 'ACME',   'ACME Platform', 'Customer onboarding, billing, and internal tooling for ACME.', '00000000-0000-0000-0000-000000000002', false, NOW() - INTERVAL '80 days', NOW() - INTERVAL '1 day'),
  ('aaaaaaaa-0000-0000-0000-000000000002', 'WEBDEV', 'Web Dev',       'Marketing site and web app improvements.',                     '00000000-0000-0000-0000-000000000003', false, NOW() - INTERVAL '60 days', NOW() - INTERVAL '2 days'),
  ('aaaaaaaa-0000-0000-0000-000000000003', 'MOBILE', 'Mobile App',    'iOS/Android feature work and bug fixes.',                      '00000000-0000-0000-0000-000000000004', false, NOW() - INTERVAL '45 days', NOW() - INTERVAL '3 days')
ON CONFLICT (id) DO NOTHING;

-- Activity: project created
-- Idempotent insert: activity_event has no natural unique key, so we avoid duplicates by
-- checking for an existing row with the same (project_id, type, summary).
INSERT INTO activity_event (project_id, issue_id, actor_user_id, type, summary, metadata, created_at)
SELECT v.project_id, v.issue_id, v.actor_user_id, v.type, v.summary, v.metadata, v.created_at
FROM (
  VALUES
    ('aaaaaaaa-0000-0000-0000-000000000001'::uuid, NULL::uuid, '00000000-0000-0000-0000-000000000002'::uuid, 'PROJECT_CREATED', 'Project ACME created',   jsonb_build_object('projectKey','ACME'),   NOW() - INTERVAL '80 days'),
    ('aaaaaaaa-0000-0000-0000-000000000002'::uuid, NULL::uuid, '00000000-0000-0000-0000-000000000003'::uuid, 'PROJECT_CREATED', 'Project WEBDEV created', jsonb_build_object('projectKey','WEBDEV'), NOW() - INTERVAL '60 days'),
    ('aaaaaaaa-0000-0000-0000-000000000003'::uuid, NULL::uuid, '00000000-0000-0000-0000-000000000004'::uuid, 'PROJECT_CREATED', 'Project MOBILE created', jsonb_build_object('projectKey','MOBILE'), NOW() - INTERVAL '45 days')
) AS v(project_id, issue_id, actor_user_id, type, summary, metadata, created_at)
WHERE NOT EXISTS (
  SELECT 1
  FROM activity_event ae
  WHERE ae.project_id = v.project_id
    AND ae.type = v.type
    AND ae.summary = v.summary
);

-- -----------------------------------------------------------------------------
-- Labels (project-scoped)
-- -----------------------------------------------------------------------------
INSERT INTO label (id, project_id, name, color, created_at) VALUES
  -- ACME
  ('11111111-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'backend',   '#0052CC', NOW() - INTERVAL '79 days'),
  ('11111111-0000-0000-0000-000000000002', 'aaaaaaaa-0000-0000-0000-000000000001', 'frontend',  '#36B37E', NOW() - INTERVAL '79 days'),
  ('11111111-0000-0000-0000-000000000003', 'aaaaaaaa-0000-0000-0000-000000000001', 'infra',     '#6554C0', NOW() - INTERVAL '79 days'),
  ('11111111-0000-0000-0000-000000000004', 'aaaaaaaa-0000-0000-0000-000000000001', 'security',  '#DE350B', NOW() - INTERVAL '79 days'),
  ('11111111-0000-0000-0000-000000000005', 'aaaaaaaa-0000-0000-0000-000000000001', 'performance','#FF991F', NOW() - INTERVAL '79 days'),
  -- WEBDEV
  ('11111111-0000-0000-0000-000000000006', 'aaaaaaaa-0000-0000-0000-000000000002', 'ui',        '#00B8D9', NOW() - INTERVAL '59 days'),
  ('11111111-0000-0000-0000-000000000007', 'aaaaaaaa-0000-0000-0000-000000000002', 'seo',       '#8777D9', NOW() - INTERVAL '59 days'),
  ('11111111-0000-0000-0000-000000000008', 'aaaaaaaa-0000-0000-0000-000000000002', 'analytics', '#2684FF', NOW() - INTERVAL '59 days'),
  -- MOBILE
  ('11111111-0000-0000-0000-000000000009', 'aaaaaaaa-0000-0000-0000-000000000003', 'android',   '#00875A', NOW() - INTERVAL '44 days'),
  ('11111111-0000-0000-0000-00000000000a', 'aaaaaaaa-0000-0000-0000-000000000003', 'ios',       '#253858', NOW() - INTERVAL '44 days'),
  ('11111111-0000-0000-0000-00000000000b', 'aaaaaaaa-0000-0000-0000-000000000003', 'release',   '#FF5630', NOW() - INTERVAL '44 days')
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Issues
-- We store both (project_id, seq) and a globally-unique issue key like ACME-12.
-- Statuses cover: BACKLOG, TODO, IN_PROGRESS, IN_REVIEW, DONE.
-- -----------------------------------------------------------------------------

-- ACME (15 issues: 3 in each status)
INSERT INTO issue (id, project_id, key, seq, title, description, type, priority, status, assignee_user_id, reporter_user_id, created_at, updated_at) VALUES
  ('bbbbbbbb-0000-0000-0000-000000000001','aaaaaaaa-0000-0000-0000-000000000001','ACME-1',  1,'Set up project repository','Initialize repo, branching strategy, and CODEOWNERS.\n\n- [ ] Add linting\n- [ ] Add CI','TASK','HIGH','DONE','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001', NOW() - INTERVAL '70 days', NOW() - INTERVAL '50 days'),
  ('bbbbbbbb-0000-0000-0000-000000000002','aaaaaaaa-0000-0000-0000-000000000001','ACME-2',  2,'Implement login (JWT)','Auth endpoints + session persistence.\n\nSearch keywords: auth jwt token refresh.','STORY','CRITICAL','DONE','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '68 days', NOW() - INTERVAL '45 days'),
  ('bbbbbbbb-0000-0000-0000-000000000003','aaaaaaaa-0000-0000-0000-000000000001','ACME-3',  3,'Database migrations baseline','Create schema and seed scripts for local dev.','TASK','HIGH','DONE','00000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '67 days', NOW() - INTERVAL '44 days'),

  ('bbbbbbbb-0000-0000-0000-000000000004','aaaaaaaa-0000-0000-0000-000000000001','ACME-4',  4,'Add global search bar','Search by issue key/title/description with filters.\n\nTry searching for: onboarding, billing, performance.','STORY','HIGH','TODO','00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '20 days', NOW() - INTERVAL '2 days'),
  ('bbbbbbbb-0000-0000-0000-000000000005','aaaaaaaa-0000-0000-0000-000000000001','ACME-5',  5,'Fix flaky session persistence','Users get logged out after refresh in some cases.','BUG','HIGH','TODO','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000001', NOW() - INTERVAL '18 days', NOW() - INTERVAL '1 day'),
  ('bbbbbbbb-0000-0000-0000-000000000006','aaaaaaaa-0000-0000-0000-000000000001','ACME-6',  6,'Design issue detail drawer','Two-column layout with inline editing and comments.','STORY','MEDIUM','TODO',NULL,'00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '16 days', NOW() - INTERVAL '5 days'),

  ('bbbbbbbb-0000-0000-0000-000000000007','aaaaaaaa-0000-0000-0000-000000000001','ACME-7',  7,'Implement drag-and-drop board','DnD between Backlog/To Do/In Progress/In Review/Done.','STORY','CRITICAL','IN_PROGRESS','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001', NOW() - INTERVAL '12 days', NOW() - INTERVAL '1 day'),
  ('bbbbbbbb-0000-0000-0000-000000000008','aaaaaaaa-0000-0000-0000-000000000001','ACME-8',  8,'Optimize issue list sorting','Add indexes for created_at, status, assignee.','TASK','MEDIUM','IN_PROGRESS','00000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '10 days', NOW() - INTERVAL '2 hours'),
  ('bbbbbbbb-0000-0000-0000-000000000009','aaaaaaaa-0000-0000-0000-000000000001','ACME-9',  9,'Investigate slow search queries','Full-text search tuning and GIN index checks.','TASK','HIGH','IN_PROGRESS','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '9 days', NOW() - INTERVAL '6 hours'),

  ('bbbbbbbb-0000-0000-0000-00000000000a','aaaaaaaa-0000-0000-0000-000000000001','ACME-10',10,'Security review for auth endpoints','Threat model and basic rate limiting.','TASK','HIGH','IN_REVIEW','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000004', NOW() - INTERVAL '7 days', NOW() - INTERVAL '1 day'),
  ('bbbbbbbb-0000-0000-0000-00000000000b','aaaaaaaa-0000-0000-0000-000000000001','ACME-11',11,'Refactor issue status transitions','Ensure allowed transitions align with workflow.','BUG','MEDIUM','IN_REVIEW','00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '6 days', NOW() - INTERVAL '12 hours'),
  ('bbbbbbbb-0000-0000-0000-00000000000c','aaaaaaaa-0000-0000-0000-000000000001','ACME-12',12,'Add theme toggle persistence','Persist theme in localStorage and user settings.','STORY','LOW','IN_REVIEW','00000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '5 days', NOW() - INTERVAL '3 hours'),

  ('bbbbbbbb-0000-0000-0000-00000000000d','aaaaaaaa-0000-0000-0000-000000000001','ACME-13',13,'Onboarding checklist improvements','Improve onboarding steps and empty states.\n\nSearch keywords: onboarding empty state.','TASK','LOW','BACKLOG',NULL,'00000000-0000-0000-0000-000000000004', NOW() - INTERVAL '3 days', NOW() - INTERVAL '2 days'),
  ('bbbbbbbb-0000-0000-0000-00000000000e','aaaaaaaa-0000-0000-0000-000000000001','ACME-14',14,'Billing export CSV','Export invoices and usage to CSV.\n\nSearch keywords: billing export csv.','STORY','MEDIUM','BACKLOG','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day'),
  ('bbbbbbbb-0000-0000-0000-00000000000f','aaaaaaaa-0000-0000-0000-000000000001','ACME-15',15,'Performance: reduce dashboard load time','Profile slow queries, add caching where needed.\n\nSearch keywords: performance dashboard.','BUG','CRITICAL','BACKLOG','00000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000001', NOW() - INTERVAL '1 day', NOW() - INTERVAL '6 hours')
ON CONFLICT (id) DO NOTHING;

-- WEBDEV (10 issues: 2 in each status)
INSERT INTO issue (id, project_id, key, seq, title, description, type, priority, status, assignee_user_id, reporter_user_id, created_at, updated_at) VALUES
  ('bbbbbbbb-0000-0000-0000-000000000010','aaaaaaaa-0000-0000-0000-000000000002','WEBDEV-1',  1,'Landing page refresh','Update hero, testimonials, and CTA.\n\nLabels: ui, seo.','STORY','MEDIUM','DONE','00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '40 days', NOW() - INTERVAL '30 days'),
  ('bbbbbbbb-0000-0000-0000-000000000011','aaaaaaaa-0000-0000-0000-000000000002','WEBDEV-2',  2,'Fix broken sitemap.xml','Search engines failing to crawl.\n\nSearch keywords: seo sitemap.','BUG','HIGH','DONE','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000001', NOW() - INTERVAL '35 days', NOW() - INTERVAL '28 days'),

  ('bbbbbbbb-0000-0000-0000-000000000012','aaaaaaaa-0000-0000-0000-000000000002','WEBDEV-3',  3,'Add cookie consent banner','GDPR compliance for analytics.','TASK','MEDIUM','TODO','00000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '8 days', NOW() - INTERVAL '3 days'),
  ('bbbbbbbb-0000-0000-0000-000000000013','aaaaaaaa-0000-0000-0000-000000000002','WEBDEV-4',  4,'Improve Lighthouse score','Reduce unused JS and optimize images.\n\nSearch keywords: performance lighthouse.','TASK','HIGH','TODO',NULL,'00000000-0000-0000-0000-000000000004', NOW() - INTERVAL '7 days', NOW() - INTERVAL '2 days'),

  ('bbbbbbbb-0000-0000-0000-000000000014','aaaaaaaa-0000-0000-0000-000000000002','WEBDEV-5',  5,'Implement pricing page A/B test','Track conversion metrics in analytics.', 'STORY','MEDIUM','IN_PROGRESS','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '6 days', NOW() - INTERVAL '1 day'),
  ('bbbbbbbb-0000-0000-0000-000000000015','aaaaaaaa-0000-0000-0000-000000000002','WEBDEV-6',  6,'Fix navbar overlap on mobile','Header overlaps content on small screens.', 'BUG','HIGH','IN_PROGRESS','00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '5 days', NOW() - INTERVAL '6 hours'),

  ('bbbbbbbb-0000-0000-0000-000000000016','aaaaaaaa-0000-0000-0000-000000000002','WEBDEV-7',  7,'Review analytics event taxonomy','Ensure consistent event naming.', 'TASK','LOW','IN_REVIEW','00000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '4 days', NOW() - INTERVAL '2 days'),
  ('bbbbbbbb-0000-0000-0000-000000000017','aaaaaaaa-0000-0000-0000-000000000002','WEBDEV-8',  8,'SEO meta tags audit','Verify title/description metadata on key pages.', 'TASK','MEDIUM','IN_REVIEW','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001', NOW() - INTERVAL '3 days', NOW() - INTERVAL '1 day'),

  ('bbbbbbbb-0000-0000-0000-000000000018','aaaaaaaa-0000-0000-0000-000000000002','WEBDEV-9',  9,'Draft new component library','Document reusable UI components.', 'EPIC','LOW','BACKLOG',NULL,'00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'),
  ('bbbbbbbb-0000-0000-0000-000000000019','aaaaaaaa-0000-0000-0000-000000000002','WEBDEV-10',10,'Spike: migrate to Vite','Evaluate migration steps and risks.', 'TASK','MEDIUM','BACKLOG','00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day')
ON CONFLICT (id) DO NOTHING;

-- MOBILE (5 issues: 1 in each status)
INSERT INTO issue (id, project_id, key, seq, title, description, type, priority, status, assignee_user_id, reporter_user_id, created_at, updated_at) VALUES
  ('bbbbbbbb-0000-0000-0000-00000000001a','aaaaaaaa-0000-0000-0000-000000000003','MOBILE-1',1,'Release 1.2.0 checklist','Prepare release notes and QA checklist.\n\nLabels: release.','TASK','HIGH','DONE','00000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000001', NOW() - INTERVAL '25 days', NOW() - INTERVAL '20 days'),
  ('bbbbbbbb-0000-0000-0000-00000000001b','aaaaaaaa-0000-0000-0000-000000000003','MOBILE-2',2,'Fix crash on startup (Android)','Null pointer during cold start.\n\nSearch keywords: android crash startup.','BUG','CRITICAL','TODO','00000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000004', NOW() - INTERVAL '6 days', NOW() - INTERVAL '2 days'),
  ('bbbbbbbb-0000-0000-0000-00000000001c','aaaaaaaa-0000-0000-0000-000000000003','MOBILE-3',3,'Implement push notification settings','Allow toggling email/in-app and push preferences (future).','STORY','MEDIUM','IN_PROGRESS','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000004', NOW() - INTERVAL '5 days', NOW() - INTERVAL '1 day'),
  ('bbbbbbbb-0000-0000-0000-00000000001d','aaaaaaaa-0000-0000-0000-000000000003','MOBILE-4',4,'iOS deep link routing review','Verify universal links and fallback routing.\n\nLabels: ios.','TASK','LOW','IN_REVIEW','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '4 days', NOW() - INTERVAL '12 hours'),
  ('bbbbbbbb-0000-0000-0000-00000000001e','aaaaaaaa-0000-0000-0000-000000000003','MOBILE-5',5,'Backlog: offline mode spike','Investigate caching strategy for offline support.','EPIC','MEDIUM','BACKLOG',NULL,'00000000-0000-0000-0000-000000000005', NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day')
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Issue labels (many-to-many)
-- -----------------------------------------------------------------------------
INSERT INTO issue_label (issue_id, label_id) VALUES
  -- ACME
  ('bbbbbbbb-0000-0000-0000-000000000001','11111111-0000-0000-0000-000000000003'), -- infra
  ('bbbbbbbb-0000-0000-0000-000000000002','11111111-0000-0000-0000-000000000004'), -- security
  ('bbbbbbbb-0000-0000-0000-000000000004','11111111-0000-0000-0000-000000000002'), -- frontend
  ('bbbbbbbb-0000-0000-0000-000000000007','11111111-0000-0000-0000-000000000002'), -- frontend
  ('bbbbbbbb-0000-0000-0000-000000000007','11111111-0000-0000-0000-000000000001'), -- backend
  ('bbbbbbbb-0000-0000-0000-000000000008','11111111-0000-0000-0000-000000000005'), -- performance
  ('bbbbbbbb-0000-0000-0000-000000000009','11111111-0000-0000-0000-000000000005'), -- performance
  ('bbbbbbbb-0000-0000-0000-00000000000a','11111111-0000-0000-0000-000000000004'), -- security
  ('bbbbbbbb-0000-0000-0000-00000000000f','11111111-0000-0000-0000-000000000005'), -- performance

  -- WEBDEV
  ('bbbbbbbb-0000-0000-0000-000000000010','11111111-0000-0000-0000-000000000006'), -- ui
  ('bbbbbbbb-0000-0000-0000-000000000010','11111111-0000-0000-0000-000000000007'), -- seo
  ('bbbbbbbb-0000-0000-0000-000000000011','11111111-0000-0000-0000-000000000007'), -- seo
  ('bbbbbbbb-0000-0000-0000-000000000014','11111111-0000-0000-0000-000000000008'), -- analytics
  ('bbbbbbbb-0000-0000-0000-000000000015','11111111-0000-0000-0000-000000000006'), -- ui
  ('bbbbbbbb-0000-0000-0000-000000000016','11111111-0000-0000-0000-000000000008'), -- analytics
  ('bbbbbbbb-0000-0000-0000-000000000017','11111111-0000-0000-0000-000000000007'), -- seo

  -- MOBILE
  ('bbbbbbbb-0000-0000-0000-00000000001a','11111111-0000-0000-0000-00000000000b'), -- release
  ('bbbbbbbb-0000-0000-0000-00000000001b','11111111-0000-0000-0000-000000000009'), -- android
  ('bbbbbbbb-0000-0000-0000-00000000001c','11111111-0000-0000-0000-00000000000b'), -- release
  ('bbbbbbbb-0000-0000-0000-00000000001d','11111111-0000-0000-0000-00000000000a')  -- ios
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- Comments (markdown) on multiple issues
-- -----------------------------------------------------------------------------
INSERT INTO comment (id, issue_id, author_user_id, body_markdown, created_at, updated_at) VALUES
  ('cccccccc-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000003','Implemented `/auth/login` and `/auth/me`.\n\nNext: refresh token flow.', NOW() - INTERVAL '46 days', NOW() - INTERVAL '46 days'),
  ('cccccccc-0000-0000-0000-000000000002','bbbbbbbb-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000004','Search should support:\n- issue key\n- title\n- description\n\nFilters: project, status, assignee.', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'),
  ('cccccccc-0000-0000-0000-000000000003','bbbbbbbb-0000-0000-0000-000000000007','00000000-0000-0000-0000-000000000002','DnD feels good. Need placeholder + highlight target column.', NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day'),
  ('cccccccc-0000-0000-0000-000000000004','bbbbbbbb-0000-0000-0000-000000000007','00000000-0000-0000-0000-000000000003','I can take the accessibility pass for keyboard support after merge.', NOW() - INTERVAL '1 day', NOW() - INTERVAL '20 hours'),
  ('cccccccc-0000-0000-0000-000000000005','bbbbbbbb-0000-0000-0000-00000000000a','00000000-0000-0000-0000-000000000001','Reviewed threat model. Add rate limiting + audit log.', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day'),
  ('cccccccc-0000-0000-0000-000000000006','bbbbbbbb-0000-0000-0000-000000000011','00000000-0000-0000-0000-000000000003','Sitemap fixed; verified in Search Console.', NOW() - INTERVAL '28 days', NOW() - INTERVAL '28 days'),
  ('cccccccc-0000-0000-0000-000000000007','bbbbbbbb-0000-0000-0000-000000000015','00000000-0000-0000-0000-000000000004','Repro steps:\n1. iPhone SE\n2. open menu\n3. scroll\n\nNavbar overlaps content.', NOW() - INTERVAL '6 hours', NOW() - INTERVAL '6 hours'),
  ('cccccccc-0000-0000-0000-000000000008','bbbbbbbb-0000-0000-0000-00000000001b','00000000-0000-0000-0000-000000000005','Crash log indicates `MainActivity` null context. Will patch and add test.', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'),
  ('cccccccc-0000-0000-0000-000000000009','bbbbbbbb-0000-0000-0000-00000000001c','00000000-0000-0000-0000-000000000002','We can reuse server-side `user_settings` for notification prefs.', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day'),
  ('cccccccc-0000-0000-0000-00000000000a','bbbbbbbb-0000-0000-0000-00000000000c','00000000-0000-0000-0000-000000000005','Theme should persist after refresh. If API update fails, revert toggle + toast.', NOW() - INTERVAL '3 hours', NOW() - INTERVAL '3 hours')
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Activity events for issues/comments (timeline)
-- -----------------------------------------------------------------------------
-- Idempotent insert: avoid duplicates on re-run.
INSERT INTO activity_event (project_id, issue_id, actor_user_id, type, summary, metadata, created_at)
SELECT v.project_id, v.issue_id, v.actor_user_id, v.type, v.summary, v.metadata, v.created_at
FROM (
  VALUES
    ('aaaaaaaa-0000-0000-0000-000000000001'::uuid,'bbbbbbbb-0000-0000-0000-000000000002'::uuid,'00000000-0000-0000-0000-000000000002'::uuid,'ISSUE_CREATED','Created issue ACME-2', jsonb_build_object('key','ACME-2','type','STORY'), NOW() - INTERVAL '68 days'),
    ('aaaaaaaa-0000-0000-0000-000000000001'::uuid,'bbbbbbbb-0000-0000-0000-000000000007'::uuid,'00000000-0000-0000-0000-000000000001'::uuid,'ISSUE_STATUS_CHANGED','Moved ACME-7 to In Progress', jsonb_build_object('from','TODO','to','IN_PROGRESS'), NOW() - INTERVAL '12 days'),
    ('aaaaaaaa-0000-0000-0000-000000000001'::uuid,'bbbbbbbb-0000-0000-0000-000000000007'::uuid,'00000000-0000-0000-0000-000000000002'::uuid,'ISSUE_COMMENT_ADDED','Commented on ACME-7', jsonb_build_object('commentId','cccccccc-0000-0000-0000-000000000003'), NOW() - INTERVAL '2 days'),
    ('aaaaaaaa-0000-0000-0000-000000000002'::uuid,'bbbbbbbb-0000-0000-0000-000000000015'::uuid,'00000000-0000-0000-0000-000000000004'::uuid,'ISSUE_CREATED','Created issue WEBDEV-6', jsonb_build_object('key','WEBDEV-6','type','BUG'), NOW() - INTERVAL '5 days'),
    ('aaaaaaaa-0000-0000-0000-000000000003'::uuid,'bbbbbbbb-0000-0000-0000-00000000001b'::uuid,'00000000-0000-0000-0000-000000000004'::uuid,'ISSUE_CREATED','Created issue MOBILE-2', jsonb_build_object('key','MOBILE-2','type','BUG'), NOW() - INTERVAL '6 days'),
    ('aaaaaaaa-0000-0000-0000-000000000003'::uuid,'bbbbbbbb-0000-0000-0000-00000000001b'::uuid,'00000000-0000-0000-0000-000000000005'::uuid,'ISSUE_COMMENT_ADDED','Commented on MOBILE-2', jsonb_build_object('commentId','cccccccc-0000-0000-0000-000000000008'), NOW() - INTERVAL '2 days')
) AS v(project_id, issue_id, actor_user_id, type, summary, metadata, created_at)
WHERE NOT EXISTS (
  SELECT 1
  FROM activity_event ae
  WHERE ae.project_id = v.project_id
    AND ae.issue_id IS NOT DISTINCT FROM v.issue_id
    AND ae.type = v.type
    AND ae.summary = v.summary
);

-- -----------------------------------------------------------------------------
-- Attachments placeholder metadata
-- -----------------------------------------------------------------------------
INSERT INTO attachment (id, issue_id, file_name, mime_type, size_bytes, url, created_at) VALUES
  ('dddddddd-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000003','schema-diagram.png','image/png', 245678, 'https://example.com/files/schema-diagram.png', NOW() - INTERVAL '44 days'),
  ('dddddddd-0000-0000-0000-000000000002','bbbbbbbb-0000-0000-0000-000000000010','landing-mock.png',   'image/png', 512340, 'https://example.com/files/landing-mock.png',    NOW() - INTERVAL '30 days'),
  ('dddddddd-0000-0000-0000-000000000003','bbbbbbbb-0000-0000-0000-00000000001a','release-notes.md',   'text/markdown', 12400, 'https://example.com/files/release-notes.md',    NOW() - INTERVAL '20 days')
ON CONFLICT (id) DO NOTHING;

COMMIT;
