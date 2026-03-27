BEGIN;

CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    customer_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE jobs (
    id BIGSERIAL PRIMARY KEY,
    job_code TEXT NOT NULL UNIQUE,
    customer_id BIGINT REFERENCES customers(id) ON DELETE SET NULL,
    drawing_code TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE statuses (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    sort_order INTEGER NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE locations (
    id BIGSERIAL PRIMARY KEY,
    location_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    location_type TEXT NOT NULL,
    parent_location_id BIGINT REFERENCES locations(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT locations_no_self_parent CHECK (id IS NULL OR parent_location_id IS NULL OR id <> parent_location_id)
);

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE workstations (
    id BIGSERIAL PRIMARY KEY,
    workstation_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    location_id BIGINT REFERENCES locations(id) ON DELETE SET NULL,
    process_step TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE parts (
    id BIGSERIAL PRIMARY KEY,
    part_code TEXT NOT NULL UNIQUE,
    job_id BIGINT REFERENCES jobs(id) ON DELETE SET NULL,
    status_id BIGINT NOT NULL REFERENCES statuses(id),
    current_location_id BIGINT REFERENCES locations(id) ON DELETE SET NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT parts_quantity_positive CHECK (quantity > 0)
);

CREATE TABLE assemblies (
    id BIGSERIAL PRIMARY KEY,
    assembly_code TEXT NOT NULL UNIQUE,
    job_id BIGINT REFERENCES jobs(id) ON DELETE SET NULL,
    status_id BIGINT NOT NULL REFERENCES statuses(id),
    current_location_id BIGINT REFERENCES locations(id) ON DELETE SET NULL,
    notes TEXT,
    created_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE assembly_parts (
    id BIGSERIAL PRIMARY KEY,
    assembly_id BIGINT NOT NULL REFERENCES assemblies(id) ON DELETE CASCADE,
    part_id BIGINT NOT NULL REFERENCES parts(id) ON DELETE RESTRICT,
    qty_used INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT assembly_parts_unique UNIQUE (assembly_id, part_id),
    CONSTRAINT assembly_parts_qty_positive CHECK (qty_used > 0)
);

CREATE TABLE part_events (
    id BIGSERIAL PRIMARY KEY,
    part_id BIGINT NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    from_status_id BIGINT REFERENCES statuses(id) ON DELETE SET NULL,
    to_status_id BIGINT REFERENCES statuses(id) ON DELETE SET NULL,
    from_location_id BIGINT REFERENCES locations(id) ON DELETE SET NULL,
    to_location_id BIGINT REFERENCES locations(id) ON DELETE SET NULL,
    workstation_id BIGINT REFERENCES workstations(id) ON DELETE SET NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_jobs_customer_id ON jobs(customer_id);
CREATE INDEX idx_locations_parent_location_id ON locations(parent_location_id);
CREATE INDEX idx_workstations_location_id ON workstations(location_id);
CREATE INDEX idx_parts_job_id ON parts(job_id);
CREATE INDEX idx_parts_status_id ON parts(status_id);
CREATE INDEX idx_parts_current_location_id ON parts(current_location_id);
CREATE INDEX idx_assemblies_job_id ON assemblies(job_id);
CREATE INDEX idx_assemblies_status_id ON assemblies(status_id);
CREATE INDEX idx_assemblies_current_location_id ON assemblies(current_location_id);
CREATE INDEX idx_part_events_part_id ON part_events(part_id);
CREATE INDEX idx_part_events_event_time ON part_events(event_time DESC);
CREATE INDEX idx_part_events_to_status_id ON part_events(to_status_id);
CREATE INDEX idx_part_events_to_location_id ON part_events(to_location_id);

COMMIT;
