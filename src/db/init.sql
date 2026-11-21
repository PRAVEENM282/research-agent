CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt TEXT NOT NULL,
  status VARCHAR(50) NOT NULL,
  result TEXT NULL,
  agent_logs JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_tasks_created_at_desc ON tasks (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks (status);
CREATE OR REPLACE FUNCTION handoff_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS tasks_updated_at_trigger ON tasks;
CREATE TRIGGER tasks_updated_at_trigger BEFORE UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION handoff_set_updated_at();
CREATE TABLE IF NOT EXISTS task_dispatch_outbox (
  id UUID PRIMARY KEY,
  task_id UUID NOT NULL,
  prompt TEXT NOT NULL,
  kind VARCHAR(20) NOT NULL DEFAULT 'run',
  approved BOOLEAN NULL,
  feedback TEXT NULL,
  delivered_at TIMESTAMPTZ NULL,
  claimed_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_task_dispatch_pending ON task_dispatch_outbox (created_at) WHERE delivered_at IS NULL;
