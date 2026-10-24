#!/usr/bin/env bash
#
# Publish the local production instance on a public hostname via a Cloudflare
# Tunnel.  ./scripts/publish.sh koshi.huynhca.com
#
# One-time prerequisite: `cloudflared tunnel login` (the domain owner approves
# it in the browser; it writes ~/.cloudflared/cert.pem).
#
# Outbound-only: no port is opened on the router and the machine's IP is not
# published. The tunnel points at the nginx frontend container, which proxies
# /api, so the browser sees one origin and CORS only needs that origin.
set -euo pipefail
HOST="${1:?usage: publish.sh <hostname>}"
NAME="koshi"
CF="${CLOUDFLARED:-$HOME/.local/bin/cloudflared}"
cd "$(dirname "$0")/.."
say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }

[ -f "$HOME/.cloudflared/cert.pem" ] || die "run '$CF tunnel login' first"

say "Tunnel"
if ! "$CF" tunnel list -o json | grep -q "\"name\":\"$NAME\""; then
  "$CF" tunnel create "$NAME"
fi
ID=$("$CF" tunnel list -o json | python3 -c "import json,sys;print([t['id'] for t in json.load(sys.stdin) if t['name']=='$NAME'][0])")
echo "  $NAME = $ID"

say "DNS: $HOST -> tunnel"
"$CF" tunnel route dns --overwrite-dns "$NAME" "$HOST"

say "Config"
cat > "$HOME/.cloudflared/config.yml" <<CFG
tunnel: $ID
credentials-file: /etc/cloudflared/$ID.json
ingress:
  - hostname: $HOST
    service: http://koshi-frontend-prod-local:80
  - service: http_status:404
CFG
chmod 600 "$HOME/.cloudflared/"*.json

# CORS must name the public origin; the backend reads it at startup.
grep -v '^PUBLIC_ORIGIN=' .env > .env.tmp || true
echo "PUBLIC_ORIGIN=https://$HOST" >> .env.tmp && mv .env.tmp .env && chmod 600 .env

say "Restarting the instance with the public origin"
./scripts/local-prod.sh up
UID_GID="$(id -u):$(id -g)" docker compose -f docker-compose.prod-local.yml --profile public up -d cloudflared

say "Waiting for https://$HOST"
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "https://$HOST/api/health" || true)
  [ "$code" = 200 ] && { echo "  live after ${i}s"; break; }
  [ "$i" = 60 ] && die "not reachable yet (DNS can take a minute) — docker logs koshi-tunnel"
  sleep 2
done
say "Published — https://$HOST"
