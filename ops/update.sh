#!/bin/sh
# Update Irene on the controller (BUILD-10, design D-5). Run after `git pull`:
#   cd /mnt/sdcard/wb-mqtt-voice && git pull && ./ops/update.sh
#
# The clone (on the SD card) is the delivery vehicle; the containers mount the
# runtime tree at /mnt/data/mqtt-voice-config (same split as the sibling
# mqtt-bridge-config). This script bridges the two:
#
# 1. Sync the GIT-OWNED assets content (donations/localization/prompts/templates/web +
#    the donation contract schemas) from the clone into the runtime assets tree.
#    --delete keeps each synced subtree exactly matching the repo; the enumeration is
#    EXPLICIT so runtime-owned subtrees (models/ cache/ state/ traces/ credentials/
#    temp/) are never touched — that's where downloaded models and durable action
#    records live (never delete them on update).
# 2. Pull fresh images and restart; prune old untagged layers (WB flash is small).
set -eu
cd "$(dirname "$0")"

RUNTIME_DIR="${RUNTIME_DIR:-/mnt/data/mqtt-voice-config}"
ASSETS_DIR="$RUNTIME_DIR/assets"
LOGS_DIR="$RUNTIME_DIR/logs"
CONFIG_DIR="$RUNTIME_DIR/config"
# Which profile TOML this controller runs (must match the image variant):
# embedded-armv7 (WB7, default) | embedded-aarch64 (WB8.5/Pi) | *-en variants.
CONFIG_PROFILE="${CONFIG_PROFILE:-embedded-armv7}"
mkdir -p "$ASSETS_DIR" "$LOGS_DIR" "$CONFIG_DIR"

# THE REPO OWNS THE CONFIG (bridge semantics): delivered on every update, on-box
# edits are overwritten — config changes are made in the repo and arrive by git pull.
cp "../configs/$CONFIG_PROFILE.toml" "$CONFIG_DIR/irene.toml"
echo "config delivered -> $CONFIG_DIR/irene.toml ($CONFIG_PROFILE)"

for d in donations localization prompts templates web; do
    rsync -a --delete "../assets/$d/" "$ASSETS_DIR/$d/"
done
cp ../assets/donation_contract_v1.1.json ../assets/donation_language_v1.1.json "$ASSETS_DIR/"

# The container runs as uid 1000 (`USER irene`); on the controller this script runs as
# root, so the mounted tree must be handed to that uid or the first model download /
# log write fails with EACCES.
chown -R 1000:1000 "$ASSETS_DIR" "$LOGS_DIR" 2>/dev/null || true
echo "assets synced -> $ASSETS_DIR"

docker compose pull
docker compose up -d --remove-orphans
docker image prune -f
docker compose ps
