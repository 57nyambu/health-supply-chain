#!/usr/bin/env bash
# Dev-only PostgreSQL cluster for machines without Docker: trust auth, 127.0.0.1 only.
# Usage: scripts/dev/local-postgres.sh start|stop|status
# Then: export DATABASE_URL=postgres://postgres@127.0.0.1:${PGPORT:-5433}/afyasync
set -euo pipefail
DIR=${AFYASYNC_PG_DIR:-$HOME/.afyasync/pg}
PORT=${PGPORT:-5433}
LOG=${DIR}.log

case "${1:-status}" in
  start)
    if [ ! -f "$DIR/PG_VERSION" ]; then
      mkdir -p "$(dirname "$DIR")"
      initdb -D "$DIR" -U postgres -A trust -E UTF8 --locale=C >/dev/null
    fi
    pg_ctl -D "$DIR" -o "-p $PORT -c listen_addresses=127.0.0.1" -l "$LOG" -w start
    psql -h 127.0.0.1 -p "$PORT" -U postgres -tc "select 1 from pg_database where datname='afyasync'" | grep -q 1 \
      || psql -h 127.0.0.1 -p "$PORT" -U postgres -c "create database afyasync" >/dev/null
    echo "DATABASE_URL=postgres://postgres@127.0.0.1:$PORT/afyasync"
    ;;
  stop) pg_ctl -D "$DIR" -m fast stop ;;
  status) pg_ctl -D "$DIR" status ;;
  *) echo "usage: $0 start|stop|status" >&2; exit 2 ;;
esac
