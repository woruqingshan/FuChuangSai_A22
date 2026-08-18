# Public Web Deployment

This runbook deploys the public CPU-server website for Zhixin Banxing.
It covers the public web layer, AI status gateway, public chat gateway, avatar
media proxy, anonymous sessions, invitation access, queueing, and Phase 9
account persistence.

## Architecture

```text
Internet
  -> zhixinbanxing.com
  -> CPU server ports 80/443
  -> Caddy
  -> frontend dist files
  -> /api/status, /api/session, /api/access/*, /api/auth/*, /api/chat, /api/jobs/*, /media/*
  -> edge-backend service
  -> Redis on CPU loopback for short-lived state
  -> PostgreSQL on CPU loopback for users/accounts/invitations
  -> CPU host 127.0.0.1:29000 SSH tunnel
  -> GPU host 127.0.0.1:19000 orchestrator
```

The frontend uses same-origin `/api/...` and `/media/...` URLs in production.
The public stack explicitly opens only `/api/status`, `/api/chat`, and the
fixed avatar media routes. Other `/api/*` routes intentionally return HTTP
503 JSON so API requests are never served as `index.html`.

The Docker services use host networking so the edge backend can reach
the host-only SSH tunnel at `127.0.0.1:29000`. The edge backend binds only
`127.0.0.1:18080`; it must not listen on a public interface.

Redis and PostgreSQL are bound only to CPU loopback:

```text
127.0.0.1:6379
127.0.0.1:5432
```

They are not routed through Caddy and must not be exposed publicly.

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

The edge backend runs database migrations before starting:

```text
alembic upgrade head
```

Do not drop or recreate PostgreSQL tables during normal deploys. Redis and
PostgreSQL use persistent Docker volumes.

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
curl -i -c /tmp/a22.cookies -b /tmp/a22.cookies -X POST https://zhixinbanxing.com/api/session
curl -i -c /tmp/a22.cookies -b /tmp/a22.cookies https://zhixinbanxing.com/api/auth/me
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
- `/api/session` creates or reuses an anonymous server-side session and sets an
  HttpOnly cookie.
- `/api/access/status` reports whether the current Session already has
  invitation access.
- `/api/access/verify` validates a runtime-configured invitation code and sets
  an HttpOnly `a22_access` cookie.
- `/api/auth/register` creates a User and Account, stores an Argon2id password
  hash, sets an HttpOnly `a22_auth` cookie, and binds the current Session to
  the new User. Registration requires invitation access in the current demo.
- `/api/auth/login` verifies username/password, sets `a22_auth`, and binds the
  current Session to the User without changing `session_id`.
- `/api/auth/logout` clears `a22_auth` and leaves the technical anonymous
  Session in place.
- `/api/auth/me` returns public account status without exposing tokens or
  password hashes.
- `/api/chat` requires a valid anonymous session cookie plus invitation access,
  then returns HTTP 202 with a Job id.
- `/api/jobs/{job_id}` is session-owned and returns queue / generation status.
- `/media/video-stream/*`, `/media/video-chunk/*`, and `/media/video/*` are
  authorized against the anonymous session before being proxied through the edge
  backend to the GPU media routes.
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
Redis `6379` and PostgreSQL `5432` must also be `127.0.0.1` only.

## Phase 9 Persistence

Phase 9 introduces Redis and PostgreSQL as required runtime dependencies.
There is no silent fallback to Python in-memory state if either storage service
is unavailable.

Redis stores short-lived state:

- `a22_session` session records by token digest.
- `a22_access` invitation access grants by token digest.
- `a22_auth` auth sessions by token digest.
- rate-limit windows.
- Job state and queue state.

PostgreSQL stores durable product records:

- `users`
- `accounts`
- `invitation_codes`

Invitation codes are stored by deterministic fingerprint only. Real code values
stay in the local server environment and are not committed.

Cookie responsibilities:

- `a22_session`: current technical browser Session.
- `a22_access`: permission to use expensive GPU generation.
- `a22_auth`: registered account authentication.

Registered account login does not automatically grant GPU access. Invitation
access remains separate.

Edge restart recovery:

- Redis Session / Access / Auth survives.
- Queued Jobs survive and can continue.
- Rendering Jobs with saved chat response resume manifest monitoring.
- Processing Jobs are failed conservatively as
  `edge_restarted_during_processing` to avoid duplicate GPU generation.

Limit:

GPU Orchestrator recent conversation history is still GPU process memory.
Phase 9 persists CPU edge state and accounts; it does not persist GPU-side
conversation history or implement long-term UserProfile memory.

## Phase 7 Session Model

Phase 7 makes the CPU edge backend the session authority:

```text
Browser HttpOnly cookie
  -> edge SessionRegistry
  -> server-generated internal session_id
  -> server-owned turn_id and stream_id
  -> GPU orchestrator
```

Production cookie:

- Name: `a22_session`
- `HttpOnly`
- `Secure`
- `SameSite=Lax`
- `Path=/`
- Browser-session cookie; no persistent `Max-Age` is set.

The cookie token is a credential and must not be logged, returned in JSON, added
to URLs, or sent to the GPU. The internal session id is an identifier and uses a
Beijing time (UTC+8) timestamp plus strong randomness:

```text
sess_YYYYMMDDTHHMMSSCST_<32 hex random>
stream_YYYYMMDDTHHMMSSCST_<16 hex random>
```

The timestamp is for operations readability only. The random suffix provides
the security property. IP addresses are not used in session ids.

The edge backend ignores client-provided `session_id` and `turn_id` in chat
payloads. It allocates the internal session id, stream id, and turn id from the
server-side registry. It also overwrites `turn_time_window.window_id`,
`turn_time_window.stream_id`, and `turn_time_window.sequence_id` before sending
requests to the GPU, while preserving sensor timing fields such as capture
timestamps.

Media routes are session-bound:

- Missing or expired cookie: HTTP 401.
- Valid cookie for a different session path: HTTP 403.
- Same-session media path: proxied upstream.

This applies to manifests, video chunks, full video, `HEAD`, and `Range`
requests.

## Phase 7 / 8 Historical Limits

Phase 7 originally used a single-process in-memory SessionRegistry. Phase 8
originally added an in-memory invitation gate, one-active-job-per-session,
bounded queue, queue position, and rate limit. Those CPU-edge states are moved
to Redis in Phase 9.

Production still runs one Uvicorn worker in Phase 9. Redis provides the
foundation for future multi-worker operation, but the service should not be
scaled to multiple workers without a follow-up concurrency review.

## Phase 8 Access And Capacity Gate

Phase 8 adds an invitation gate and bounded public GPU queue on the CPU edge
backend. After Phase 9, Access Grants, Jobs, Queue, and Rate Limit state are
Redis-backed, while invitation `used_count` is PostgreSQL-backed.

Runtime-only secret configuration:

```text
INVITATION_CODES_JSON
```

Example shape only:

```json
[
  {
    "code": "<secret>",
    "enabled": true,
    "expires_at": "2026-12-31T23:59:59+08:00",
    "max_uses": 20
  }
]
```

Do not commit the real code value. On the CPU server, keep it in a local
environment file that is excluded from Git.

Public chat now uses Jobs:

```text
POST /api/chat -> 202 { job_id, status, queue_position }
GET /api/jobs/{job_id} -> queued / processing / rendering / completed / failed
```

The single public Job worker keeps the GPU slot until the LiveAvatar manifest is
terminal. This means the slot is not released when GPU `/chat` returns; it is
released only after manifest complete / render failure / timeout.

Configured defaults:

```text
ACCESS_COOKIE_NAME=a22_access
ACCESS_TTL_SECONDS=86400
JOB_QUEUE_MAX_PENDING=3
JOB_RENDER_TIMEOUT_SECONDS=1800
JOB_RETENTION_SECONDS=3600
JOB_MANIFEST_POLL_SECONDS=2
```

Phase 9 keeps the same public Job contract but persists the CPU edge state.
Edge restart no longer clears Session, Access, Auth, Rate Limit, queued Jobs, or
invitation used-count state.

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
