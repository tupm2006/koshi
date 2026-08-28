#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KOSHI_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

DB_PATH="${KOSHI_ROOT}/source_code/backend/app/data/koshi.db"
BACKUP_DIR="${KOSHI_ROOT}/data/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "$BACKUP_DIR"

if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" ".backup '${BACKUP_DIR}/koshi_${TIMESTAMP}.db'"
    echo "[✓] Online hot backup created successfully at: ${BACKUP_DIR}/koshi_${TIMESTAMP}.db"
    
    # Retain backups from the last 7 days
    find "$BACKUP_DIR" -type f -name "koshi_*.db" -mtime +7 -delete || true
else
    echo "[!] Database file not found at: $DB_PATH" >&2
    exit 1
fi
