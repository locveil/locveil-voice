#!/bin/sh
# ONE-TIME env-family cutover: IRENE_* -> LOCVEIL_VOICE_* on the controller (BUILD-36/PROD-21).
#
# The pydantic env_prefix and the explicit env keys were renamed in code AND in the
# repo-owned docker-compose.yml (LOCVEIL_VOICE_CONFIG_FILE, LOCVEIL_VOICE_REPORTS_TOKEN).
# The compose changes reach the controller by `git pull` + update.sh; the ONE hand-maintained
# key lives in the runtime `.env` (the reports token). This script swaps that key, delivers the
# renamed compose, and smokes /health — the whole cutover in one atomic step.
#
# Run on the controller, as root, AFTER the pull brings in the renamed compose:
#
#   cd /mnt/sdcard/locveil-voice && git pull && sh ops/cutover-env-locveil-voice.sh
#
# Idempotent: safe to re-run (a second run finds nothing to rename).
set -eu
cd "$(dirname "$0")"

RUNTIME=/mnt/data/locveil-voice-config
ENV_FILE="$RUNTIME/.env"

# 1. Rename the one secret key in the runtime .env (keeps a one-time .bak).
if [ -f "$ENV_FILE" ] && grep -q '^IRENE_REPORTS_TOKEN=' "$ENV_FILE"; then
    cp -n "$ENV_FILE" "$ENV_FILE.pre-locveil-env.bak"
    sed -i 's/^IRENE_REPORTS_TOKEN=/LOCVEIL_VOICE_REPORTS_TOKEN=/' "$ENV_FILE"
    echo ".env: IRENE_REPORTS_TOKEN -> LOCVEIL_VOICE_REPORTS_TOKEN (backup: $ENV_FILE.pre-locveil-env.bak)"
else
    echo ".env: no IRENE_REPORTS_TOKEN to rename (already cut over, or token unset) — ok"
fi

# 2. Deliver the renamed compose (new env keys) into the runtime tree + restart the stack.
./update.sh

# 3. Smoke: the service answers /health under the new env.
echo ">> smoke: waiting for /health ..."
ok=0
for _ in $(seq 1 60); do
    if curl -sf http://localhost:8080/health >/dev/null 2>&1; then ok=1; break; fi
    sleep 1
done
[ "$ok" = 1 ] || { echo "SMOKE FAILED: :8080/health not answering — check 'docker logs -f locveil-voice'" >&2; exit 1; }
echo "env cutover complete.  verify:  docker exec locveil-voice env | grep LOCVEIL_VOICE_"
