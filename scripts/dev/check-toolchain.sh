#!/usr/bin/env bash
# Report the toolchain against IMPLEMENTATION §4. Missing required tools fail; version drift warns.
set -u
status=0

version_of() { "$@" 2>/dev/null | head -n1 | grep -oE '[0-9]+(\.[0-9]+)+' | head -n1; }

check() { # name, minimum major, command...
  local name=$1 want=$2; shift 2
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "MISSING  $name (need $want+)"; status=1; return
  fi
  local have; have=$(version_of "$@")
  local major=${have%%.*}
  if [ -n "$major" ] && [ "$major" -lt "${want%%.*}" ] 2>/dev/null; then
    echo "OLD      $name $have (need $want+)"; status=1
  else
    echo "ok       $name $have"
  fi
}

check uv 0 uv --version
check node 22 node --version
check pnpm 10 pnpm --version
check git 2 git --version
check gitleaks 8 gitleaks version
if command -v docker >/dev/null 2>&1; then
  check docker 24 docker --version
  docker compose version >/dev/null 2>&1 && echo "ok       docker compose" || { echo "MISSING  docker compose v2"; status=1; }
else
  echo "WARN     docker not found: compose services unavailable; use scripts/dev/local-postgres.sh and a local Redis"
fi
node_major=$(version_of node --version); node_major=${node_major%%.*}
[ -n "$node_major" ] && [ "$node_major" -lt 24 ] && echo "WARN     Node $node_major: Node 24 LTS is the target (IMPLEMENTATION §4)"
exit $status
