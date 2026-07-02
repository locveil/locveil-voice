// Dev default (served by vite from public/). In the nginx image this file is OVERWRITTEN
// at container start from the API_BASE_URL env var (docker-entrypoint.sh). Empty means:
// use http://<page-hostname>:6000 (see apiClient.ts).
window.__IRENE_API_BASE__ = "";
