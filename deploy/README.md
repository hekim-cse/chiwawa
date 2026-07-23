# Chiwawa production deployment

The production stack exposes only the Flutter/Nginx container on host port
`8082`, matching the existing `violai` deployment pattern. FastAPI has no host
port and is reachable only by the frontend container over the private Compose
network.

## First-time setup

```bash
cp deploy/chiwawa.production.env.example deploy/chiwawa.production.env
mkdir -p deploy/runtime
```

Set the real Google, Maps, Gemini, image-search, and JWT values in
`deploy/chiwawa.production.env`. The Google OAuth client must use this callback:

```text
https://chiwawa.jmllem.com/api/v1/auth/google/callback
```

Keep `REQUIRE_AUTH=true` in production. It protects the trip, wanted-place,
plan, schedule, travel, and assistant APIs from anonymous requests.

Photo place search accepts the frontend's multipart image upload. The backend
temporarily stores the image under `PHOTO_SEARCH_UPLOAD_DIR`, publishes it at
a random short-lived URL under `PUBLIC_BASE_URL`, and sends that URL to the
Modal image-search service. The temporary file is deleted when recognition
finishes.

The Cloudflare hostname must allow unauthenticated origin fetches for
`/api/v1/photo-search-images/*`; Modal fetches this short-lived URL as a
server-to-server request and cannot complete a browser/WAF challenge.

## Build and run

```bash
docker compose -f docker-compose.production.yml config
docker compose -f docker-compose.production.yml up -d --build
docker compose -f docker-compose.production.yml ps
```

The existing Cloudflare Tunnel must route the public hostname
`chiwawa.jmllem.com` to the frontend host port:

```text
http://172.17.0.1:8082
```

The frontend binds to the Docker bridge address only, so direct access through
the server's LAN/public address is not enabled by this Compose file.

Cloudflare terminates HTTPS at the edge. The public API is accessed through
the same origin, for example:

```text
https://chiwawa.jmllem.com/api/v1/trips
```

## Health checks

```bash
curl -fsS https://chiwawa.jmllem.com/health
docker compose -f docker-compose.production.yml logs --tail=100 backend frontend
```
