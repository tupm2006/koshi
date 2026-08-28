#!/usr/bin/env bash
# Writes ./.env with a per-machine JWT_SECRET for the local Docker stack.
#
# docker compose reads ./.env automatically, so this is all the dev stack needs.
# The file is gitignored. It is regenerated only if missing — rerunning will not
# silently sign everyone out.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ] && grep -q '^JWT_SECRET=.\+' .env; then
  echo ".env already has a JWT_SECRET; leaving it alone."
  echo "To rotate deliberately: remove the JWT_SECRET line and rerun."
  exit 0
fi

printf 'JWT_SECRET=%s\n' "$(openssl rand -hex 32)" >> .env
echo "Wrote a new JWT_SECRET to ./.env  (gitignored — never commit it)"
echo "Now: docker compose -f docker-compose.dev.yml up -d --build"
