-- GitHub Clone Seed Data
-- Creates test users, repositories, issues, and stars

-- Test users (simplified auth, plain text passwords)
INSERT INTO users (id, username, email, password, name, bio, location) VALUES
  ('00000000-0000-0000-0000-000000000001', 'octocat', 'octocat@github.com', 'github123', 'The Octocat', 'GitHub mascot and test user', 'San Francisco, CA'),
  ('00000000-0000-0000-0000-000000000002', 'torvalds', 'linus@kernel.org', 'linux123', 'Linus Torvalds', 'Creator of Linux and Git', 'Portland, OR'),
  ('00000000-0000-0000-0000-000000000003', 'gvanrossum', 'guido@python.org', 'python123', 'Guido van Rossum', 'Python BDFL (retired)', 'California'),
  ('00000000-0000-0000-0000-000000000004', 'testuser', 'test@example.com', 'test123', 'Test User', 'Demo account for testing', 'New York, NY')
ON CONFLICT (username) DO NOTHING;

-- Sample repositories
INSERT INTO repositories (id, owner_id, name, description, language, stars_count, forks_count, issues_count) VALUES
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Hello-World', 'My first repository on GitHub!', 'JavaScript', 42, 12, 3),
  ('10000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'octocat.github.io', 'Personal website and blog', 'HTML', 18, 3, 0),
  ('10000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000002', 'linux', 'Linux kernel source tree', 'C', 15234, 8921, 247),
  ('10000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000002', 'git', 'Git - the fast distributed version control system', 'C', 9876, 4321, 89),
  ('10000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000003', 'cpython', 'The Python programming language', 'Python', 8745, 3210, 156),
  ('10000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000003', 'peps', 'Python Enhancement Proposals', 'reStructuredText', 2341, 987, 45),
  ('10000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000004', 'test-repo', 'A test repository for demo purposes', 'TypeScript', 5, 1, 2)
ON CONFLICT (owner_id, name) DO NOTHING;

-- Stars (user starred repositories)
INSERT INTO stars (user_id, repository_id) VALUES
  -- octocat stars
  ('00000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000003'), -- linux
  ('00000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000004'), -- git
  ('00000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000005'), -- cpython
  -- torvalds stars
  ('00000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001'), -- Hello-World
  ('00000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000005'), -- cpython
  -- gvanrossum stars
  ('00000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000003'), -- linux
  ('00000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000004'), -- git
  ('00000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001'), -- Hello-World
  -- testuser stars
  ('00000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000003'), -- linux
  ('00000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000005')  -- cpython
ON CONFLICT (user_id, repository_id) DO NOTHING;

-- Sample issues
INSERT INTO issues (id, repository_id, author_id, number, title, body, state, labels) VALUES
  ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000004', 1, 'Add README badges', 'Would be nice to have build status and coverage badges in the README', 'open', ARRAY['enhancement', 'documentation']),
  ('20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 2, 'Fix typo in index.js', 'There is a typo on line 42', 'closed', ARRAY['bug']),
  ('20000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000003', 3, 'Add CI/CD pipeline', 'We should set up automated testing and deployment', 'open', ARRAY['enhancement', 'ci/cd']),
  ('20000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001', 1, 'Memory leak in process scheduler', 'Found a memory leak when running stress tests', 'open', ARRAY['bug', 'critical']),
  ('20000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000004', 2, 'Documentation improvement', 'Add more examples to the kernel documentation', 'open', ARRAY['documentation']),
  ('20000000-0000-0000-0000-000000000006', '10000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000002', 1, 'Performance regression in 3.11', 'Noticed slower performance compared to 3.10', 'closed', ARRAY['bug', 'performance']),
  ('20000000-0000-0000-0000-000000000007', '10000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000004', 1, 'Initial setup', 'Setting up the basic project structure', 'open', ARRAY['setup']),
  ('20000000-0000-0000-0000-000000000008', '10000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000004', 2, 'Add tests', 'Need to add unit tests', 'open', ARRAY['testing', 'enhancement'])
ON CONFLICT DO NOTHING;

-- Sample issue comments
INSERT INTO issue_comments (issue_id, author_id, body) VALUES
  ('20000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Good idea! I can help with that.'),
  ('20000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'Fixed in commit abc123'),
  ('20000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000002', 'GitHub Actions would be perfect for this'),
  ('20000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000002', 'Thanks for reporting! Looking into it now.'),
  ('20000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000003', 'This has been fixed in the latest release')
ON CONFLICT DO NOTHING;
