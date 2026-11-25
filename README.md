# PFTL Network and Agent Reference — Second Measurement Window

A second, fresh measurement window for the PFTL network (the postfiatd
fork of rippled) and the public agent work-request surface. All numbers
in this reference were measured 2026-11-24 → 2026-11-25 (ledger
sequences 8332480–8361280, 24.19 hours). Nothing is reused from any
earlier window.

Every substantive claim is labelled [MEASURED] (observed in this
window, with the script and raw output that produced it), [SIMULATED]
(produced by a local model or drill, not observed on the live network),
or [UNSUPPORTED] (cannot be established from the public sources used
here). Every claim is mapped to its evidence in `docs/CLAIMS.md`.

## What this reference measures

[MEASURED] Ledger close cadence over 24.19 h: segment mean 3.024 s,
median 3.018 s, range 3.015–3.065 s across 48 half-hour segments; no
segment implies a halt longer than ~24 s; 0 dense-burst intervals above
3x the segment-median cadence.

[MEASURED] Validator topology: 25 validators on the live list, 0
duplicates, quorum 17 under the 67% rule (20 under the upstream 80%
rule), minimum fork-safe pairwise UNL overlap 21 of 25 (23 under 80%).

[MEASURED] Fees and burn: base fee 10 drops, median fee 5000 drops;
0.098436 PFT burned over the window; 23 transactions in 49 sampled
ledgers (mean 0.47 per ledger).

[MEASURED] Agent surface: `GET /api/tasks` returns a JSON policy/config
document to an unauthenticated caller (all record lists empty, wallet
null); write methods are rejected at routing with 405, not by an auth
layer; no 401/403, no 415, and no rate-limit signal was observed on any
probed route.

## How to run it

```sh
bash reproduce.sh
```

Python 3.9+ standard library only; no network at run time — the
scripts replay the vendored `data/` captures. Each script prints
PASS/FAIL and writes its unedited stdout to `outputs/<script>.log`.
The runner exits non-zero if any script fails and prints a final
`ALL CHECKS PASSED` / `FAILED` summary, then `verify_digests.sh`
checks the SHA-256 manifest.

To re-capture a fresh live window instead of replaying the vendored
one, see `docs/REPRODUCTION.md` (commands: `measure_window.py --live`,
`agent_surface_probe.py --live`).

## File map

| Path | Contents |
|---|---|
| `scripts/rpc_client.py` | Shared read-only JSON-RPC client (retries, backoff) |
| `scripts/measure_window.py` | M-01: ledger-window measurement (live + replay) |
| `scripts/validator_topology.py` | M-02: validator-list quorum/overlap re-derivation |
| `scripts/agent_surface_probe.py` | M-03: unauthenticated public-surface probes |
| `scripts/recovery_drills.py` | M-04: retry / resume / digest-mismatch drills (simulated) |
| `scripts/run_all.sh` | Runs all four checks, captures unedited logs to `outputs/` |
| `reproduce.sh` | `run_all.sh` + digest verification (the CI command) |
| `verify_digests.sh` | `sha256sum -c SHA256SUMS` |
| `data/testnet_vl.json` | Validator list, fetched 2026-11-26 from postfiat.org |
| `data/window_raw.json` | Raw ledger headers + fee snapshot for the window |
| `data/window_summary.json` | Derived window statistics |
| `data/topology_summary.json` | Derived quorum/overlap figures |
| `data/agent_surface_raw.json` | Probe statuses, headers, body prefixes + SHA-256 |
| `data/agent_surface_summary.json` | Probe verdicts |
| `data/postfiatd_pin.json` | Pinned postfiatd commit + file blob SHA-256s |
| `outputs/` | Unedited logs from the latest `run_all.sh` run (4/4 passed) |
| `docs/NETWORK_MEASUREMENTS.md` | Window method and results |
| `docs/AGENT_SURFACE.md` | Probe method, results, and header evidence |
| `docs/REMEDIATION.md` | Severity-scored remediation guidance |
| `docs/DECISION_MEMO.md` | Primary-source decision memo |
| `docs/CLAIMS.md` | Claim-to-evidence index |
| `docs/SOURCES.md` | Pinned primary sources |
| `docs/REPRODUCTION.md` | Fresh-clone reproduction steps |
| `docs/FAILURE_MODES.md` | Failure-mode catalogue |
| `SHA256SUMS` | SHA-256 of every file in this reference |
| `.github/workflows/ci.yml` | Runs `reproduce.sh` on a clean checkout |

## Pinned sources

- postfiatd at commit `0085a1ff885d6a446369cf73a4430f75af22be55`
  (2026-10-10, release 1.0.9): `src/xrpld/app/misc/detail/ValidatorList.cpp`,
  `src/xrpld/consensus/LedgerTiming.h`, `src/xrpld/app/misc/Manifest.h`,
  `src/xrpld/overlay/detail/Tuning.h`, `src/xrpld/peerfinder/detail/Tuning.h`,
  `include/xrpl/protocol/SystemParameters.h`, `docs/NodeSetup.md`.
  Commit verified by local clone (`git rev-parse HEAD`) and the GitHub
  API; file blob SHAs in `data/postfiatd_pin.json`.
- Live testnet validator list: https://postfiat.org/testnet_vl.json
  (fetched 2026-11-26; sequence 31, 25 validators).
- Live testnet RPC: https://rpc.testnet.postfiat.org (build 1.0.9,
  network_id 2025).
- Live explorer: https://explorer.testnet.postfiat.org/ (JS app; used
  only as a reachability cross-check, not as a data source).
- Live agent surface: https://tasknode.postfiat.org/ (probed 2026-11-25,
  unauthenticated, read-only).

Full source list with file:line pins: `docs/SOURCES.md`.
