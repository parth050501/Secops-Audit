#!/usr/bin/env bash
#
# Code Core Systems — Database Restore
#
# Restores the PostgreSQL database from a backup file made by backup.sh.
#
# USAGE
#   ./restore.sh /home/ubuntu/backups/codecore-secops-20260629-020000.sql.gz
#
# WARNING: this OVERWRITES the current database contents with the backup.
# It will ask for confirmation first.
#
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/ubuntu/SecOps--Audit}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
  echo "Usage: ./restore.sh <path-to-backup.sql.gz>" >&2
  echo "Available backups:" >&2
  ls -1t /home/ubuntu/backups/codecore-*.sql.gz 2>/dev/null | head >&2 || echo "  (none found)" >&2
  exit 1
fi

cd "$PROJECT_DIR"
POSTGRES_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2-)"
POSTGRES_DB="$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2-)"
POSTGRES_USER="${POSTGRES_USER:-secops}"
POSTGRES_DB="${POSTGRES_DB:-secops}"

echo "About to RESTORE '$BACKUP_FILE'"
echo "into database '$POSTGRES_DB' (user '$POSTGRES_USER')."
echo "This OVERWRITES current data. Type 'yes' to continue:"
read -r CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."; exit 1
fi

echo "[restore] restoring…"
gunzip -c "$BACKUP_FILE" | $COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
echo "[restore] done. You may want to restart the backend:"
echo "  $COMPOSE restart backend"
