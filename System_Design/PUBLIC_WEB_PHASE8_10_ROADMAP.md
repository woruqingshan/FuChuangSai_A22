# Public Web Phase 8-10 Roadmap

This document fixes the product-domain boundaries after Phase 7 session
isolation. It is intentionally a design foundation, not an implementation
commitment for Phase 7.5.

## Current State After Phase 7

Current capabilities:

- Session Isolation: yes.
- HttpOnly anonymous session cookie: yes.
- CPU edge backend as session authority: yes.
- Server-owned `session_id`, `stream_id`, and `turn_id`: yes.
- Media ownership authorization: yes.
- Same-session media access: allowed.
- Missing cookie: HTTP 401.
- Cross-session media: HTTP 403.

Not implemented yet:

- User Account: no.
- Persistent User: no.
- Long-term UserProfile: no.
- Capacity Queue: no.
- One active generation per session: no.
- Rate limit: no.
- Redis / database persistence: no.

The current public prototype should be described as a server-side anonymous
session isolated AI web prototype. It should not be described as a registered
multi-user product with persistent user memory.

## Domain Definitions

### Session

A Session is a technical isolation unit for one anonymous browser usage period
and its conversation context.

Current fields:

- `session_id`
- `stream_id`
- turn sequence
- `created_at`
- `last_seen_at`

Current binding:

```text
HttpOnly a22_session cookie
  -> CPU SessionRegistry
  -> internal session_id / stream_id
```

Current responsibilities:

- Chat isolation
- GPU context routing
- Media ownership authorization

A Session is not a long-term user identity. Do not rename `session_id` to
`user_id`, and do not treat one Session as one User.

### User

A User is the long-term business entity.

Future relationship:

```text
User 1
  -> Session A
  -> Session B
  -> Session C
```

Anonymous sessions currently have `user_id = null`. After account support is
added, registered sessions can be associated with a concrete User.

### Account

An Account is the authentication credential entity for a User.

Future responsibilities:

- username
- password hash
- login / logout
- authentication state

Account is not the same as User. A User is the business entity; an Account is a
way to access that User's data.

### UserProfile

A UserProfile stores long-term personalization and companionship knowledge for
a User.

Future relationship:

```text
User
  -> UserProfile
  -> Sessions
```

UserProfile belongs to `user_id`, not to one `session_id`. It must work across
Sessions after login and persistence exist.

## Current AI Context vs Future UserProfile

The current GPU orchestrator already has turn and session-level capabilities:

- current text input
- speech features
- vision features
- multimodal alignment
- emotion state
- RAG route
- conversation history
- recent context
- context summary

The current system does not yet have:

- UserProfile Builder
- Profile Extractor
- Profile Updater
- cross-session profile retrieval
- persistent user memory

Correct wording:

> The system already has multimodal state awareness and Session-level multi-turn
> context. These capabilities provide the data foundation for future long-term
> UserProfile construction.

Incorrect wording:

> The system already supports persistent long-term user profiles.

## Future Schema Direction

### User

```text
user_id
status
created_at
updated_at
```

### Account

```text
account_id
user_id
username
password_hash
created_at
last_login_at
status
```

### UserProfile

```text
user_id

stable_profile:
  preferred_name
  age_range
  living_situation
  interests
  preferred_topics
  communication_style
  preferred_avatar
  daily_habits
  important_people

dynamic_profile:
  recent_topics
  recent_concerns
  recent_emotion_trend
  interaction_frequency
  recent_support_needs
  last_interaction_at
```

### Session

```text
session_id
user_id nullable
stream_id
created_at
last_seen_at
```

In the current anonymous-only system, `user_id = null`.

## Phase 8: Access & Capacity Protection

Phase 8 answers:

```text
Who is allowed to use the expensive GPU?
How does the service handle simultaneous users safely?
```

Phase 8 does not implement Accounts.

Planned architecture:

```text
Browser
  -> Invitation Gate
  -> Server Session
  -> Rate Limit
  -> one-active-job-per-session
  -> bounded queue
  -> GPU
```

### Invitation Code

Invitation codes are GPU access control, not user identity.

Recommended flow:

```text
Visitor
  -> enter invitation code
  -> POST /api/access/verify
  -> CPU validates code
  -> HttpOnly Access Cookie
  -> Chat allowed
```

Cookies stay separate:

- Session cookie: `a22_session`
- Access cookie: `a22_access`

Do not store the invitation code itself in browser localStorage.

Invitation model:

```text
code
enabled
expires_at
max_uses
used_count
created_at
```

Public endpoints:

- `/`
- `/app`
- `/healthz`
- `/api/status`
- `/api/session`

Access-protected endpoints:

- `POST /api/chat`
- future Job / Queue APIs

Media already has session ownership authorization. Whether media should also
require the Access Cookie should be decided during the Phase 8 threat-model
review.

### Job Model

Phase 8 introduces a formal Job:

```text
job_id
session_id
turn_id
status:
  queued
  processing
  rendering
  completed
  failed
  cancelled
created_at
started_at
completed_at
error
```

Current behavior:

```text
POST /chat -> LiveAvatar
```

Future behavior:

```text
POST /chat -> Job -> Capacity Manager -> GPU
```

### One Active Job Per Session

The server must enforce:

```text
one session -> at most one active generation
```

Frontend-only `isSending` is not enough because multiple tabs can share the
same session cookie. If a session already has an active job, return a clear
conflict response such as HTTP 409.

### Bounded Global Queue

Because one high-quality LiveAvatar generation can take several minutes,
Phase 8 must add a bounded queue. A first deployment can use a small limit such
as one rendering job plus three to five queued jobs, adjusted after real
testing.

When the queue is full, return HTTP 429. Do not accept unlimited work.

### Queue State

Users should see:

- queued
- position
- rendering
- completed
- failed

The frontend should eventually show product language such as:

```text
当前正在排队，前方还有 2 个任务。
```

### Rate Limit

Phase 8 starts rate limiting by:

- IP address
- Session

IP is only an abuse-protection dimension. It must not be used as Session ID,
User ID, or Account ID.

Phase 8 completion state:

> The system becomes a controlled-access public AI demo service with bounded GPU
> capacity.

### Phase 8 Implementation Snapshot

Phase 8 is implemented as a single-process in-memory public access and capacity
gate in the CPU edge backend.

Implemented public APIs:

- `GET /api/access/status`
- `POST /api/access/verify`
- `POST /api/chat`
- `GET /api/jobs/{job_id}`

Cookie separation:

- `a22_session`: anonymous technical Session credential.
- `a22_access`: invitation access credential.

The access token is opaque, HttpOnly, Secure, SameSite=Lax, and bound to the
current server-side `session_id`. Access does not create a User, Account, or
UserProfile.

Invitation code configuration is supplied through runtime environment, not Git:

```text
INVITATION_CODES_JSON
```

The production code value must not be committed, returned in JSON, put into the
frontend bundle, or written to logs.

The public chat flow is now asynchronous:

```text
POST /api/chat
  -> validate Session
  -> validate Access
  -> rate limit
  -> create Job
  -> HTTP 202 { job_id, status, queue_position }

GET /api/jobs/{job_id}
  -> queued / processing / rendering / completed / failed
```

The frontend polls the Job until `chat_response_ready=true`. Once a
ChatResponse is available, the existing LiveAvatar frontend renderer continues
to poll `/media/video-stream/.../manifest` and plays the synchronized video.

GPU slot ownership:

- Acquired when the single public Job worker claims a queued Job.
- Held through GPU `/chat`.
- Remains held during LiveAvatar background rendering.
- Released only after the backend Job worker observes manifest terminal state:
  `complete=true` with chunks, `complete=true` with error/no chunks, or render
  timeout.

Default capacity:

```text
1 active public GPU generation
JOB_QUEUE_MAX_PENDING=3
```

One-active-job rule:

```text
one Session -> at most one queued / processing / rendering Job
```

If violated, `POST /api/chat` returns HTTP 409. If the bounded queue is full,
it returns HTTP 429 with `reason=queue_full`.

Basic in-memory rate limits:

- Invitation verification by client IP.
- Chat submission by Session.
- Chat submission by client IP.

Caddy overwrites `X-A22-Client-IP` before forwarding API requests to Edge, and
the Edge rate limiter uses that trusted header with `request.client.host` as a
fallback.

Phase 8 in-memory state:

- invitation `used_count`
- access grants
- rate-limit windows
- Jobs
- queue

Known Phase 8 limits:

- Edge restart invalidates access grants.
- Edge restart loses Job / Queue state.
- Edge restart resets invitation `used_count`.
- Edge restart resets rate-limit windows.
- Multiple Uvicorn workers are not supported.
- Multiple Edge instances are not supported.

Phase 9 must move Session / Access / Job / Queue / Rate Limit state to Redis
and long-term business records to PostgreSQL or an explicitly approved
alternative.

## Phase 9: Persistence + Account / Password

Phase 9 answers:

```text
Who is this person?
What survives an Edge restart?
How can anonymous usage become long-term usage?
```

Recommended storage:

- Redis
- PostgreSQL

Redis responsibilities:

- Session state
- Job state
- Queue
- Rate limit
- short-lived access state

PostgreSQL responsibilities:

- User
- Account
- Invitation records
- UserProfile metadata
- long-term business data

Do not put all long-term business data in Redis merely for convenience.

### Account Model

```text
User
  user_id
  created_at
  updated_at
  status

Account
  account_id
  user_id
  username
  password_hash
  created_at
  last_login_at
  status
```

### Auth API

Phase 9 should plan at least:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

Username and password are enough for the first version. OAuth, SMS codes, and
third-party login should not be included unless explicitly approved later.

### Password Storage

Passwords must never be stored in plaintext or with weak hashes. Use a mature
password hashing method such as Argon2id or bcrypt.

Forbidden:

- plaintext
- MD5
- SHA1
- raw SHA256(password)

Passwords must not appear in logs.

### Anonymous to Registered Migration

Important product path:

```text
anonymous experience
  -> current valid Session
  -> register
  -> create User + Account
  -> attach current Session to user_id
```

Do not force users to restart the conversation after registration. Do not
rename `session_id` to `user_id`.

### Persistence

Phase 7 uses an in-memory SessionRegistry. Phase 9 moves Session / Job / Queue
state to Redis so Edge restart recovery and future multi-worker deployments can
work.

Phase 9 completion state:

> The system can answer who the user is and has persistent account plus
> session/job infrastructure. Long-term UserProfile intelligence is still Phase
> 10.

## Phase 10: Long-Term UserProfile + Account Security

Phase 10 answers:

```text
What does the system remember about this User over time?
How are these sensitive long-term data protected?
```

### Profile Builder

Core flow:

```text
Current Turn
+ Speech Evidence
+ Vision Evidence
+ Emotion
+ Old Profile
  -> Profile Extractor
  -> Candidate facts / observations
  -> Profile Updater
  -> Persistent UserProfile
  -> Next LLM Turn
```

Profile evidence can come from:

- text
- speech emotion
- vision emotion
- multimodal alignment
- dominant emotion
- recent session memory
- RAG route

### Stable vs Dynamic Profile

Stable Profile examples:

- preferred_name
- age_range
- living_situation
- interests
- preferred_topics
- communication_style
- preferred_avatar
- daily_habits
- important_people

Dynamic Profile examples:

- recent_topics
- recent_concerns
- recent_emotion_trend
- interaction_frequency
- recent_support_needs
- last_interaction_at

Do not put everything into one free-text summary.

### Source and Confidence

Profile facts must keep source and confidence.

Example:

```text
fact: interest = 象棋
source: explicit_user_statement
confidence: high
```

Emotion inferences from speech or vision should be treated as recent
observations. They must not become permanent medical diagnosis labels from a
single turn.

### Profile Persistence and Prompt Use

UserProfile binds to `user_id`, not `session_id`.

Prompt architecture:

```text
Base System Prompt
+ Long-term User Profile
+ Relevant User Memory
+ Recent Session Context
+ RAG Context
+ Current Turn
```

Do not inject the full database profile into every LLM turn. Select relevant
fields to reduce tokens, privacy exposure, and irrelevant conditioning.

### Account Security

Because Phase 9 introduces accounts and passwords, Phase 10 must complete a
systematic authentication and authorization review:

- login rate limit
- failed login throttling
- temporary lockout
- username enumeration protection
- session fixation protection
- CSRF review
- XSS review
- authorization review
- password log review
- cookie security
- logout invalidation
- sensitive profile protection

Login failure messages should avoid username enumeration. Use a unified message
such as:

```text
用户名或密码错误
```

### Session Fixation

When an anonymous session becomes a logged-in registered session, regenerate the
authentication credential. Do not upgrade a pre-login anonymous credential into
a high-privilege logged-in credential unchanged.

### CSRF and XSS

Cookie-based authentication requires a CSRF threat review for state-changing
operations such as profile update, password change, logout, account delete, and
data delete.

User content such as nicknames, profile text, chat content, and memory must not
be inserted with unsafe `innerHTML`.

### Sensitive Profile Data

Potential sensitive data includes:

- emotion changes
- family relationships
- daily habits
- support needs
- explicitly shared personal information

Phase 10 must enforce user-level authorization, minimize storage, avoid logging
full profiles, and avoid public debug endpoints that return profile data.

Phase 10 acceptance must include:

- Anonymous A / B isolation
- Registered A / B isolation
- Session isolation
- Chat isolation
- Media isolation
- Profile isolation
- Account isolation
- Invitation gate
- Queue isolation
- Rate limit
- Login / logout
- Restart recovery
- cross-session Profile usage
- GPU offline behavior
- tunnel reconnect behavior
