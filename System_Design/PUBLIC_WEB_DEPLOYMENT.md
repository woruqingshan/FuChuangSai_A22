# Public Web Deployment

This runbook deploys the public CPU-server website for Zhixin Banxing.
It only covers the static public web layer. GPU inference, the public API
gateway, sessions, jobs, and queueing are handled in later phases.

## Architecture

```text
Internet
  -> zhixinbanxing.com
  -> CPU server ports 80/443
  -> Docker Compose public-web service
  -> Caddy
  -> frontend dist files
```

The frontend uses same-origin `/api/...` URLs in production. In this phase,
`/api/*` intentionally returns HTTP 503 JSON so API requests are never served
as `index.html`.

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
curl -i https://zhixinbanxing.com/api/chat
```

Expected:

- HTTP redirects to HTTPS.
- `https://zhixinbanxing.com/` serves the landing page.
- `https://zhixinbanxing.com/app` serves the app shell and supports refresh.
- `https://www.zhixinbanxing.com/*` redirects to the apex domain.
- `/healthz` returns HTTP 200.
- `/api/*` returns HTTP 503 JSON until the public gateway is connected.

## Logs

```bash
docker compose -f compose.yaml -f compose.public.yaml logs -f public-web
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
development ports or GPU/model services. Do not commit certificates, private
keys, `.env` files, logs, `node_modules`, or built `dist` artifacts.
