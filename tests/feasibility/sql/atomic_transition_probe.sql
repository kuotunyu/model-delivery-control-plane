CREATE TABLE IF NOT EXISTS environments (
    environment_id text PRIMARY KEY,
    active_release_id text,
    current_revision integer NOT NULL,
    policy_digest text NOT NULL
);

CREATE TABLE IF NOT EXISTS releases (
    release_id text PRIMARY KEY,
    environment_id text NOT NULL REFERENCES environments(environment_id),
    state text NOT NULL CHECK (state = 'PRODUCTION'),
    revision integer NOT NULL CHECK (revision > 0)
);

CREATE TABLE IF NOT EXISTS route_plans (
    environment_id text NOT NULL REFERENCES environments(environment_id),
    revision integer NOT NULL CHECK (revision > 0),
    payload jsonb NOT NULL,
    payload_digest text NOT NULL,
    signature bytea NOT NULL,
    PRIMARY KEY (environment_id, revision)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id text PRIMARY KEY,
    environment_id text NOT NULL REFERENCES environments(environment_id),
    revision integer NOT NULL CHECK (revision > 0),
    payload_digest text NOT NULL
);
