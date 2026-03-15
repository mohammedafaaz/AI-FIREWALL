# Shell — Enterprise AI Firewall

> A production-grade security middleware layer that intercepts every message to and from an enterprise AI assistant — blocking prompt injections, obfuscated attacks, PII leaks, behavioral manipulation, and AI-driven fraud before they cause damage.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+ + Flask + Flask-JWT-Extended + Flask-CORS |
| Frontend | Vanilla HTML + CSS (Apple Liquid Glass UI) + Vanilla JavaScript |
| Charts | Chart.js (CDN) |
| AI / LLM | Bytez API (Qwen/Qwen3-4B) |
| Security modules | Python standard library only — `re`, `unicodedata`, `base64` |
| PDF scanning | PyMuPDF |
| Auth | JWT + bcrypt + RBAC (admin / hr / employee) |
| Database | SQLite (zero config, embedded) |

**No ML models. No spaCy. No sentence-transformers. No GPU required.**
Every security module runs on Python built-ins — zero external dependencies for the pipeline itself.

---

## Prerequisites

- Python 3.10+
- pip
- A Bytez API key — get one free at https://bytez.com

---

## Setup

### Step 1 — Install dependencies

```bash
pip install flask flask-jwt-extended flask-cors bcrypt requests pymupdf
```

Or using requirements.txt:

```bash
pip install -r requirements.txt
```

### Step 2 — Configure your API key

Open `config.py` and set:

```python
BYTEZ_API_KEY  = 'your-bytez-api-key-here'
BYTEZ_MODEL    = 'Qwen/Qwen3-4B'
JWT_SECRET_KEY = 'any-long-random-string-you-choose'
DATABASE_PATH  = 'database/firewall.db'
```

### Step 3 — Initialize the database

```bash
python database/init_db.py
python database/seed.py
```

### Step 4 — Start the server

```bash
python app.py
```

Open: http://localhost:5000

---

## Demo Credentials

| Role | Username | Password | Access |
|---|---|---|---|
| Admin | `admin` | `admin123` | All pages, all approvals, dashboard |
| HR Manager | `hr_manager` | `hr123` | Own events + delegated actions |
| Employee | `developer` | `dev123` | Own chat + own events only |

---

## The 8-Step Security Pipeline

Every chat message passes through all 8 stages in sequence:

```
User message
    |
    v
+----------------------------------------------------------+
|  INPUT INSPECTION                                        |
|                                                          |
|  Step 1 -- Shadow Prompt Reveal                          |
|            Strips zero-width chars, homoglyphs, Base64,  |
|            HTML comments, RTL overrides                  |
|            -> Sanitises only, does not block             |
|                                                          |
|  Step 2 -- Token Smuggling Detection                     |
|            Detects leet (1gnor3), punct-split (by-pass), |
|            token-split (ign ore), reversed keywords      |
|            -> Hard blocks if injection keyword revealed  |
|                                                          |
|  Step 3 -- Prompt Injection Detection                    |
|            Jailbreaks, persona override, authority       |
|            impersonation, instruction replacement        |
|            -> Hard blocks                                |
|                                                          |
|  Step 4 -- DLP Input Scan                                |
|            Masks SSN, credit cards, emails, phones       |
|            before the AI ever sees them                  |
|            -> Redacts only, does not block               |
+----------------------------------------------------------+
    |
    v
+----------------------------------------------------------+
|  Step 5 -- AI Call                                       |
|            Sanitised, masked prompt sent to LLM          |
+----------------------------------------------------------+
    |
    v
+----------------------------------------------------------+
|  OUTPUT INSPECTION                                       |
|                                                          |
|  Step 6 -- Behavior Monitor                              |
|            Scans AI response for private IPs,            |
|            credentials, stack traces, API keys           |
|            -> Hard blocks if critical secret found       |
|                                                          |
|  Step 7 -- DLP Output Scan                               |
|            Masks PII from AI response before user sees   |
|            -> Redacts only, does not block               |
|                                                          |
|  Step 8 -- Action Approval                               |
|            Catches DROP TABLE, wire transfers, rm -rf,   |
|            mass deletes in AI response                   |
|            -> Hard blocks HIGH risk, queues for review   |
+----------------------------------------------------------+
    |
    v
Safe response delivered to user
```

**Mutation Replay** fires asynchronously in a background thread after any block from any module — generates semantic variants of the blocked attack for the pattern library.

---

## Security Modules

| # | Module | File | Catches | Action |
|---|---|---|---|---|
| 1 | Shadow Prompt Reveal | `modules/shadow_prompt.py` | Zero-width chars, homoglyphs, Base64, HTML comments, RTL overrides | Sanitize only |
| 2 | Token Smuggling | `modules/token_smuggling.py` | Leet, punct-split, token-split, unicode spaces, reversed keywords | Hard block |
| 3 | Prompt Injection | `modules/prompt_injection.py` | Jailbreaks, persona override, authority impersonation | Hard block |
| 4 | DLP Input | `modules/dlp.py` | SSN, credit cards, emails, phones — in user message | Redact only |
| 5 | AI Call | `utils.py` | — | — |
| 6 | Behavior Monitor | `modules/behavior_monitor.py` | Private IPs, credentials, stack traces, API keys — in AI response | Hard block |
| 7 | DLP Output | `modules/dlp.py` | Same PII — in AI response | Redact only |
| 8 | Action Approval | `modules/action_approval.py` | DROP TABLE, wire transfers, rm -rf, mass deletes — in AI response | Hard block + queue |
| — | Mutation Replay | `modules/mutation_replay.py` | Generates variants of any blocked attack | Async, no block |

---

## DLP Architecture — Why No External API

All PII detection runs entirely on-premise using regex pattern matching. No user data is ever sent to an external API for analysis.

The pipeline design guarantees this: DLP Input (Step 4) masks all PII **before** the prompt reaches the AI call (Step 5). The LLM only ever receives already-sanitised text and has no visibility into what was redacted.

This satisfies GDPR, HIPAA, DPDP Act, and PCI-DSS requirements for data minimisation at the AI boundary.

---

## Role-Based Access Control

| Feature | Admin | HR | Employee |
|---|---|---|---|
| View all events on dashboard | Yes | No | No |
| View own events only | Yes | Yes | Yes |
| Approve / Reject actions | Yes | If delegated | No |
| Delegate to HR | Yes | No | No |
| Threat Replay | Yes | Yes (own events) | No |
| Chat | Yes | Yes | Yes |

---

## Threat Replay

Every hard block from any module is recorded with full metadata. The Threat Replay page animates the 8-step pipeline and shows exactly which step blocked the request, the detection score, and the reason.

Access: Dashboard → click **Replay** on any blocked row, or navigate to `/replay.html`.

The `?id=` URL param from the dashboard auto-selects and auto-plays the correct event. The page loads up to 50 blocked-only events via the dedicated `/api/replay/events` endpoint.

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | None | Authenticate, get JWT token |
| GET | `/api/health` | None | Health check |
| POST | `/api/chat/send` | JWT | Send message through full 8-step pipeline |
| GET | `/api/dashboard/stats` | JWT | All dashboard data — stats, charts, recent events |
| GET | `/api/replay/events` | JWT | Blocked-only events for Threat Replay (up to 50) |
| POST | `/api/scan/prompt` | JWT | Manual prompt injection scan |
| POST | `/api/dlp/scan` | JWT | Manual DLP scan |
| POST | `/api/shadow/scan-text` | JWT | Scan text for shadow prompts |
| POST | `/api/shadow/scan-pdf` | JWT | Scan uploaded PDF |
| POST | `/api/scan/token-smuggling` | JWT | Manual token smuggling scan |
| GET | `/api/actions/queue` | JWT Admin/HR | Get action approval queue |
| POST | `/api/actions/approve/<id>` | JWT Admin/HR | Approve a queued action |
| POST | `/api/actions/reject/<id>` | JWT Admin/HR | Reject a queued action |
| POST | `/api/actions/delegate/<id>` | JWT Admin | Delegate action to HR |

---

## Project Structure

```
ai_firewall/
├── app.py                        # Flask app — all routes
├── config.py                     # API keys, JWT secret, DB path
├── utils.py                      # call_llm() shared function
├── requirements.txt
├── README.md
├── TEST_PROMPTS.txt              # Full test scenarios for all modules
├── test_behavior_monitor.py      # Direct unit test for Behavior Monitor
├── database/
│   ├── init_db.py                # Creates SQLite tables
│   ├── seed.py                   # Demo users
│   └── models.py                 # All DB query helpers
├── modules/
│   ├── shadow_prompt.py          # Step 1
│   ├── token_smuggling.py        # Step 2
│   ├── prompt_injection.py       # Step 3
│   ├── dlp.py                    # Steps 4 and 7
│   ├── behavior_monitor.py       # Step 6
│   ├── action_approval.py        # Step 8
│   └── mutation_replay.py        # Background async
├── middleware/
│   ├── interceptor.py            # 8-step pipeline orchestrator
│   └── auth.py                   # JWT validation middleware
└── frontend/
    ├── index.html                # Login page
    ├── dashboard.html            # Threat dashboard
    ├── chat.html                 # AI chat with firewall
    ├── replay.html               # Threat Replay animation
    ├── approvals.html            # Action approval queue
    ├── css/
    │   ├── glass.css             # Apple Liquid Glass design system
    │   └── animations.css        # Keyframe animations
    └── js/
        ├── api.js                # All fetch calls to Flask backend
        ├── dashboard.js          # Chart.js + live feed
        ├── chat.js               # Chat interface + firewall handler
        └── shadow.js             # Shadow prompt highlight renderer
```

---

## Database Schema

| Table | Purpose |
|---|---|
| `users` | Auth, roles, departments |
| `prompt_events` | All pipeline events — module, score, blocked, timestamp |
| `session_messages` | Conversation history per user |
| `action_queue` | Pending high-risk actions awaiting review |

---

## Notes

- **Zero ML dependency** — all 7 security modules use only Python's standard library. No model downloads, no GPU.
- **Single LLM boundary** — the only place data leaves your server is the AI call in Step 5, after DLP has already masked all PII.
- **Graceful fallback** — if the LLM API is unavailable, modules fall back to regex-only mode and the app continues running.
- **Async replay** — Mutation Replay runs in a background thread and does not add latency to chat responses.
- **SQL injection safe** — all queries use parameterized statements.
- **JWT expiry** — tokens expire after 8 hours.
- **Dashboard** — auto-refreshes every 10 seconds.
- **Approvals** — auto-refreshes every 15 seconds.
- **Threat Replay** — loads up to 50 blocked events via dedicated `/api/replay/events` endpoint.

---

## Bugs Fixed

| Bug | File | Root Cause | Fix |
|---|---|---|---|
| BEHAVIOR never hard blocked | `behavior_monitor.py` | Issues returned without `severity` field. Interceptor checked `severity == critical` — always `None`. | Added `severity: critical` to all detected issues. |
| ACTION never hard blocked | `interceptor.py` | Action approval returns `risk_level = HIGH`. Interceptor checked `risk_level == critical` — never matched. | Changed check to `risk_level in (HIGH, critical)`. |
| Threat Replay missed non-injection events | `replay.html` + `app.py` + `models.py` | Replay loaded from `/api/dashboard/stats` (20 mixed events). After filtering blocked-only, older events were cut. `?id=` from dashboard pointed to events outside the window. | Added `/api/replay/events` returning 50 blocked-only events sorted newest first. |