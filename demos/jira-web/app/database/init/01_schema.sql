-- 01_schema.sql
-- Jira Software Clone - PostgreSQL schema
--
-- Notes:
-- * Uses UUID primary keys
-- * Uses TIMESTAMPTZ timestamps
-- * Includes updated_at triggers
-- * Includes indexes for filtering/sorting/search

BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------------------------------
-- Utility: updated_at trigger
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Users
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_user (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(100) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'member' CHECK (role IN ('admin','member','viewer')),
  avatar_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_user_email ON app_user (email);

DROP TRIGGER IF EXISTS trg_app_user_updated_at ON app_user;
CREATE TRIGGER trg_app_user_updated_at
BEFORE UPDATE ON app_user
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- -----------------------------------------------------------------------------
-- User settings
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_settings (
  user_id UUID PRIMARY KEY REFERENCES app_user(id) ON DELETE CASCADE,
  theme VARCHAR(10) NOT NULL DEFAULT 'light' CHECK (theme IN ('light','dark')),
  notifications_email BOOLEAN NOT NULL DEFAULT TRUE,
  notifications_in_app BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_user_settings_updated_at ON user_settings;
CREATE TRIGGER trg_user_settings_updated_at
BEFORE UPDATE ON user_settings
FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- -----------------------------------------------------------------------------
-- Auth: revoked JWTs (denylist)
-- -----------------------------------------------------------------------------
-- Stateless JWTs cannot be invalidated without a revocation strategy.
-- We store revoked token identifiers (jti) until their natural expiration.
CREATE TABLE IF NOT EXISTS revoked_jwt (
  jti UUID PRIMARY KEY,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_revoked_jwt_expires_at ON revoked_jwt (expires_at);

-- -----------------------------------------------------------------------------
-- Projects
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  key VARCHAR(10) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  lead_user_id UUID REFERENCES app_user(id) ON DELETE SET NULL,
  is_archived BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT project_key_uppercase CHECK (key = UPPER(key))
);

CREATE INDEX IF NOT EXISTS idx_project_key ON project (key);
CREATE INDEX IF NOT EXISTS idx_project_is_archived ON project (is_archived);

DROP TRIGGER IF EXISTS trg_project_updated_at ON project;
CREATE TRIGGER trg_project_updated_at
BEFORE UPDATE ON project
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- -----------------------------------------------------------------------------
-- Labels (project-scoped)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS label (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  name VARCHAR(50) NOT NULL,
  color VARCHAR(7) NOT NULL DEFAULT '#6B778C' CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT label_unique_per_project UNIQUE (project_id, name)
);

CREATE INDEX IF NOT EXISTS idx_label_project_id ON label (project_id);

-- -----------------------------------------------------------------------------
-- Issues
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS issue (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  key VARCHAR(32) NOT NULL UNIQUE,
  seq INT NOT NULL,
  title VARCHAR(500) NOT NULL,
  description TEXT,
  type VARCHAR(20) NOT NULL CHECK (type IN ('BUG','TASK','STORY','EPIC')),
  priority VARCHAR(20) NOT NULL CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  status VARCHAR(20) NOT NULL CHECK (status IN ('BACKLOG','TODO','IN_PROGRESS','IN_REVIEW','DONE')),
  assignee_user_id UUID REFERENCES app_user(id) ON DELETE SET NULL,
  reporter_user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT issue_seq_unique_per_project UNIQUE (project_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_issue_project_id ON issue (project_id);
CREATE INDEX IF NOT EXISTS idx_issue_project_status ON issue (project_id, status);
CREATE INDEX IF NOT EXISTS idx_issue_assignee_user_id ON issue (assignee_user_id);
CREATE INDEX IF NOT EXISTS idx_issue_reporter_user_id ON issue (reporter_user_id);
CREATE INDEX IF NOT EXISTS idx_issue_created_at ON issue (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_issue_key ON issue (key);

-- Full-text search index (title + description)
ALTER TABLE issue
  ADD COLUMN IF NOT EXISTS search_tsv tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title,'')), 'A') ||
    setweight(to_tsvector('english', coalesce(description,'')), 'B')
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_issue_search_tsv ON issue USING GIN (search_tsv);

DROP TRIGGER IF EXISTS trg_issue_updated_at ON issue;
CREATE TRIGGER trg_issue_updated_at
BEFORE UPDATE ON issue
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- -----------------------------------------------------------------------------
-- Issue <-> Label join
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS issue_label (
  issue_id UUID NOT NULL REFERENCES issue(id) ON DELETE CASCADE,
  label_id UUID NOT NULL REFERENCES label(id) ON DELETE CASCADE,
  PRIMARY KEY (issue_id, label_id)
);

CREATE INDEX IF NOT EXISTS idx_issue_label_label_id ON issue_label (label_id);

-- -----------------------------------------------------------------------------
-- Comments
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS comment (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  issue_id UUID NOT NULL REFERENCES issue(id) ON DELETE CASCADE,
  author_user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
  body_markdown TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comment_issue_id_created_at ON comment (issue_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comment_author_user_id ON comment (author_user_id);

DROP TRIGGER IF EXISTS trg_comment_updated_at ON comment;
CREATE TRIGGER trg_comment_updated_at
BEFORE UPDATE ON comment
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- -----------------------------------------------------------------------------
-- Activity log (append-only)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_event (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  issue_id UUID REFERENCES issue(id) ON DELETE CASCADE,
  actor_user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
  type VARCHAR(50) NOT NULL CHECK (type IN (
    'ISSUE_CREATED',
    'ISSUE_UPDATED',
    'ISSUE_STATUS_CHANGED',
    'ISSUE_COMMENT_ADDED',
    'ISSUE_COMMENT_UPDATED',
    'ISSUE_COMMENT_DELETED',
    'PROJECT_CREATED'
  )),
  summary TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_project_id_created_at ON activity_event (project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_issue_id_created_at ON activity_event (issue_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_actor_user_id ON activity_event (actor_user_id);

-- -----------------------------------------------------------------------------
-- Attachments (placeholder metadata)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attachment (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  issue_id UUID NOT NULL REFERENCES issue(id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes INT NOT NULL CHECK (size_bytes >= 0),
  url TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_attachment_issue_id_created_at ON attachment (issue_id, created_at DESC);

COMMIT;
