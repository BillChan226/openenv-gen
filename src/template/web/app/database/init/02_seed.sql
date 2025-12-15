-- Seed data for {{ENV_NAME}}
-- This file populates initial data for reproducible environment states

-- Admin user (password: admin123)
INSERT INTO "Users" (id, name, email, password, role) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Admin User', 'admin@example.com', '$2a$10$rQEY7xBbPmYt8q.KqQzQxeOQZMzGqB7dK1ZC8qQF3Y5F8E8E8E8E8', 'admin')
ON CONFLICT (email) DO NOTHING;

-- Test user (password: user123)
INSERT INTO "Users" (id, name, email, password, role) VALUES
    ('00000000-0000-0000-0000-000000000002', 'Test User', 'user@example.com', '$2a$10$rQEY7xBbPmYt8q.KqQzQxeOQZMzGqB7dK1ZC8qQF3Y5F8E8E8E8E8', 'user')
ON CONFLICT (email) DO NOTHING;

-- {{GENERATED_SEED_DATA}}
