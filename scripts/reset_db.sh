#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_NAME="${1:-stremet_tracker}"
SOCKET_DIR="$ROOT_DIR/.pgsocket"
PORT="${STREMET_PGPORT:-5440}"

dropdb --if-exists -h "$SOCKET_DIR" -p "$PORT" -U postgres "$DB_NAME"
createdb -h "$SOCKET_DIR" -p "$PORT" -U postgres "$DB_NAME"
psql -h "$SOCKET_DIR" -p "$PORT" -U postgres -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$ROOT_DIR/db/001_init.sql"
psql -h "$SOCKET_DIR" -p "$PORT" -U postgres -d "$DB_NAME" -v ON_ERROR_STOP=1 -f "$ROOT_DIR/db/002_seed_reference_data.sql"

printf 'Database reset and migrated: %s\n' "$DB_NAME"
