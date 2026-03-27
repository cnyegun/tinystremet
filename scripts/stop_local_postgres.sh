#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$ROOT_DIR/.pgdata"

if [ ! -d "$DATA_DIR" ]; then
  printf 'No local Postgres data directory found at %s\n' "$DATA_DIR"
  exit 0
fi

pg_ctl -D "$DATA_DIR" -m fast stop

printf 'Postgres stopped\n'
