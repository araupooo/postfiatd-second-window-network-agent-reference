# Agent Surface Probes

## Method

[MEASURED] Six unauthenticated, read-only probes of
`https://tasknode.postfiat.org/`, run 2026-11-25 17:16:21–17:16:35 UTC
(2 s apart, 6 requests total). No session, no credentials, no user
identity, no signed requests. Script:
`scripts/agent_surface_probe.py --live`; replay with `--replay`.
Raw results (status, headers with `set-cookie` redacted, 300-char body
prefix, full-body SHA-256) are vendored in
`data/agent_surface_raw.json`; verdicts in
`data/agent_surface_summary.json`.

Privacy: only status codes, headers, body prefixes, and body hashes
are stored — no full response bodies. The `/api/tasks` response was
additionally inspected once at probe time for identifiers: its lists
are all empty, `walletAddress` is null, `accountId` is an empty string.
A naive `r[0-9A-Za-z]{24,34}` scan of that body returns 5 matches, all
of which are camelCase JSON keys (`requiresActivePftlWalletSync`,
etc.), not addresses; there are 0 `0x`-style addresses and 0 email
addresses in the body. The pack-wide identifier grep (see
`docs/REPRODUCTION.md`) confirms no per-user record anywhere in the
pack.

## Results

| Probe | Request | Status | Verdict |
|---|---|---|---|
| P-01 | `GET /` | 200 | Public HTML shell (landing page, expected) |
| P-02 | `GET /robots.txt` | 404 | Not found: `{"ok":false,"error":"static_asset_not_found","path":"/robots.txt"}` |
| P-03 | `GET /api` | 200 | SPA fallback — body byte-identical to `/` (same SHA-256) |
| P-04 | `GET /api/tasks` | 200 | Unauthenticated JSON read (finding) |
| P-05 | `POST /api/tasks` `{}` | 405 | Method not allowed: `tasks_method_not_allowed`, `allowedMethods: ["GET"]` |
| P-06 | `POST /api/tasks` `text/plain` | 405 | Same 405 as P-05 (method rejected before content negotiation) |

Counts: 6 probes, 0 auth-required (401/403), 1 unauthenticated JSON
read, 0 unexpected 2xx, 0 rate-limited (429), 0 transport errors.

## What the unauthenticated `/api/tasks` response discloses

[MEASURED] `GET /api/tasks` returns HTTP 200 with a JSON document
(1,970 bytes) describing platform configuration and policy for an
anonymous caller:

- Feature flags: `personalRequestEnabled` true,
  `networkRequestEnabled` false, `alphaRequestEnabled` false;
  `dailyRewardCap` 8.
- Request/sync state: `requests.items` empty, `sync.status`
  `wallet_required`, `requestCount` 0, `walletAddress` null;
  `outstanding`, `verification`, `refused`, `rewarded` all empty.
- Network-task policy (`networkTasks`, schema
  `pf.task_node.network_task_eligibility.v1`): manual requests create
  personal proposals only (`canRequestManually` false); routing needs
  a signed-in account, a linked PFT wallet, and a network-task
  operating badge (`requiresSignedInAccount`,
  `requiresLinkedPftWallet`, `requiresNetworkTaskOperatingBadge` all
  true); capacity is consumed by outstanding or pending network tasks
  until terminal state; personal tasks do not block network tasks.
  Status `sign_in_required`, one gate (`account`, `action_required`).
- `reinstatement` null.

[MEASURED] No per-user record is present in the anonymous response
(all lists empty, wallet null, account empty). The disclosure is of
configuration and policy shape, not of user data — for an anonymous
caller. Whether the same route returns per-wallet records when called
with a session is [UNSUPPORTED] here: authenticated endpoints were
never probed, by design.

## What was NOT observed

- [MEASURED] No 401 or 403 on any probed route. Write methods are
  rejected at routing (405 + `Allow: GET`), not by an authentication
  layer — the route table, not an auth check, is what stops an
  unauthenticated POST.
- [MEASURED] No 415: the malformed-content-type probe (P-06) received
  the same 405 as the well-formed one, so content negotiation is never
  reached for POST on this route.
- [MEASURED] No rate limiting: no 429 in 6 probes, and no
  `RateLimit-*` or `Retry-After` header on any response. Rate-limit
  thresholds are [UNSUPPORTED]: establishing them would require abusive
  request volumes, which were not attempted.
- [MEASURED] Response headers on all probes: `cache-control: no-store`,
  `x-frame-options: DENY`, `x-content-type-options: nosniff`,
  `referrer-policy: strict-origin-when-cross-origin`,
  `permissions-policy: camera=(), microphone=(), geolocation=(),
  payment=()`, a restrictive `content-security-policy`, `server:
  Fly/9bb2ac9a88 (2026-11-23)`. The security-header posture is
  well-formed; the gap is authorization, not transport headers.

## Failure modes observed

- F-01 Unauthenticated read of a nominally account-scoped route
  (`GET /api/tasks` → 200 JSON). Recovery: none needed by the caller;
  the fix is server-side (see `docs/REMEDIATION.md` R-01).
- F-02 Write rejected at routing, not at auth (405, not 401/403).
  A future route added without the same method table would have no
  auth backstop (R-02).
- F-03 `/robots.txt` absent (404 JSON error). Crawlers and scanners
  receive a JSON error instead of a policy file (R-04).
- F-04 SPA fallback on `/api` (200 HTML identical to `/`): unknown
  GET paths render the app shell instead of a 404, which can mask
  routing mistakes (R-05).
