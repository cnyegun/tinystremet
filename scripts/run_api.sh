#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres@/stremet_tracker?host=$ROOT_DIR/.pgsocket&port=${STREMET_PGPORT:-5440}}"

exec uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
