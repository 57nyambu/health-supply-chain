#!/usr/bin/env bash
set -euo pipefail

SKIP_SEED=0
if [[ "${1:-}" == "--skip-seed" ]]; then
  SKIP_SEED=1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "== AfyaSync backend setup (Linux) =="
echo "Repo: $REPO_ROOT"

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate

if [[ "$SKIP_SEED" -eq 0 ]]; then
  python manage.py seed_facility_demo_data
fi

python manage.py check

echo "Backend setup complete."
echo "Run: source .venv/bin/activate && python manage.py runserver"
