# Database Setup

Use PostgreSQL for the Stremet tracker.

Why:
- strong relational fit for parts, assemblies, locations, and event history
- reliable uniqueness for per-part codes
- good auditability and reporting as the system grows
- clean path to future ERP integration

Files:
- `001_init.sql` creates the core schema
- `002_seed_reference_data.sql` inserts statuses and a sample facility layout

Apply locally:

```bash
createdb stremet_tracker
psql -d stremet_tracker -f db/001_init.sql
psql -d stremet_tracker -f db/002_seed_reference_data.sql
```

Or use the local helper scripts:

```bash
chmod +x scripts/*.sh
./scripts/start_local_postgres.sh
./scripts/reset_db.sh
```

This starts a repo-local PostgreSQL instance using:
- data dir: `.pgdata`
- socket dir: `.pgsocket`
- default port: `5440`

Stop it with:

```bash
./scripts/stop_local_postgres.sh
```

Core modeling decisions:
- `parts` is the tracked per-piece unit
- `assemblies` represents a product built from one or more parts
- `assembly_parts` links many parts into one assembly
- `part_events` stores traceability history
- `locations` supports a simple parent-child facility hierarchy

This schema is intentionally scoped for the MVP and does not try to mirror the full ERP.
