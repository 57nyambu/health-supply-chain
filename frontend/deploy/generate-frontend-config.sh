#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  source .env
fi

: "${API_BASE_URL:=http://localhost:8000/api/v1}"

cat > assets/js/config.js <<EOF
window.AFYASYNC_CONFIG = {
  API_BASE_URL: "${API_BASE_URL}",
};
EOF

echo "Generated assets/js/config.js with API_BASE_URL=${API_BASE_URL}"
