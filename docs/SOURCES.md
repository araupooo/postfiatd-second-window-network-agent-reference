# Pinned Sources

Every source this reference rests on, with the access date and the
exact pin (commit, file:line, or URL). Line numbers were verified with
`grep -n` on a local clone of postfiatd at the pinned commit — never
from a raw-file web fetch. Blob SHA-256s are in
`data/postfiatd_pin.json`; every blob SHA was confirmed against the
GitHub API at the pinned commit (verified in two batches because the
unauthenticated 60/hour API rate limit was exhausted mid-verification;
all six match the local clone).

## postfiatd `0085a1ff885d6a446369cf73a4430f75af22be55` (2026-10-10, release 1.0.9)

Repository: https://github.com/postfiatorg/postfiatd — HEAD verified by
local clone (`git rev-parse HEAD`) and by the GitHub API
(`GET /repos/postfiatorg/postfiatd/commits/main`) before the rate
limit was hit. Merge PR #50, "hotfix/upstream-hardening-1.0.9".

| # | Path | Lines | What it pins |
|---|---|---|---|
| L1 | `src/xrpld/app/misc/detail/ValidatorList.cpp` | 1902–1905 | 67% quorum comment (devnet/testnet; mainnet "should be reverted to 80%") |
| L2 | `src/xrpld/app/misc/detail/ValidatorList.cpp` | 1933–1934 | Quorum formula `max(ceil(effective*0.67), ceil(unl*0.6))` |
| L3 | `src/xrpld/app/misc/detail/ValidatorList.cpp` | 1845–1897 | `--quorum` override warning; quorum disabled when publishers unavailable |
| L4 | `src/xrpld/app/misc/detail/ValidatorList.cpp` | 2109 | `quorum_ = calculateQuorum(...)` |
| L5 | `src/xrpld/consensus/LedgerTiming.h` | 35–44 | Close-time resolutions 10/20/30/60/90/120 s; default 30 s |
| L6 | `include/xrpl/protocol/SystemParameters.h` | 85 | Amendment threshold 67/100 (`postFixAmendmentMajorityCalcThreshold`) |
| L7 | `include/xrpl/protocol/SystemParameters.h` | 87–88 | Amendment majority hold: two weeks |
| L8 | `src/xrpld/app/misc/Manifest.h` | 276–289 | Untrusted-manifest bound 1000 keys; evict-oldest; listed keys never bounded |
| L9 | `src/xrpld/overlay/detail/Tuning.h` | 32, 36, 58 | `convergedLedgerLimit` 24; `divergedLedgerLimit` 128; `checkIdlePeers` 4 s |
| L10 | `src/xrpld/peerfinder/detail/Tuning.h` | 52, 59, 63 | `outPercent` 15; `minOutCount` 10; `defaultMaxPeers` 21 |
| L11 | `docs/NodeSetup.md` | 115, 126, 241 | Canonical testnet list URL; foundation RPC `https://rpc.testnet.postfiat.org` |
| L12 | `docs/NodeSetup.md` | 169–170, 440 | Explorer validator pages: `https://explorer.testnet.postfiat.org/network/validators` |

## Live network sources (accessed 2026-11-25/26)

| # | URL | Accessed | What it pins |
|---|---|---|---|
| N1 | https://rpc.testnet.postfiat.org | 2026-11-25 17:18–17:21 UTC | Window ledgers 8332480–8361280; build 1.0.9; network_id 2025; quorum 17; proposers 25 |
| N2 | https://postfiat.org/testnet_vl.json | 2026-11-26 | Validator list sequence 31, 25 validators (vendored as `data/testnet_vl.json`) |
| N3 | https://explorer.testnet.postfiat.org/ | 2026-11-25 | Reachability only (HTTP 200, JS app); no data taken — its `/api/v2/*` paths return the app shell |
| N4 | https://tasknode.postfiat.org/ | 2026-11-25 17:16 UTC | Agent-surface probes P-01–P-06 (unauthenticated, read-only) |

## External references

| # | Source | What it pins |
|---|---|---|
| E1 | arXiv:1802.07242, "Analysis of the XRP Ledger Consensus Protocol", Theorem 8 | Fork-safety condition `Oi,j > nj/2 + ni − qi + ti,j`, as quoted in the `ValidatorList.cpp` comment (L1) |
| E2 | https://postfiat.org/validator-setup/ | Foundation RPC node runs the current release; peer port 2559; validator setup (accessed 2026-11-25) |

## Method reference only (results NOT reused)

The prior window's reference,
https://github.com/araupooo/postfiat-network-architecture-agent-integration-reference
(README + `docs/SOURCES.md`, read 2026-11-25), was consulted only for
its endpoint list and method (RPC methods, validator-list URL, quorum
re-derivation approach). No number from it appears in this reference:
the window, the validator list, the probes, and the source pins were
all re-captured fresh. Note: the repository name given in the
assignment brief for the prior pack returns GitHub API 404; the
prior pack above (created 2026-11-13, verified live) is the one
that was actually read.
