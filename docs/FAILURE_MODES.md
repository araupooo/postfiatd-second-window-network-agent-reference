# Failure Modes

Catalogue of failure modes observed or demonstrated in this window.
Severity follows `docs/REMEDIATION.md` (R-01–R-08).

## Network / RPC

- FM-01 — No halt observed: worst half-hour segment mean close time
  3.065 s vs 3.024 s overall; no segment implies a halt longer than
  ~24 s. (Measured, C-03.)
- FM-02 — Close-time quantization: per-ledger close-time steps are
  bucket artifacts of the 10 s resolution (16×1 s, 2×7 s, 4×8 s in the
  bursts). A monitor alerting on single-ledger close-time jumps would
  page on noise. (Measured, C-04; remediation R-07.)
- FM-03 — Missed ledgers are not directly observable: the public RPC
  exposes no per-validator validation feed. Only indirect signals
  exist (0 burst outliers; 0.20% consistency delta). (Unsupported,
  U-01/U-03.)
- FM-04 — Near-idle traffic: 0.47 transactions per sampled ledger.
  Fee/burn figures (0.098 PFT/day) say nothing about load behavior.
  (Measured, C-08/C-09; unsupported U-06.)
- FM-05 — RPC gave zero 429s across 122 requests in ~3.5 minutes, and
  no rate-limit headers. The limit, if any, is undisclosed.
  (Unsupported, U-04; remediation R-06.)

## Agent surface

- FM-06 — Unauthenticated JSON read (`GET /api/tasks` → 200).
  (Measured, C-15; remediation R-01, HIGH.)
- FM-07 — Write rejected at routing, not at auth (405, not 401/403).
  (Measured, C-16; remediation R-02, MEDIUM.)
- FM-08 — SPA fallback on unknown API paths (`GET /api` → 200 HTML
  identical to `/`). (Measured, C-17; remediation R-05, LOW.)
- FM-09 — `/robots.txt` absent (404 JSON error). (Measured, C-17;
  remediation R-04, LOW.)
- FM-10 — No rate-limit signal on any probe (no 429, no headers).
  (Measured, C-17; unsupported U-04; remediation R-06, LOW.)

## Recovery (demonstrated locally, simulated)

- FM-11 — Transient RPC failure (503, timeout) recovered by bounded
  retry with exponential backoff; success on attempt 3 of 4.
  (Drill D-01, `outputs/recovery_drills.log`.)
- FM-12 — Interrupted window capture (6-header gap) repaired by a
  resume pass that fills exactly the missing sequences and verifies
  contiguity. (Drill D-02.)
- FM-13 — Tampered file detected by SHA-256 digest mismatch; the
  original verifies clean. (Drill D-03; `verify_digests.sh` is the
  pack-level form of this check.)
- FM-14 — Stale-window risk: `measure_window.py --live` overwrites the
  vendored window. A `--live` run started but interrupted leaves a
  partial `window_raw.json` only if the process is killed mid-write;
  the script writes the file atomically at the end of the fetch, so an
  interrupted run leaves the previous vendored file intact. (Design
  note; the atomic-write claim is by code inspection of
  `live_fetch()`, which builds the dict in memory and writes once.)

## Source / pinning

- FM-15 — GitHub API unauthenticated rate limit (60/hour, per-IP) was
  exhausted during pin verification, forcing the blob-SHA check into
  two batches. All six file blob SHAs were ultimately confirmed
  against the API and match the local clone exactly. (See
  `data/postfiatd_pin.json`.)
- FM-16 — The prior pack's repository name as given in the assignment
  brief returns GitHub API 404; the actual prior pack
  (`postfiat-network-architecture-agent-integration-reference`,
  created 2026-11-13, verified live) was used for method reference
  instead. No result was reused either way.
