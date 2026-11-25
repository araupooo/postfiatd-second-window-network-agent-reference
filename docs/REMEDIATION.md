# Remediation Guidance

Severity scale: HIGH = exploitable or data-exposing now; MEDIUM =
weakens a security boundary or mainnet readiness; LOW = hygiene or
observability; INFO = context, no action required.

## R-01 — HIGH: require authentication for `/api/tasks` (or strip it for anonymous callers)

[MEASURED] `GET /api/tasks` returns HTTP 200 with a JSON policy/config
document to an unauthenticated caller (probe P-04,
`data/agent_surface_raw.json`). The anonymous response currently
carries no per-user records (all lists empty, wallet null), so the
exposure today is configuration and policy shape: feature flags,
`dailyRewardCap` 8, the full network-task eligibility policy and gate
structure. The risk is that the same route is one session-cookie away
from returning per-wallet records — the route does not appear to
enforce authentication at all, so any future field added to this
response is public by default.

Guidance: put an authentication check in front of `/api/*` (return
401 for anonymous callers), or split the route into a public config
endpoint (flags only) and an authenticated state endpoint. Re-probe
after the fix: anonymous `GET /api/tasks` must return 401, and the
authenticated response must be checked to contain only the caller's
own records. Regression test: add the P-04 probe to CI as a live
smoke check (it is currently replay-only).

## R-02 — MEDIUM: enforce authorization at the API layer, not only at routing

[MEASURED] Unauthenticated `POST /api/tasks` is rejected with 405
(`tasks_method_not_allowed`, `allowedMethods: ["GET"]`), not 401/403
(probes P-05/P-06). The method table is doing the work an auth layer
should do. Any future route added without an explicit method table —
or any method added to this route — would have no auth backstop.

Guidance: add auth middleware covering all `/api/*` routes that
returns 401 before routing logic runs, and keep the 405 as a second
layer. Verify with the P-05/P-06 probes after the change (expect 401
for POST without a session).

## R-03 — MEDIUM: track the 67% → 80% quorum revert as a mainnet gate

[MEASURED] postfiatd 1.0.9 still uses a 67% validator-list quorum
(`ValidatorList.cpp:1902-1905`, comment: "for devnet/testnet... For
mainnet, this should be reverted to 80%"), and the live testnet quorum
is 17 of 25 (vs 20 under 80%). The amendment threshold is a second,
distinct 67% (`SystemParameters.h:85`). At the current list size the
67% rule lets two UNLs share as few as 21 of 25 validators and stay
fork-safe, vs 23 under 80%.

Guidance: record the revert as an explicit, checkable mainnet-gate
item (code change + test asserting quorum 20 at UNL 25 + amendment
review), and do not treat testnet fork-safety margins as mainnet
margins. No action is needed on testnet itself.

## R-04 — LOW: publish `/robots.txt` (or return a real 404)

[MEASURED] `GET /robots.txt` returns 404 with a JSON error
(`static_asset_not_found`). Crawlers, scanners, and uptime monitors
get an API-shaped error instead of a crawl policy.

Guidance: serve a minimal `robots.txt` (or a deliberate 404 HTML
page) so automated clients are not left guessing which paths are
public. One-line fix; no security impact beyond tidiness.

## R-05 — LOW: stop serving the app shell for unknown `/api/*` paths

[MEASURED] `GET /api` returns 200 with HTML byte-identical to the
landing page (probe P-03, same SHA-256 as P-01). Unknown API paths
render the SPA shell instead of a 404, which masks routing mistakes
and makes unauthenticated API enumeration return 200s.

Guidance: return JSON 404 for unknown `/api/*` paths (as `/robots.txt`
already does) and reserve the SPA fallback for non-API paths.

## R-06 — LOW: document and signal API rate limits

[MEASURED] No 429 and no `RateLimit-*`/`Retry-After` header appeared
in any probe response. Thresholds are [UNSUPPORTED] (establishing them
would need abusive volumes, not attempted). The RPC side behaved the
same way: 122 requests in ~3.5 minutes drew no 429.

Guidance: publish the limit policy for the public RPC and the task
API, and emit standard `RateLimit-*` headers so legitimate clients
can back off before hitting a limit. Do not rely on clients discovering
limits by tripping them.

## R-07 — LOW: monitor close-time segment means, not per-ledger diffs

[MEASURED] Per-ledger close-time steps in this window are bucket
artifacts of the 10 s resolution (16 of 22 burst intervals are 1 s, 4
are 8 s). A monitor alerting on per-ledger close-time spikes would
page on quantization noise.

Guidance: alert on half-hour segment-mean close time (this window:
3.015–3.065 s) and on any segment implying a halt longer than ~30 s;
treat single-ledger close-time jumps of 7–8 s as normal.

## R-08 — INFO: testnet traffic is near idle; fee/burn figures are not stress figures

[MEASURED] 23 transactions in 49 sampled ledgers (0.47/ledger);
0.098436 PFT burned in 24.19 h. Nothing here validates fee-market or
spam-resistance behavior under load. Any load claim needs a dedicated
load window and is [UNSUPPORTED] from this pack.
