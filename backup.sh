#!/usr/bin/env bash
#
# Code Core Systems — Database Backup
#
# Backs up the PostgreSQL database to a local file, and optionally uploads it to
# S3 (so a server loss doesn't lose the backups too). Run it manually before any
# risky change, and on a daily schedule via cron.
#
# USAGE
#   ./backup.sh                 # local backup only
#   ./backup.sh --s3            # local backup + upload to S3 (needs S3_BUCKET set)
#
# SETUP (one time)
#   1. Put this script in ~/SecOps--Audit/ and make it executable:
#        chmod +x backup.sh
#   2. (For S3) install AWS CLI and configure credentials, then set the bucket:
#        sudo apt-get install -y awscli
#        aws configure          # use an IAM key with write access to your bucket
#        export S3_BUCKET=s3://your-backup-bucket/codecore   # or set in the script below
#
# RESTORE (see restore.sh)
#
set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────
PROJECT_DIR="${PROJECT_DIR:-/home/ubuntu/SecOps--Audit}"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
BACKUP_DIR="${BACKUP_DIR:-/home/ubuntu/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-14}"          # delete local backups older than this
S3_BUCKET="${S3_BUCKET:-}"                 # e.g. s3://my-bucket/codecore (empty = no S3)

# Read DB creds from the project's .env (never hardcode them)
cd "$PROJECT_DIR"
POSTGRES_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2-)"
POSTGRES_DB="$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2-)"
POSTGRES_USER="${POSTGRES_USER:-secops}"
POSTGRES_DB="${POSTGRES_DB:-secops}"

mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/codecore-${POSTGRES_DB}-${TS}.sql.gz"

echo "[backup] dumping database '$POSTGRES_DB' as user '$POSTGRES_USER'…"
# -T = no TTY (needed in cron). pg_dump runs inside the postgres container.
$COMPOSE exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$OUT"

SIZE="$(du -h "$OUT" | cut -f1)"
echo "[backup] wrote $OUT ($SIZE)"

# ── Optional S3 upload ──────────────────────────────────────────────
if [ "${1:-}" = "--s3" ] || [ -n "$S3_BUCKET" ]; then
  if [ -z "$S3_BUCKET" ]; then
    echo "[backup] --s3 given but S3_BUCKET is not set; skipping upload." >&2
  elif ! command -v aws >/dev/null 2>&1; then
    echo "[backup] aws CLI not installed; skipping S3 upload. (sudo apt-get install awscli)" >&2
  else
    echo "[backup] uploading to $S3_BUCKET/ …"
    aws s3 cp "$OUT" "$S3_BUCKET/$(basename "$OUT")"
    echo "[backup] uploaded."
  fi
fi

# ── Prune old local backups ─────────────────────────────────────────
find "$BACKUP_DIR" -name "codecore-*.sql.gz" -type f -mtime +"$RETAIN_DAYS" -delete 2>/dev/null || true
echo "[backup] done. Local backups kept for $RETAIN_DAYS days in $BACKUP_DIR."
