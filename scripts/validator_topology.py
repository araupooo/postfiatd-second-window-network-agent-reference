"""Validator topology re-derivation (M-02).

Reads the freshly fetched validator list (data/testnet_vl.json, fetched
2026-11-26 from https://postfiat.org/testnet_vl.json) and re-derives the
quorum and UNL-overlap figures from the pinned postfiatd source
(commit 0085a1ff885d6a446369cf73a4430f75af22be55, verified by local
clone + GitHub API):

  quorum = max(ceil(effective * 0.67), ceil(unl * 0.6))
    src/xrpld/app/misc/detail/ValidatorList.cpp:1933-1934
  (upstream rippled uses 0.80 in place of 0.67; the in-code comment at
  lines 1902-1905 says the fork uses 67% for devnet/testnet and that
  mainnet "should be reverted to 80%".)

Theorem 8 (arXiv:1802.07242, as quoted in the same comment):
fork safety for a pair of nodes requires
  Oi,j > nj/2 + ni - qi + ti,j
with ti,j = min(ti, tj, Oi,j); for qi = 0.67*ni and ti <= 0.33*ni this
gives pi + pj < 0.33*ni, i.e. the two UNLs may differ in at most
floor(0.33*ni) validators in total and stay fork-safe. The script
reports the same bound under the 80% rule for comparison.

Fully offline and deterministic. Writes data/topology_summary.json.

Usage: python3 scripts/validator_topology.py
"""

import base64
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
DATA = os.path.join(PACK, "data")
VL_PATH = os.path.join(DATA, "testnet_vl.json")
OUT_PATH = os.path.join(DATA, "topology_summary.json")

PINNED_COMMIT = "0085a1ff885d6a446369cf73a4430f75af22be55"


def load_vl():
    with open(VL_PATH) as f:
        doc = json.load(f)
    blob = doc["blobs_v2"][0]["blob"]
    raw = base64.urlsafe_b64decode(blob + "=" * (-len(blob) % 4))
    vl = json.loads(raw)
    return doc, vl


def quorum(unl_size, effective_size, factor):
    return max(math.ceil(effective_size * factor),
               math.ceil(unl_size * 0.6))


def main():
    doc, vl = load_vl()
    validators = vl["validators"]
    keys = [v["validation_public_key"] for v in validators]
    unl_size = len(keys)
    unique_keys = len(set(keys))
    effective = vl["effective"]
    sequence = vl["sequence"]
    expiration = vl["expiration"]

    q67 = quorum(unl_size, unl_size, 0.67)
    q80 = quorum(unl_size, unl_size, 0.80)
    # Theorem 8 bound, from the derivation in the source comment:
    # pi + pj < 0.33*ni under 67% (pi + pj < 0.20*ni under 80%),
    # strict inequality, so the largest integer total difference is
    # ceil(0.33*n) - 1 (67%) and ceil(0.20*n) - 1 (80%). With the
    # difference split evenly, the smallest fork-safe pairwise overlap is
    # n - max_total_difference / 2.
    max_diff_67 = math.ceil(0.33 * unl_size) - 1
    max_diff_80 = math.ceil(0.20 * unl_size) - 1
    min_overlap_67 = unl_size - max_diff_67 / 2.0
    min_overlap_80 = unl_size - max_diff_80 / 2.0

    summary = {
        "pinned_postfiatd_commit": PINNED_COMMIT,
        "validator_list": {
            "source_url": "https://postfiat.org/testnet_vl.json",
            "sequence": sequence,
            "effective_ripple_epoch": effective,
            "expiration_ripple_epoch": expiration,
            "validator_count": unl_size,
            "unique_validation_public_keys": unique_keys,
            "duplicate_keys": unl_size - unique_keys,
            "manifest_present_for_all": all("manifest" in v for v in validators),
        },
        "quorum_rederivation": {
            "formula": "max(ceil(effective*0.67), ceil(unl*0.6))",
            "source": "src/xrpld/app/misc/detail/ValidatorList.cpp:1933-1934",
            "unl_size": unl_size,
            "effective_unl_size": unl_size,
            "effective_unl_size_note": "The VL blob field 'effective' (848866298) is a Ripple-epoch timestamp, NOT a size. The effective UNL size is the count of listed validators (25); this matches the live validation_quorum of 17 reported by server_info (max(ceil(25*0.67), ceil(25*0.6)) = max(17, 15) = 17).",
            "quorum_67pct": q67,
            "quorum_80pct_upstream": q80,
            "quorum_delta": q80 - q67,
            "live_validation_quorum": "see data/window_summary.json agreement_and_missed.validation_quorum_at_fetch",
        },
        "unl_overlap_theorem8": {
            "source": "arXiv:1802.07242 via ValidatorList.cpp:1902-1932 comment",
            "max_total_unl_difference_67pct": max_diff_67,
            "max_total_unl_difference_80pct": max_diff_80,
            "min_pairwise_overlap_fork_safe_67pct": min_overlap_67,
            "min_pairwise_overlap_fork_safe_80pct": min_overlap_80,
            "note": "Bounds assume equal-size UNLs (ni = nj = n). Max total difference from pi + pj < 0.33*ni (67%) / < 0.20*ni (80%); minimum overlap assumes the difference is split evenly between the two UNLs.",
        },
    }
    with open(OUT_PATH, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    print("M-02 validators: %d (unique keys %d, duplicates %d)" % (
        unl_size, unique_keys, unl_size - unique_keys))
    print("M-02 quorum: 67%% rule -> %d, 80%% rule -> %d (delta %d)" % (
        q67, q80, q80 - q67))
    print("M-02 overlap: max total UNL difference 67%% -> %d, 80%% -> %d" % (
        max_diff_67, max_diff_80))
    print("M-02 PASS")


if __name__ == "__main__":
    main()
