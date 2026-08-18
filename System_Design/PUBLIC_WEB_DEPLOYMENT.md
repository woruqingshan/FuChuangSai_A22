# Public Web Deployment

This runbook deploys the public CPU-server website for Zhixin Banxing.
It covers the public web layer and the Phase 5 AI status gateway. Full
public chat, media serving, sessions, jobs, and queueing are handled in
later phases.

## Architecture

```text
Internet
  -> zhixinbanxing.com
  -> CPU server ports 80/443
  -> Caddy
  -> frontend dist files
  -> /api/status
  -> edge-backend service
  -> CPU host 127.0.0.1:29000 SSH tunnel
  -> GPU host 127.0.0.1:19000 orchestrator /health
```

The frontend uses same-origin `/api/...` URLs in production. Phase 5 only
opens `/api/status`. Other `/api/*` routes intentionally return HTTP 503 JSON
so API requests are never served as `index.html`.

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

This stops the public web container. It keeps Caddy volumes unless explicitly
removed.

## Health Checks

```bash
curl -I http://zhixinbanxing.com
curl -I https://zhixinbanxing.com
curl -I https://www.zhixinbanxing.com
curl -I https://zhixinbanxing.com/app
curl -i https://zhixinbanxing.com/healthz
curl -i https://zhixinbanxing.com/api/status
curl -i https://zhixinbanxing.com/api/chat
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
- Other `/api/*` routes return HTTP 503 JSON until later phases connect them.

Check the host tunnel directly:

```bash
ss -lntp | grep 29000
curl -sS http://127.0.0.1:29000/health
```

The `29000` listener must be `127.0.0.1` only.

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
