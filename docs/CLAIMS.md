# Claim-to-Evidence Index

Labels: [MEASURED] observed in the 2026-11-24→25 window or by the
probes, with the script and vendored output that produced it;
[SIMULATED] produced by a local model or drill, not observed live;
[UNSUPPORTED] cannot be established from the public sources used here.
Line numbers are from the vendored files as committed (verify with
`grep -n`); JSON keys are given alongside for stability.

## Measured claims

| # | Claim | Evidence (script → output file:line) | Primary source |
|---|---|---|---|
| C-01 | Window: ledger seq 8332480–8361280, 2026-11-24 17:06:22 UTC → 2026-11-25 17:18:03 UTC, 87,101 s (24.19 h), 28,800 ledgers | `scripts/measure_window.py` → `data/window_summary.json:69,72,76` (`window.*`); raw headers `data/window_raw.json` | `https://rpc.testnet.postfiat.org` (`ledger`, `server_info`), 2026-11-25 17:18–17:21 UTC, 122 requests |
| C-02 | Close cadence: segment mean 3.0243 s, median 3.0183 s, range 3.0150–3.0650 s | `scripts/measure_window.py` → `data/window_summary.json:27` (`close_time_seconds.*`) | Same RPC window as C-01 |
| C-03 | No segment implies a halt longer than ~24 s (max excess 0.0407 s/ledger × 600) | `scripts/measure_window.py` → `data/window_summary.json:27` (segment max 3.0650 vs overall 3.0243) | Same RPC window as C-01 |
| C-04 | Dense-burst close steps: n=22, mean 2.818 s, median 1 s, min 1 s, max 8 s, p95 8.0 s; histogram 16×1 s, 2×7 s, 4×8 s; resolution 10 s | `scripts/measure_window.py` → `data/window_summary.json:23,26` (`close_time_seconds.*`) | Same RPC window as C-01; resolution pinned in `LedgerTiming.h:35-44` |
| C-05 | Last-close proposers 25, validation quorum 17, server_state full, 21 peers, build 1.0.9, network_id 2025 | `scripts/measure_window.py` → `data/window_summary.json:5,9`; `data/window_raw.json` (`server_info_at_fetch`) | `server_info`, same fetch as C-01 |
| C-06 | 0 dense-burst intervals above 3x segment-median cadence; no sequence gaps in 71 sampled headers | `scripts/measure_window.py` → `data/window_summary.json` (`agreement_and_missed.*`) | Same RPC window as C-01 |
| C-07 | Base fee 10 drops, median fee 5000 drops, min/open 10 drops; reference level 256, median level 128000 | `scripts/measure_window.py` → `data/window_summary.json:33` (`fees_and_burn.*`) | `fee` RPC, same fetch as C-01 |
| C-08 | Burn 98,436 drops = 0.098436 PFT over the window | `scripts/measure_window.py` → `data/window_summary.json:35` | `ledger` headers `total_coins`, same fetch as C-01 |
| C-09 | 23 transactions in 49 sampled ledgers (mean 0.47, median 0, max 5) | `scripts/measure_window.py` → `data/window_summary.json:64` (`transactions.*`) | `ledger` with `transactions:true`, same fetch as C-01 |
| C-10 | Validator list sequence 31: 25 validators, 25 unique keys, 0 duplicates, manifest for every entry | `scripts/validator_topology.py` → `data/topology_summary.json:30` (`validator_list.*`); raw `data/testnet_vl.json` | `https://postfiat.org/testnet_vl.json`, fetched 2026-11-26 |
| C-11 | Quorum 17 under the 67% rule vs 20 under the upstream 80% rule at UNL 25 | `scripts/validator_topology.py` → `data/topology_summary.json:8,9` | postfiatd `0085a1ff885d6a446369cf73a4430f75af22be55``, `ValidatorList.cpp:1933-1934`; corroborated by C-05 live quorum 17 |
| C-12 | Minimum fork-safe pairwise UNL overlap 21 of 25 (67%) vs 23 of 25 (80%); max total UNL difference 8 vs 4 | `scripts/validator_topology.py` → `data/topology_summary.json:17,18` | Theorem 8 (arXiv:1802.07242) via `ValidatorList.cpp:1902-1932` comment |
| C-13 | Amendment threshold 67/100, held two weeks | Source pin only | postfiatd `0085a1ff885d6a446369cf73a4430f75af22be55``, `SystemParameters.h:85` + `defaultAmendmentMajorityTime` |
| C-14 | Overlay/peer parameters: convergedLedgerLimit 24, divergedLedgerLimit 128, checkIdlePeers 4 s; outPercent 15, minOutCount 10, defaultMaxPeers 21; untrusted-manifest bound 1000, evict-oldest | Source pin only (verified by `grep -n` on local clone) | postfiatd `0085a1ff885d6a446369cf73a4430f75af22be55``, `overlay/detail/Tuning.h:32,36,58`, `peerfinder/detail/Tuning.h:52,59,63`, `app/misc/Manifest.h:276-289` |
| C-15 | `GET /api/tasks` returns 200 JSON to an unauthenticated caller (flags, dailyRewardCap 8, network-task policy; all record lists empty, wallet null) | `scripts/agent_surface_probe.py` → `data/agent_surface_summary.json:63`; raw `data/agent_surface_raw.json` (P-04) | `https://tasknode.postfiat.org/api/tasks`, probed 2026-11-25 17:16 UTC |
| C-16 | Unauthenticated `POST /api/tasks` rejected with 405 (`tasks_method_not_allowed`, `allowedMethods: ["GET"]`), identically for JSON and text/plain bodies | `scripts/agent_surface_probe.py` → `data/agent_surface_raw.json` (P-05, P-06) | Same probe run as C-15 |
| C-17 | No 401/403, no 415, no 429, no rate-limit headers on any of 6 probes; `GET /api` returns HTML byte-identical to `/`; `GET /robots.txt` → 404 JSON | `scripts/agent_surface_probe.py` → `data/agent_surface_summary.json:2` (`auth_required_count: 0`); raw P-01–P-03 | Same probe run as C-15 |
| C-18 | Response security headers present on all probes (CSP, `X-Frame-Options: DENY`, `nosniff`, `no-store`, restrictive permissions policy) | `scripts/agent_surface_probe.py` → `data/agent_surface_raw.json` (P-01–P-06 `headers`) | Same probe run as C-15 |

## Simulated claims

| # | Claim | Evidence | Primary source |
|---|---|---|---|
| S-01 | Retry-after-failure, resume-after-interruption, and digest-mismatch drills demonstrate the recovery paths | `scripts/recovery_drills.py` (D-01–D-03) → `outputs/recovery_drills.log` | Local simulation against scripted fixtures/temp copies; the retry policy mirrors `scripts/rpc_client.py`. These drills prove the recovery code paths, not live platform behavior. |
| S-02 | Overlay/consensus parameter consequences (e.g. validation propagation within the 3–5 s cadence) are model-derived where stated in `docs/NETWORK_MEASUREMENTS.md` | Pinned source parameters (C-14) | No live message-flow measurement exists in this pack; see U-02. |

## Unsupported claims

| # | Claim | Why it is unsupported here |
|---|---|---|
| U-01 | Per-validator agreement rate over the window | The public RPC exposes no per-validator validation feed. Only indirect signals exist (C-06). |
| U-02 | Consensus message-flow volumes (validations/proposals per ledger) | Not observable through the public RPC; only source-pinned parameters (C-14). |
| U-03 | A counted missed-ledger total for the window | Only the indirect signals in C-06; the 57.3-ledger consistency delta is cadence variation (±0.8% segment means), not a count. |
| U-04 | Rate-limit thresholds for the public RPC or the task API | Establishing them would require abusive request volumes; not attempted. Zero 429s in 122 RPC requests and 6 probes is absence of a signal, not a measured limit. |
| U-05 | Behavior of authenticated task-API routes (per-wallet records, submission, verification) | Authenticated endpoints were never probed, by design. |
| U-06 | Fee-market / spam-resistance behavior under load | The window was near idle (C-09); no load was applied. |
| U-07 | Any claim about mainnet (quorum, thresholds, readiness) | All measurements are testnet (network_id 2025); mainnet does not exist yet and the 67%→80% revert is unexecuted (R-03). |
