#!/usr/bin/env bash
# Writes ./.env with a per-machine JWT_SECRET for the local Docker stack.
#
# docker compose reads ./.env automatically, so this is all the dev stack needs.
# The file is gitignored. It is regenerated only if missing — rerunning will not
# silently sign everyone out.
set -euo pipefail
cd "$(dirname "$0")/.."

# Four secrets, all per-machine and all generated here:
#   JWT_SECRET       dev stack signing key
#   PROD_JWT_SECRET  local production signing key — separate on purpose, so a
#                    session minted against seeded demo data cannot authenticate
#                    against the real instance
#   MYSQL_PASSWORD / MYSQL_ROOT_PASSWORD  for the local production database
wrote=0
for name in JWT_SECRET PROD_JWT_SECRET MYSQL_PASSWORD MYSQL_ROOT_PASSWORD; do
  if [ -f .env ] && grep -q "^${name}=.\+" .env; then
    echo "  ${name}: already set, leaving it alone"
  else
    printf '%s=%s\n' "$name" "$(openssl rand -hex 32)" >> .env
    echo "  ${name}: generated"
    wrote=1
  fi
done

if [ "$wrote" = "0" ]; then
  echo
  echo "Nothing to do. To rotate one deliberately, delete its line from .env and rerun."
  exit 0
fi

echo
echo "Written to ./.env (gitignored — never commit it)."
echo "  dev stack:   docker compose -f docker-compose.dev.yml up -d --build"
echo "  local prod:  ./scripts/local-prod.sh up"
