#!/usr/bin/env bash
#
# Deploy Koshi to a remote host.
#
#   ./scripts/deploy.sh <ssh-host> [remote-dir]
#   ./scripts/deploy.sh umi /home/tupm/docker/koshi
#
# Replaces the ad-hoc tar|ssh one-liner that used to live in CLAUDE.md. That
# command excluded only .git, node_modules and dist — so it shipped, to the
# production host:
#
#   .env and source/backend/.env  — the developer's local secrets, overwriting
#                                   production's. source/backend/.env carries
#                                   ENVIRONMENT=development, SEED_DEMO_DATA=true
#                                   and CORS_ORIGINS=*, which would put the live
#                                   host into development mode with known-password
#                                   seed accounts — and the startup safety guard
#                                   would not object, because it exempts
#                                   development.
#   source/backend/data/*.db      — a developer database, over production's.
#   source/backend/.venv/         — a host virtualenv, hundreds of MB.
#
# (F-37.) Everything below exists to make those failures impossible rather than
# merely unlikely.
#
# The JWT secret is generated ON THE REMOTE and never leaves it. Nothing in this
# script transfers a secret, and no secret is ever passed as a command-line
# argument, where it would be visible in the remote process list.
set -euo pipefail

HOST="${1:?usage: deploy.sh <ssh-host> [remote-dir]}"
DIR="${2:-/home/tupm/docker/koshi}"
cd "$(dirname "$0")/.."

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- preflight
say "Preflight"
ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" true \
  || die "cannot reach '$HOST' over ssh (BatchMode: needs a key, not a password)"

git diff --quiet && git diff --cached --quiet \
  || die "working tree is dirty — commit or stash before deploying, so the
          deployed tree matches a commit you can point at"

echo "  host:   $HOST"
echo "  dir:    $DIR"
echo "  commit: $(git rev-parse --short HEAD) on $(git rev-parse --abbrev-ref HEAD)"

# ---------------------------------------------------------------- transfer
# Deliberately an allowlist of exclusions rather than "tar everything". Anything
# holding a credential, a database, or a platform-specific build must be named
# here. When in doubt, exclude it — the container builds what it needs.
say "Uploading source (secrets, databases and virtualenvs excluded)"
tar -czf - \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='dist' \
  --exclude='.env' \
  --exclude='.env.*' \
  `# .env.* also drops .env.example, which is only documentation and is in git.` \
  `# tar has no way to re-include after an exclude, and erring toward dropping` \
  `# an anything-dot-env is the right side to err on.` \
  --exclude='*.db' \
  --exclude='*.sqlite' \
  --exclude='*.sqlite3' \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='tsconfig.tsbuildinfo' \
  . | ssh "$HOST" "mkdir -p '$DIR' && tar -xzf - -C '$DIR'"

# Belt and braces: prove no secret landed, rather than trusting the exclude list.
say "Verifying no secret was transferred"
ssh "$HOST" "cd '$DIR' && find . -name '.env' -not -name '.env.example' \
  -not -path './node_modules/*' | grep . && echo LEAKED || echo clean" \
  | grep -qx clean || die ".env found on the remote after upload — check the exclude list"

# ---------------------------------------------------------------- secret
# Generated remotely, into a file only root/the deploy user can read. If one
# already exists it is left alone: rotating signs every user out, so it must be
# a deliberate act (ROTATE=1), never a side effect of deploying.
say "Ensuring a JWT secret exists on the remote"
ssh "$HOST" "cd '$DIR' && ROTATE='${ROTATE:-0}' sh -s" <<'REMOTE'
set -eu
if [ -f .env ] && grep -q '^JWT_SECRET=.\+' .env && [ "$ROTATE" != "1" ]; then
  echo "  keeping the existing JWT_SECRET (pass ROTATE=1 to rotate)"
else
  [ -f .env ] && grep -v '^JWT_SECRET=' .env > .env.tmp || : > .env.tmp
  printf 'JWT_SECRET=%s\n' "$(openssl rand -hex 32)" >> .env.tmp
  mv .env.tmp .env
  chmod 600 .env
  echo "  wrote a NEW JWT_SECRET — every existing session is now invalid"
fi
REMOTE

# ---------------------------------------------------------------- build
say "Building images from scratch"
# --no-cache because a cached layer can carry a file the new .dockerignore was
# added to exclude (F-32); a cache hit would silently keep shipping it.
ssh "$HOST" "cd '$DIR' && docker compose build --no-cache"

say "Verifying the built image carries no secret"
ssh "$HOST" "cd '$DIR' && docker compose run --rm --no-deps --entrypoint sh koshi-backend -c '
  test -f /app/.env && echo LEAKED_ENV;
  ls /app/data/*.db >/dev/null 2>&1 && echo LEAKED_DB;
  test -d /app/.venv && echo LEAKED_VENV;
  echo checked'" | grep -q LEAKED && die "the built image still contains secrets or data" || true

# ---------------------------------------------------------------- migrate
# Outside development the API refuses to start unless the database is at head
# (D6 RISK-10), and the production compose file does not run migrations itself —
# by design, so a forgotten migration fails loudly rather than being papered
# over by an implicit create_all. That means the deploy has to run them, in a
# one-off container, BEFORE bringing the service up.
#
# Back up first: 0002 drops users.role and its downgrade reconstructs that
# column from memberships rather than restoring the original values (D6 §7.2).
say "Backing up the database, then migrating"
ssh "$HOST" "cd '$DIR' && docker compose run --rm --no-deps --entrypoint sh koshi-backend -c '
  if [ -f /app/data/koshi.db ]; then
    cp /app/data/koshi.db \"/app/data/koshi.db.bak-\$(date +%Y%m%d-%H%M%S)\" && echo \"  backed up\";
  else
    echo \"  no existing database — this is a first deploy\";
  fi'"

ssh "$HOST" "cd '$DIR' && docker compose run --rm --no-deps koshi-backend alembic upgrade head" \
  || die "migration failed — the service was NOT started, so the old container
          is still serving. Investigate before retrying; if this is a database
          created before Alembic existed, see D6 §7.2 for the stamp step."

# ---------------------------------------------------------------- release
say "Starting"
ssh "$HOST" "cd '$DIR' && docker compose up -d"

say "Health check"
for i in $(seq 1 30); do
  if ssh "$HOST" "cd '$DIR' && docker compose exec -T koshi-backend \
       python -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)\"" 2>/dev/null; then
    echo "  healthy after ${i}s"
    break
  fi
  [ "$i" = 30 ] && die "backend did not become healthy in 30s — check: ssh $HOST 'cd $DIR && docker compose logs koshi-backend'"
  sleep 1
done

say "Confirming the schema is at head"
ssh "$HOST" "cd '$DIR' && docker compose exec -T koshi-backend alembic current" \
  | grep -q '(head)' || die "database is not at the head revision — see D6 §7.2"

# ---------------------------------------------------------------- cleanup
# Rotation does not un-publish an image containing the old secret (D6 §7.1).
say "Removing superseded images"
ssh "$HOST" "docker image prune -f --filter 'label!=keep' && docker images -f dangling=true -q | xargs -r docker rmi -f" || true

say "Done — $(git rev-parse --short HEAD) is live on $HOST"
echo "If you passed ROTATE=1, every user is signed out and must log in again."
