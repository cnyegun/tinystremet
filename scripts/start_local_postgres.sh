#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$ROOT_DIR/.pgdata"
SOCKET_DIR="$ROOT_DIR/.pgsocket"
PID_DIR="$ROOT_DIR/.pids"
LOG_FILE="$ROOT_DIR/postgres.log"
PORT="${STREMET_PGPORT:-5440}"

mkdir -p "$SOCKET_DIR" "$PID_DIR"

if [ ! -d "$DATA_DIR" ]; then
  initdb -D "$DATA_DIR" -A trust -U postgres >/dev/null
fi

pg_ctl \
  -D "$DATA_DIR" \
  -l "$LOG_FILE" \
  -o "-F -k $SOCKET_DIR -p $PORT" \
  -w start

printf 'Postgres started\n'
printf '  socket: %s\n' "$SOCKET_DIR"
printf '  port: %s\n' "$PORT"
printf '  log: %s\n' "$LOG_FILE"
