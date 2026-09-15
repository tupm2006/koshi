#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KOSHI_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

BACKUP_DIR="${KOSHI_ROOT}/data/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "$BACKUP_DIR"

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^koshi-backend$"; then
    docker exec koshi-backend python3 -c "import sqlite3; src=sqlite3.connect('/app/data/koshi.db'); dst=sqlite3.connect('/tmp/backup_${TIMESTAMP}.db'); src.backup(dst); dst.close(); src.close()"
    docker cp "koshi-backend:/tmp/backup_${TIMESTAMP}.db" "${BACKUP_DIR}/koshi_${TIMESTAMP}.db"
    docker exec koshi-backend rm -f "/tmp/backup_${TIMESTAMP}.db"
    echo "[✓] Online hot backup created successfully at: ${BACKUP_DIR}/koshi_${TIMESTAMP}.db"
elif [ -f "${KOSHI_ROOT}/source_code/backend/app/data/koshi.db" ]; then
    python3 -c "import sqlite3; src=sqlite3.connect('${KOSHI_ROOT}/source_code/backend/app/data/koshi.db'); dst=sqlite3.connect('${BACKUP_DIR}/koshi_${TIMESTAMP}.db'); src.backup(dst); dst.close(); src.close()"
    echo "[✓] Online hot backup created successfully at: ${BACKUP_DIR}/koshi_${TIMESTAMP}.db"
elif [ -f "${KOSHI_ROOT}/data/koshi.db" ]; then
    python3 -c "import sqlite3; src=sqlite3.connect('${KOSHI_ROOT}/data/koshi.db'); dst=sqlite3.connect('${BACKUP_DIR}/koshi_${TIMESTAMP}.db'); src.backup(dst); dst.close(); src.close()"
    echo "[✓] Online hot backup created successfully at: ${BACKUP_DIR}/koshi_${TIMESTAMP}.db"
else
    echo "[!] Database file not found" >&2
    exit 1
fi

# Retain backups from the last 7 days
find "$BACKUP_DIR" -type f -name "koshi_*.db" -mtime +7 -delete || true
