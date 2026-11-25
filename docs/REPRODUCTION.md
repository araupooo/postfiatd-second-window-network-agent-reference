# Reproduction

## Fresh clone (no network needed)

```sh
git clone <this-repo-url>
cd <repo>
bash reproduce.sh
```

Expected output ends with:

```
ALL CHECKS PASSED
REPRODUCE OK
```

`reproduce.sh` runs `scripts/run_all.sh` (all four checks replayed
from the vendored `data/`, logs to `outputs/<script>.log`) and then
`bash verify_digests.sh` (`sha256sum -c SHA256SUMS`). Python 3.9+
standard library only; no third-party packages; no secrets or
credentials.

The CI workflow (`.github/workflows/ci.yml`) runs exactly this command
on `ubuntu-latest` with Python 3.12 on every push and pull request.

## Re-capturing a fresh live window

The vendored data is the 2026-11-24→25 window. To capture a new one:

```sh
python3 scripts/measure_window.py --live     # ~4 min, ~122 RPC requests
python3 scripts/agent_surface_probe.py --live # 6 requests, ~12 s
python3 scripts/validator_topology.py        # offline, re-reads data/testnet_vl.json
bash scripts/run_all.sh                      # replay + logs
bash verify_digests.sh
```

Note: `--live` overwrites `data/window_raw.json`,
`data/window_summary.json`, `data/agent_surface_raw.json`, and
`data/agent_surface_summary.json`. Re-fetch the validator list first
if a new list is wanted:

```sh
curl -s -o data/testnet_vl.json https://postfiat.org/testnet_vl.json
```

## Identifier sweep (privacy check)

Before any publish, run the pack-wide sweep for per-user records. It
must print nothing (exit 1 from `grep` = no match, which is the pass
condition here):

```sh
grep -rInE '0x[0-9a-fA-F]{40}|r[0-9A-HJ-NP-Za-km-z]{25,35}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' \
  --exclude-dir=.git --exclude=SHA256SUMS --exclude=testnet_vl.json . || echo "SWEEP CLEAN"
```

`data/testnet_vl.json` is excluded from that sweep on purpose: it is
the foundation-published validator list, whose single `blob` field is
base64 — long base64 runs trip the base58 address pattern as a false
positive. The blob decodes (see `scripts/validator_topology.py`) to
validator public keys (`ED...`) and manifests — public network data,
not user wallets, accounts, or handles — and the decoded list was
checked separately (25 keys, all `ED`-prefixed, 0 emails, 0 `0x`
addresses; the 8 base58-pattern matches in the decoded blob are all
substrings of the base64 manifest strings, verified by locating each
inside a `manifest` field).

Known false positives to expect and dismiss explicitly: the
`r[0-9A-Za-z]{24,34}`-style pattern matches camelCase JSON keys inside
the vendored `/api/tasks` body prefix (e.g.
`requiresActivePftlWalletSync`); those are keys, not addresses — the
stricter sweep above (base58 alphabet excluding 0/O/I/l, length 25–35)
does not match them. The vendored probe data contains no full response
bodies by design.

## Fresh-clone self-check performed for this pack

The pack was copied to a temp directory, `bash reproduce.sh` was run
there, and it exited 0 with digests passing. See
`outputs/reproduce_selfcheck.log` (recorded at build time).
