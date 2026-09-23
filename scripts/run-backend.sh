#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

pick_python() {
  local candidate
  for candidate in python3.11 python3.12 python3.13 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      "$candidate" - <<'PY' >/dev/null 2>&1 || continue
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
      printf '%s' "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(pick_python || true)"
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "No supported Python found. Install Python 3.11+ and retry."
  exit 1
fi

cd "$BACKEND_DIR"

recreate_venv=0
if [[ ! -d ".venv" ]]; then
  recreate_venv=1
elif [[ ! -x ".venv/bin/python" ]]; then
  recreate_venv=1
elif ! .venv/bin/python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1; then
  recreate_venv=1
elif ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  recreate_venv=1
fi

if [[ "$recreate_venv" -eq 1 ]]; then
  rm -rf .venv
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if ! python -c "import fastapi, sqlmodel" >/dev/null 2>&1; then
  pip install -r requirements.txt
fi

if [[ -z "${DATABASE_URL:-}" || "${DATABASE_URL}" == "postgresql+psycopg://aqualens:aqualens@localhost:5432/aqualens" ]]; then
  export DATABASE_URL="sqlite:///./aqualens.db"
fi

resolved_google_key="${GOOGLE_API_KEY:-}"
if [[ -z "$resolved_google_key" && -f "$ROOT_DIR/.env" ]]; then
  resolved_google_key="$(
    sed -nE 's/^[[:space:]]*GOOGLE_API_KEY[[:space:]]*=[[:space:]]*(.*)[[:space:]]*$/\1/p' "$ROOT_DIR/.env" | tail -n 1
  )"
  # Trim optional matching single/double quotes around dotenv values.
  if [[ "$resolved_google_key" == \"*\" && "$resolved_google_key" == *\" ]]; then
    resolved_google_key="${resolved_google_key:1:${#resolved_google_key}-2}"
  elif [[ "$resolved_google_key" == \'*\' && "$resolved_google_key" == *\' ]]; then
    resolved_google_key="${resolved_google_key:1:${#resolved_google_key}-2}"
  fi
fi

if [[ "$resolved_google_key" == "your-gemini-api-key-here" ]]; then
  resolved_google_key=""
fi

if [[ -z "$resolved_google_key" && "${AQUALENS_FAKE_GEMINI:-0}" != "1" ]]; then
  echo "Warning: GOOGLE_API_KEY is not set and AQUALENS_FAKE_GEMINI is off."
  echo "Session reasoning calls will fail until a real Gemini key is provided."
fi

# Avoid .pyc writes inside site-packages causing WatchFiles reload loops.
export PYTHONDONTWRITEBYTECODE=1

alembic upgrade head
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --reload \
  --reload-dir app \
  --reload-exclude ".venv/*" \
  --reload-exclude "*/site-packages/*" \
  --reload-exclude "__pycache__/*"
