#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  source .env
fi

: "${API_BASE_URL:=/api/v1}"
: "${DEMO_ADMIN_EMAIL:=admin@afyasync.dima.co.ke}"
: "${DEMO_FACILITY_EMAIL:=facility@afyasync.dima.co.ke}"
: "${DEMO_REPORTER_EMAIL:=reporter@afyasync.dima.co.ke}"

cat > assets/js/config.js <<EOF
window.AFYASYNC_CONFIG = {
  API_BASE_URL: "${API_BASE_URL}",
  DEMO_LOGINS: [
    { label: "Admin", email: "${DEMO_ADMIN_EMAIL}" },
    { label: "Facility", email: "${DEMO_FACILITY_EMAIL}" },
    { label: "Reporter", email: "${DEMO_REPORTER_EMAIL}" },
  ],
};
EOF

echo "Generated assets/js/config.js with API_BASE_URL=${API_BASE_URL} and demo logins"
