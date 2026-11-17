CREATE TABLE IF NOT EXISTS runtime_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  mode TEXT NOT NULL CHECK (mode IN ('work', 'rest', 'paused')),
  work_started_at TEXT,
  work_deadline TEXT,
  rest_until TEXT,
  lease_owner TEXT,
  lease_expires_at TEXT,
  last_checkpoint TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_jobs (
  job_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  payload_ciphertext TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'leased', 'completed', 'failed', 'quarantined')),
  attempts INTEGER NOT NULL DEFAULT 0,
  available_at TEXT NOT NULL,
  lease_owner TEXT,
  lease_expires_at TEXT,
  checkpoint_ciphertext TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runtime_jobs_due
  ON runtime_jobs(status, available_at, lease_expires_at);

CREATE TABLE IF NOT EXISTS runtime_audit (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  subject_hash TEXT,
  details_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runtime_audit_created
  ON runtime_audit(created_at);

CREATE TABLE IF NOT EXISTS backup_manifests (
  backup_id TEXT PRIMARY KEY,
  object_key TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  byte_length INTEGER NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending', 'verified', 'failed')),
  created_at TEXT NOT NULL,
  verified_at TEXT
);

INSERT OR IGNORE INTO runtime_state(id, mode, work_started_at, work_deadline, updated_at)
VALUES (1, 'work', CURRENT_TIMESTAMP, datetime('now', '+60 minutes'), CURRENT_TIMESTAMP);
