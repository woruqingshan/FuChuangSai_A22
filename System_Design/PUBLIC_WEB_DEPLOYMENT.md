# Public Web Deployment

This runbook deploys the public CPU-server website for Zhixin Banxing.
It covers the public web layer, AI status gateway, public chat gateway, and
avatar media proxy. Formal sessions, authorization, jobs, queueing, and rate
limits are handled in later phases.

## Architecture

```text
Internet
  -> zhixinbanxing.com
  -> CPU server ports 80/443
  -> Caddy
  -> frontend dist files
  -> /api/status, /api/chat, /media/*
  -> edge-backend service
  -> CPU host 127.0.0.1:29000 SSH tunnel
  -> GPU host 127.0.0.1:19000 orchestrator
```

The frontend uses same-origin `/api/...` and `/media/...` URLs in production.
The public stack explicitly opens only `/api/status`, `/api/chat`, and the
fixed avatar media routes. Other `/api/*` routes intentionally return HTTP
503 JSON so API requests are never served as `index.html`.

The Phase 5 Docker services use host networking so the edge backend can reach
the host-only SSH tunnel at `127.0.0.1:29000`. The edge backend binds only
`127.0.0.1:18080`; it must not listen on a public interface.

## GPU Tunnel

Create a host-level SSH tunnel with a private key that is stored outside Git.
The tunnel must bind only to CPU loopback:

```text
CPU 127.0.0.1:29000 -> GPU 127.0.0.1:19000
```

Use systemd or an equivalent supervisor so the tunnel restarts automatically.
Do not commit SSH targets, private keys, passwords, or server-specific unit
files. A typical unit uses:

```text
ssh -NT \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -L 127.0.0.1:29000:127.0.0.1:19000 \
  <gpu-ssh-alias-or-host>
```

## First Deploy

Confirm DNS records point to the CPU server:

```bash
nslookup zhixinbanxing.com
nslookup www.zhixinbanxing.com
```

Build and start the public web stack:

```bash
docker compose -f compose.yaml -f compose.public.yaml up -d --build
```

Check status:

```bash
docker compose -f compose.yaml -f compose.public.yaml ps
docker compose -f compose.yaml -f compose.public.yaml logs --tail=100 public-web
docker compose -f compose.yaml -f compose.public.yaml logs --tail=100 edge-backend
```

## Update Deploy

After pulling or checking out reviewed code:

```bash
docker compose -f compose.yaml -f compose.public.yaml up -d --build
docker compose -f compose.yaml -f compose.public.yaml ps
```

## Stop

```bash
docker compose -f compose.yaml -f compose.public.yaml down
```

This stops the public web and edge backend containers. It keeps Caddy volumes
unless explicitly removed.

## Health Checks

```bash
curl -I http://zhixinbanxing.com
curl -I https://zhixinbanxing.com
curl -I https://www.zhixinbanxing.com
curl -I https://zhixinbanxing.com/app
curl -i https://zhixinbanxing.com/healthz
curl -i https://zhixinbanxing.com/api/status
curl -i https://zhixinbanxing.com/api/chat
curl -i https://zhixinbanxing.com/media/video-stream/example/1/manifest
```

Expected:

- HTTP redirects to HTTPS.
- `https://zhixinbanxing.com/` serves the landing page.
- `https://zhixinbanxing.com/app` serves the app shell and supports refresh.
- `https://www.zhixinbanxing.com/*` redirects to the apex domain.
- `/healthz` returns HTTP 200.
- `/api/status` returns HTTP 200 with `ai_available=true` when the GPU tunnel
  and orchestrator are healthy.
- `/api/status` returns HTTP 503 with `ai_available=false` when the tunnel or
  GPU orchestrator is unavailable.
- `/api/chat` is proxied through the edge backend to the GPU orchestrator.
- `/media/video-stream/*`, `/media/video-chunk/*`, and `/media/video/*` are
  proxied through the edge backend to the GPU media routes.
- Other `/api/*` routes return HTTP 503 JSON.
- Unknown media objects return upstream media errors such as HTTP 404, not SPA
  `index.html`.

Check the host tunnel directly:

```bash
ss -lntp | grep 29000
curl -sS http://127.0.0.1:29000/health
```

The `29000` listener must be `127.0.0.1` only.
The edge backend `18080` listener must also be `127.0.0.1` only.

## Phase 6 Limits

The Phase 6 public chain is intended for single-user or small engineering
validation. It does not provide formal session isolation, media ownership
authorization, one-active-job-per-session enforcement, queueing, Redis-backed
persistence, or rate limiting.

## Logs

```bash
docker compose -f compose.yaml -f compose.public.yaml logs -f public-web
docker compose -f compose.yaml -f compose.public.yaml logs -f edge-backend
```

## Rollback

List recent commits:

```bash
git log --oneline -10
```

Checkout or revert to a known-good commit, then rebuild:

```bash
docker compose -f compose.yaml -f compose.public.yaml up -d --build
```

Do not remove Caddy data volumes during normal rollback. They contain ACME
certificate state used for HTTPS renewal.

## Security Boundary

The public stack exposes only ports 80 and 443. It must not expose local
development ports, the edge backend container port, the tunnel port, or
GPU/model services. Do not commit certificates, private keys, `.env` files,
logs, `node_modules`, built `dist` artifacts, SSH targets, or host-specific
systemd units.
