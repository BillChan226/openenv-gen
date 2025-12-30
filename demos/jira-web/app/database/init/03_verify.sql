-- 03_verify.sql
-- Optional smoke-test queries for seeded data.
-- Run after 01_schema.sql + 02_seed.sql.

-- 1) Counts
SELECT 'users' AS entity, COUNT(*) AS count FROM app_user;
SELECT 'projects' AS entity, COUNT(*) AS count FROM project;
SELECT 'issues' AS entity, COUNT(*) AS count FROM issue;
SELECT 'comments' AS entity, COUNT(*) AS count FROM comment;
SELECT 'labels' AS entity, COUNT(*) AS count FROM label;

-- 2) Project issue counts
SELECT p.key AS project_key, p.name, COUNT(i.id) AS issue_count
FROM project p
LEFT JOIN issue i ON i.project_id = p.id
GROUP BY p.key, p.name
ORDER BY p.key;

-- 3) Status distributions per project
SELECT p.key AS project_key, i.status, COUNT(*) AS count
FROM issue i
JOIN project p ON p.id = i.project_id
GROUP BY p.key, i.status
ORDER BY p.key, i.status;

-- 4) Assignee workload per project
SELECT p.key AS project_key, u.name AS assignee, COUNT(i.id) AS assigned_count
FROM issue i
JOIN project p ON p.id = i.project_id
LEFT JOIN app_user u ON u.id = i.assignee_user_id
GROUP BY p.key, u.name
ORDER BY p.key, assigned_count DESC, assignee;

-- 5) Text search examples
-- Search by key
SELECT key, title, status FROM issue WHERE key ILIKE '%ACME-7%';

-- Search by title/description (full-text)
SELECT key, title
FROM issue
WHERE search_tsv @@ plainto_tsquery('english', 'performance')
ORDER BY created_at DESC
LIMIT 10;

-- 6) Ensure all required statuses exist
SELECT status, COUNT(*) FROM issue GROUP BY status ORDER BY status;
