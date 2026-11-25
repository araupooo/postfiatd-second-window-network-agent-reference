# Decision Memo — Second-Window Findings

Primary sources only. Each paragraph below cites the source it rests
on; the full pin list is in `docs/SOURCES.md` and the claim index in
`docs/CLAIMS.md`.

## 1. The network is healthy and idle

Source: `data/window_summary.json` (from `data/window_raw.json`, 71
ledger headers fetched 2026-11-25 17:18–17:21 UTC via
`https://rpc.testnet.postfiat.org`).

Over 24.19 h (sequences 8332480–8361280) the ledger closed every
3.024 s on average (segment medians 3.018 s, worst half-hour segment
3.065 s), with no segment implying a halt longer than ~24 s and no
dense-burst interval above 3x the median cadence. The validator list
holds 25 validators, quorum 17, last-close proposers 25. Traffic is
near idle (0.47 transactions per sampled ledger; 0.098 PFT burned in
the window). Decision: there is no network-health blocker to any
dependent work; equally, there is no load evidence — any claim about
behavior under load is unsupported by this window.

## 2. The 67% quorum is confirmed live and unchanged

Source: postfiatd commit `0085a1ff885d6a446369cf73a4430f75af22be55`,
`src/xrpld/app/misc/detail/ValidatorList.cpp:1902-1905,1933-1934`,
corroborated by live `server_info` (`validation_quorum` 17).

The fork uses a 67% validator-list quorum for devnet/testnet, against
80% upstream, and the code itself says mainnet "should be reverted to
80%". The live quorum (17 of 25) matches the 67% formula exactly, and
the minimum fork-safe pairwise UNL overlap is 21 of 25 (23 under 80%).
Decision: treat the revert as a mainnet gate (R-03), not as a testnet
defect. Testnet fork-safety margins must not be quoted as mainnet
margins.

## 3. The public agent surface discloses config without authentication

Source: `data/agent_surface_raw.json`, probes P-01–P-06, 2026-11-25
17:16 UTC, `https://tasknode.postfiat.org/`.

`GET /api/tasks` answers an unauthenticated caller with HTTP 200 and
a JSON document containing feature flags, the daily reward cap (8),
and the full network-task eligibility policy. No per-user record was
present for an anonymous caller, and no write method succeeded
(`POST` → 405, rejected at routing, not by auth). No 401/403, no 415,
and no rate-limit signal appeared on any probed route. Decision: the
exposure today is configuration, not user data — but the route has no
authentication enforcement, so the fix (R-01: 401 for anonymous
callers, or a public-config/authenticated-state split) should land
before any per-user field is added to that response. The 405-only
write rejection (R-02) should gain an auth layer behind it.

## 4. What this window does NOT establish

- Per-validator agreement rates and a counted missed-ledger total:
  the public RPC exposes no per-validator validation feed
  ([UNSUPPORTED], see `docs/NETWORK_MEASUREMENTS.md`).
- Consensus message-flow volumes: not observable via the public RPC
  ([SIMULATED] parameters only, from pinned source).
- Rate-limit thresholds for the RPC or the task API: not observable
  without abusive request volumes, which were not attempted
  ([UNSUPPORTED]).
- Authenticated-route behavior: authenticated endpoints were never
  probed, by design ([UNSUPPORTED]).

Decision: do not cite this reference for any of the four items above.
A follow-up window that needs them must say so explicitly and use a
different method (validator-side telemetry, or a load harness with an
agreed budget).

## 5. Reproduction

`bash reproduce.sh` replays all four checks from the vendored data and
verifies the SHA-256 manifest with no network access. The CI workflow
(`.github/workflows/ci.yml`) runs the same command on a clean
checkout. Fresh-capture commands are in `docs/REPRODUCTION.md`.
