#!/bin/sh
# BUILD-9 (D-4): inject the runtime API base for the browser. Empty API_BASE_URL means
# the app falls back to http://<page-hostname>:6000 — right for the usual "UI and Irene
# on the same box" case; set API_BASE_URL to point elsewhere.
set -eu
cat > /usr/share/nginx/html/runtime-config.js <<EOF
// Written at container start (docker-entrypoint.d/40-runtime-config.sh).
window.__IRENE_API_BASE__ = "${API_BASE_URL:-}";
EOF
