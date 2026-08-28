#!/usr/bin/env bash
#
# Manage the local production instance (docker-compose.prod-local.yml).
#
#   ./scripts/local-prod.sh up       build, back up, migrate, start, verify
#   ./scripts/local-prod.sh down     stop (keeps the database)
#   ./scripts/local-prod.sh reset    stop and DESTROY the database
#   ./scripts/local-prod.sh logs
#
# Same shape as scripts/deploy.sh, run against the local docker daemon rather
# than over ssh. Migrations are an explicit step for the same reason: outside
# development the app refuses to start on a stale schema, and the production
# compose file deliberately does not migrate on its own — a container restart
# must never quietly apply a schema change.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.prod-local.yml"
URL="http://localhost:8090"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }

case "${1:-up}" in

down)  say "Stopping (database kept)"; $COMPOSE down; exit 0 ;;
logs)  $COMPOSE logs -f; exit 0 ;;
reset)
  say "Destroying the local production database"
  read -rp "This deletes every account and project in the local prod instance. Type 'yes': " ok
  [ "$ok" = "yes" ] || die "aborted"
  $COMPOSE down -v
  exit 0
  ;;

up) ;;
*)  die "unknown command '${1}' (up | down | reset | logs)" ;;
esac

# ---------------------------------------------------------------- preflight
grep -q '^PROD_JWT_SECRET=.\+' .env 2>/dev/null \
  || die "no PROD_JWT_SECRET in ./.env — run ./scripts/dev-env.sh first"

say "Building"
$COMPOSE build

say "Verifying the image carries no secret or developer data"
# `docker compose run` MOUNTS the data volume, so it would inspect image+volume
# and report the runtime database as a leak. The question is what is baked into
# the image, so inspect the image directly, with nothing mounted.
# `compose images` only lists images belonging to existing CONTAINERS, so it
# returns nothing right after a `down` — precisely when this check matters most.
# `config --images` resolves the name from the file itself.
image=$($COMPOSE config --images koshi-backend)
[ -n "$image" ] || die "could not resolve the backend image name"
result=$(docker run --rm --entrypoint sh "$image" -c '
  test -f /app/.env       && echo LEAKED_ENV
  ls /app/data/*.db       >/dev/null 2>&1 && echo LEAKED_DB
  test -d /app/.venv      && echo LEAKED_VENV
  echo checked')
echo "$result" | grep -q LEAKED && die "image contains secrets or data: $result"
echo "  clean"

# ---------------------------------------------------------------- migrate
say "Backing up, then migrating"
$COMPOSE run --rm --no-deps --entrypoint sh koshi-backend -c '
  if [ -f /app/data/koshi.db ]; then
    cp /app/data/koshi.db "/app/data/koshi.db.bak-$(date +%Y%m%d-%H%M%S)" && echo "  backed up"
  else
    echo "  no existing database — first run"
  fi'

$COMPOSE run --rm --no-deps koshi-backend alembic upgrade head \
  || die "migration failed; the service was not started"

# ---------------------------------------------------------------- release
say "Starting"
$COMPOSE up -d

say "Waiting for health"
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$URL/api/health" 2>/dev/null || true)
  [ "$code" = "200" ] && { echo "  healthy after ${i}s"; break; }
  [ "$i" = 30 ] && die "not healthy in 30s — $COMPOSE logs koshi-backend"
  sleep 1
done

# ---------------------------------------------------------------- assert
# The point of this stack is that production settings are in force. Assert it
# rather than trusting the compose file, so a future edit that quietly relaxes
# one of them fails here.
say "Confirming production posture"

$COMPOSE exec -T koshi-backend python -c "
from app.config import settings
import sys
problems = []
if settings.ENVIRONMENT.lower() in ('development','dev','test','testing'):
    problems.append('ENVIRONMENT is development — the safety guard is disabled')
if settings.JWT_SECRET == settings.DEV_JWT_SECRET:
    problems.append('JWT_SECRET is the development default')
if settings.SEED_DEMO_DATA:
    problems.append('SEED_DEMO_DATA is on — known-password accounts exist')
if settings.CORS_ORIGINS.strip() == '*':
    problems.append('CORS_ORIGINS is a wildcard')
if settings.ALLOW_UNVERIFIED_GOOGLE_TOKENS:
    problems.append('unverified Google tokens are accepted')
for p in problems:
    print('  NOT PRODUCTION:', p)
sys.exit(1 if problems else 0)
" || die "the instance is not in a production posture"
echo "  guard armed, secret non-default, no demo seeding, CORS pinned"

$COMPOSE exec -T koshi-backend alembic current | grep -q '(head)' \
  || die "schema is not at head"
echo "  schema at head"

accounts=$($COMPOSE exec -T koshi-backend python -c "
from app.database import SessionLocal
from app.models.entities import User
db = SessionLocal(); print(db.query(User).count()); db.close()")
echo "  $accounts account(s) in the database"

say "Ready — $URL"
[ "$accounts" = "0" ] && echo "Empty instance: open the landing page and sign up to create the first account."
exit 0
