# BUILD-9 (design D-4): config-ui as a bridge-style static nginx image.
# ONE multi-arch manifest (amd64+arm64+armv7) — the dist is arch-independent, only the
# nginx base differs per platform. Published as ghcr.io/droman42/wb-mqtt-voice-ui; NOT
# deployed to the controller for now (the ops/ compose ships it disabled).
#
# No proxy stage: Irene's API has no /api prefix and serves permissive CORS, so the
# browser talks to the backend directly. The API base is runtime-injected via
# /runtime-config.js (API_BASE_URL env; empty = same-hostname:6000 fallback in code).

FROM node:22-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.d/40-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/40-runtime-config.sh

EXPOSE 3000
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost:3000/ || exit 1
