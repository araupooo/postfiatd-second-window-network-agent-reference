# Network Measurements — Second Window

## Method

[MEASURED] All figures in this document come from
`scripts/measure_window.py --live`, run 2026-11-25 17:18–17:21 UTC
(122 JSON-RPC requests to `https://rpc.testnet.postfiat.org`, 0.25 s
apart, bounded retries on 429/5xx; zero 429s observed). Raw headers
are vendored in `data/window_raw.json`; derived statistics in
`data/window_summary.json`. Replay with
`python3 scripts/measure_window.py --replay` (no network).

Window definition: the latest validated ledger at fetch start was
sequence 8361280. Sampled headers were taken at 600-ledger steps
backwards (49 samples, ~30 min apart at the observed cadence) plus two
dense bursts of 12 consecutive headers (window start and end). The
true span is computed from the headers' own `close_time` values, never
assumed: 2026-11-24 17:06:22 UTC → 2026-11-25 17:18:03 UTC, 87,101 s
(24.19 h), 28,800 ledgers, 71 sampled headers.

## Results

### Ledger close cadence

[MEASURED] Segment means (per ~30 min segment, close-time delta /
sequence delta): overall mean 3.0243 s, median 3.0183 s, minimum
3.0150 s, maximum 3.0650 s. The slowest segment exceeds the overall
mean by 0.0407 s per ledger; over 600 ledgers that bounds any single
slowdown in that segment to ~24 s — no segment implies a halt longer
than ~24 s anywhere in the window.

[MEASURED] Dense-burst per-ledger close-time steps (n=22): mean
2.818 s, median 1 s, minimum 1 s, maximum 8 s, p95 8.0 s. Histogram:
16 intervals of 1 s, 2 of 7 s, 4 of 8 s. Close-time resolution reported
by every sampled header is 10 s.

Interpretation (measured pattern, not assumption): reported close
times cluster 3–4 ledgers per 10 s bucket — 1 s steps inside a bucket
(e.g. ...660, 661, 662, 663) and 7–8 s jumps between buckets (663 →
670). Per-ledger close-time differences are therefore bucket artifacts
of the 10 s resolution, and the segment means above — not the burst
median of 1 s — are the reliable cadence measure. The 10 s resolution
is the finest of the possible resolutions pinned in
`src/xrpld/consensus/LedgerTiming.h:35-44` (10/20/30/60/90/120 s,
default 30 s).

### Agreement and missed ledgers

[MEASURED] At fetch time `server_info` reported `last_close.proposers`
25 and `validation_quorum` 17; `server_state` full; 21 peers; build
1.0.9; `complete_ledgers` 8300054–8361171 (8361282 by the end of the
fetch). No sequence gaps were observed among the 71 sampled headers.

[UNSUPPORTED] A true per-validator agreement rate and a counted
missed-ledger total cannot be established from the public RPC: it
exposes no per-validator validation feed. What the window supports is
two indirect signals, both reported in `data/window_summary.json`:
(a) 0 of 22 dense-burst intervals exceed 3x the segment-median
cadence (9.05 s); (b) the window consistency check —
span / segment-median cadence = 28,857 expected ledgers vs 28,800
actual, a 57.3-ledger (0.20%) delta that reflects cadence variation
across segments (segment means vary ±0.8%), not a counted miss.
Neither signal is a missed-ledger count, and this reference does not
present one.

### Fees and burn

[MEASURED] `fee` at fetch: base fee 10 drops, median fee 5000 drops,
minimum fee 10 drops, open-ledger fee 10 drops; reference level 256,
median level 128000; `current_ledger_size` 4, `current_queue_size` 0,
`max_queue_size` 2000.

[MEASURED] `total_coins` fell from 99,999,999,966,356,892 drops to
99,999,999,966,258,456 drops over the window: 98,436 drops burned =
0.098436 PFT in 24.19 h (≈0.00407 PFT/hour at this traffic level).

### Transactions

[MEASURED] 49 sampled ledgers carried 23 transactions total: mean
0.47, median 0, maximum 5 per ledger. The testnet was effectively
idle during this window; fee and burn figures are low-traffic figures,
not stress figures.

### Validator topology (re-derivation)

[MEASURED] Live validator list (fetched 2026-11-26, sequence 31):
25 validators, 25 unique validation public keys, 0 duplicates, a
manifest present for every entry. Effective Ripple-epoch timestamp
848866298; expiration 892052157. The blob field `effective` is a
timestamp, not a size — the effective UNL size is the validator count
(25).

[MEASURED] Quorum re-derivation from the pinned source
(`ValidatorList.cpp:1933-1934`,
`max(ceil(effective*0.67), ceil(unl*0.6))`): at UNL 25 the quorum is
17 under the 67% rule vs 20 under the upstream 80% rule (delta 3).
The live `validation_quorum` of 17 reported by `server_info`
corroborates the 67% rule exactly. The in-code comment at lines
1902–1905 states the fork uses 67% for devnet/testnet and that
mainnet "should be reverted to 80%".

[MEASURED] Theorem 8 overlap (arXiv:1802.07242, as quoted in the same
comment): the two UNLs of 25 may differ by at most 8 validators in
total and stay fork-safe under 67% (4 under 80%); with the difference
split evenly, the minimum fork-safe pairwise overlap is 21 of 25
under 67% (23 under 80%). Amendment threshold is a second, distinct
67%: `postFixAmendmentMajorityCalcThreshold` is 67/100
(`SystemParameters.h:85`), held for two weeks
(`defaultAmendmentMajorityTime`, same file).

### Overlay and peer parameters (source pins, not live measurements)

The following are pinned from the postfiatd source at commit
`0085a1ff885d6a446369cf73a4430f75af22be55``, verified by `grep -n` on a local clone and cross-checked
against GitHub API blob SHAs (see `data/postfiatd_pin.json`); they are
specification-derived, not measured live:

- `src/xrpld/overlay/detail/Tuning.h:32,36,58`: `convergedLedgerLimit`
  24, `divergedLedgerLimit` 128, `checkIdlePeers` 4 s.
- `src/xrpld/peerfinder/detail/Tuning.h:52,59,63`: `outPercent` 15,
  `minOutCount` 10, `defaultMaxPeers` 21. The live node reported 21
  peers at fetch time, equal to `defaultMaxPeers`.
- `src/xrpld/app/misc/Manifest.h:276-289`: untrusted-manifest bound
  1000 keys, evict-oldest when full, listed keys never bounded.

[SIMULATED] No consensus-message-flow volumes are claimed: message
counts per ledger are not observable through the public RPC. The
overlay parameters above are the only flow evidence in this reference.
