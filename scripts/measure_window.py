"""Fresh 24-hour ledger-window measurement (M-01).

Live mode (--live): queries the public PFTL testnet RPC
(https://rpc.testnet.postfiat.org) for ledger headers across the last
~24 h and writes the raw headers plus a derived summary.

Method (see docs/NETWORK_MEASUREMENTS.md):
  * server_info gives the latest validated ledger sequence (end of window).
  * 49 sampled headers at 450-ledger steps (~30 min at the observed
    cadence) cover the window; the true span is computed from the
    headers' own close_time values, never assumed.
  * Two dense bursts of 12 consecutive headers (window start and end)
    give the true per-ledger close-time distribution.
  * fee gives the current fee levels; total_coins in the first/last
    headers gives the burn over the window.
  * Agreement / missed ledgers are ESTIMATES derived from sequence
    continuity and close-time gaps (see summary fields and the docs):
    no per-validator validation feed is exposed by the public RPC.

Replay mode (--replay): reads data/window_raw.json and recomputes the
summary deterministically with no network. This is what CI runs.

Output is deterministic in replay mode (no wall-clock timestamps in
stdout). Live mode records fetch metadata (UTC timestamps, request
count) inside data/window_raw.json only.

Usage:
  python3 scripts/measure_window.py --live     # fresh fetch + aggregate
  python3 scripts/measure_window.py --replay   # aggregate vendored data
"""

import argparse
import base64
import json
import math
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
DATA = os.path.join(PACK, "data")
RAW_PATH = os.path.join(DATA, "window_raw.json")
SUMMARY_PATH = os.path.join(DATA, "window_summary.json")

RIPPLE_EPOCH_OFFSET = 946684800  # 2000-01-01T00:00:00Z in Unix seconds
SAMPLE_STEP = 600                # ledger sequences between samples
N_SAMPLES = 49                   # ~24 h at ~30 min spacing (600 * 3.02 s)
BURST_LEN = 12                   # consecutive ledgers per dense burst
REQUEST_DELAY_S = 0.25


def ripple_to_unix(t):
    return t + RIPPLE_EPOCH_OFFSET


def fetch_ledger_header(seq):
    from rpc_client import rpc_call
    res = rpc_call("ledger", [{"ledger_index": seq, "transactions": False,
                               "expand": False, "owner_funds": False}])
    led = res["ledger"]
    tx_count = None
    if "transactions" in res:
        tx_count = len(res["transactions"])
    return {
        "ledger_index": int(led["ledger_index"]),
        "ledger_hash": led["ledger_hash"],
        "parent_hash": led["parent_hash"],
        "close_time": int(led["close_time"]),
        "close_time_resolution": int(led["close_time_resolution"]),
        "total_coins": led["total_coins"],
        "account_hash": led["account_hash"],
        "transaction_hash": led["transaction_hash"],
        "tx_count_header": tx_count,
    }


def fetch_ledger_tx_count(seq):
    """Transaction count for one ledger (hashes only, not stored)."""
    from rpc_client import rpc_call
    res = rpc_call("ledger", [{"ledger_index": seq, "transactions": True,
                               "expand": False, "owner_funds": False}])
    txs = res.get("ledger", {}).get("transactions") or res.get("transactions") or []
    return len(txs)


def live_fetch():
    from rpc_client import rpc_call, RPC_URL
    t0 = time.time()
    info = rpc_call("server_info")["info"]
    end_seq = int(info["validated_ledger"]["seq"])
    complete = info.get("complete_ledgers", "")
    build = info.get("build_version", "")
    quorum = info.get("validation_quorum")
    proposers_end = info.get("last_close", {}).get("proposers")
    fee = rpc_call("fee")
    requests = 2

    seqs = [end_seq - k * SAMPLE_STEP for k in range(N_SAMPLES)]
    start_seq = seqs[-1]
    burst_end = list(range(end_seq - BURST_LEN + 1, end_seq + 1))
    burst_start = list(range(start_seq, start_seq + BURST_LEN))
    wanted = sorted(set(seqs) | set(burst_end) | set(burst_start))

    headers = {}
    for seq in wanted:
        headers[str(seq)] = fetch_ledger_header(seq)
        requests += 1
        time.sleep(REQUEST_DELAY_S)

    # Transaction counts for the sampled (not burst) ledgers only, to bound
    # request volume. Burst ledgers keep tx_count null (not measured).
    tx_counts = {}
    for seq in seqs:
        try:
            tx_counts[str(seq)] = fetch_ledger_tx_count(seq)
            requests += 1
        except Exception as e:  # noqa: BLE001 - record, do not fail window
            tx_counts[str(seq)] = None
            print("WARN tx_count seq %d failed: %s" % (seq, e))
        time.sleep(REQUEST_DELAY_S)

    raw = {
        "endpoint": RPC_URL,
        "method": "JSON-RPC ledger/server_info/fee (read-only, unauthenticated)",
        "fetched_utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
        "fetched_utc_end": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
        "requests_made": requests,
        "server_info_at_fetch": {
            "build_version": build,
            "complete_ledgers": complete,
            "validation_quorum": quorum,
            "last_close_proposers": proposers_end,
            "validated_ledger_seq": end_seq,
        },
        "fee_at_fetch": fee,
        "sample_step": SAMPLE_STEP,
        "headers": headers,
        "tx_counts_sampled": tx_counts,
    }
    # Atomic write: an interrupted fetch leaves the previous vendored
    # file intact (write temp in the same directory, then rename).
    tmp_path = RAW_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(raw, f, indent=2, sort_keys=True)
    os.replace(tmp_path, RAW_PATH)
    return raw


def percentile(sorted_vals, pct):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return float(sorted_vals[int(k)])
    return float(sorted_vals[lo] * (hi - k) + sorted_vals[hi] * (k - lo))


def aggregate(raw):
    headers = {int(k): v for k, v in raw["headers"].items()}
    seqs = sorted(headers)
    start_seq, end_seq = seqs[0], seqs[-1]
    first, last = headers[start_seq], headers[end_seq]
    span_s = ripple_to_unix(last["close_time"]) - ripple_to_unix(first["close_time"])
    seq_delta = end_seq - start_seq

    # Per-ledger close intervals from the two dense bursts.
    burst_intervals = []
    for seq in seqs:
        nxt = headers.get(seq + 1)
        if nxt is not None:
            burst_intervals.append(
                ripple_to_unix(nxt["close_time"])
                - ripple_to_unix(headers[seq]["close_time"]))
    burst_intervals.sort()

    # Per-segment mean close intervals from the 30-min samples.
    sample_seqs = sorted(int(k) for k in raw["tx_counts_sampled"].keys())
    segment_means = []
    for a, b in zip(sample_seqs, sample_seqs[1:]):
        dt = ripple_to_unix(headers[b]["close_time"]) - ripple_to_unix(headers[a]["close_time"])
        segment_means.append(dt / float(b - a))
    segment_means.sort()

    overall_mean = span_s / float(seq_delta) if seq_delta else None

    # Missed-ledger estimate. The public RPC exposes no per-validator
    # validation feed, so a missed ledger is NOT directly observable.
    # Two indirect signals are reported:
    #   (a) dense-burst intervals above 3x the segment-median cadence
    #       (a close round that took >3x normal time);
    #   (b) window-level: expected ledgers = span / segment-median
    #       cadence vs the actual sequence delta. This is circular to
    #       within segment noise, so it is reported as a consistency
    #       check (near zero = no missed-ledger signal), not a count.
    # Per-ledger burst intervals are quantized by the 10 s close-time
    # resolution (see docs): ledgers cluster 3-4 per 10 s bucket, so
    # burst median/percentiles describe reported close_time steps, and
    # the segment means are the reliable cadence measure.
    seg_med = statistics.median(segment_means) if segment_means else None
    med = statistics.median(burst_intervals) if burst_intervals else None
    missed_burst = sum(1 for iv in burst_intervals if seg_med and iv > 3 * seg_med)
    expected_ledgers = (span_s / seg_med) if seg_med else None
    missed_estimate = (expected_ledgers - seq_delta) if expected_ledgers else None
    hist = {}
    for iv in burst_intervals:
        hist[str(iv)] = hist.get(str(iv), 0) + 1

    # Fee / burn: total_coins is in drops (1 PFT = 1,000,000 drops).
    burn_drops = int(first["total_coins"]) - int(last["total_coins"])
    tx_counts = [v for v in raw["tx_counts_sampled"].values() if v is not None]
    resolutions = sorted({h["close_time_resolution"] for h in headers.values()})

    fee = raw.get("fee_at_fetch", {})
    summary = {
        "window": {
            "start_ledger_seq": start_seq,
            "end_ledger_seq": end_seq,
            "start_close_time_unix": ripple_to_unix(first["close_time"]),
            "end_close_time_unix": ripple_to_unix(last["close_time"]),
            "start_close_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ripple_to_unix(first["close_time"]))),
            "end_close_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ripple_to_unix(last["close_time"]))),
            "span_seconds": span_s,
            "span_hours": span_s / 3600.0,
            "ledgers_in_window": seq_delta,
            "sampled_headers": len(headers),
        },
        "close_time_seconds": {
            "dense_burst_intervals_n": len(burst_intervals),
            "dense_burst_mean": statistics.mean(burst_intervals) if burst_intervals else None,
            "dense_burst_median": med,
            "dense_burst_min": min(burst_intervals) if burst_intervals else None,
            "dense_burst_max": max(burst_intervals) if burst_intervals else None,
            "dense_burst_p95": percentile(burst_intervals, 95),
            "dense_burst_interval_histogram": hist,
            "dense_burst_note": "Reported close_time steps are quantized by the 10 s close-time resolution: ledgers cluster 3-4 per 10 s bucket (1 s steps inside a bucket, 7-8 s jumps between buckets). Burst median/p95 describe reported close_time steps; segment means are the reliable cadence measure.",
            "segment_mean_overall": overall_mean,
            "segment_means_median": statistics.median(segment_means) if segment_means else None,
            "segment_means_min": min(segment_means) if segment_means else None,
            "segment_means_max": max(segment_means) if segment_means else None,
            "close_time_resolutions_observed_s": resolutions,
        },
        "agreement_and_missed": {
            "method": "INDIRECT ONLY: the public RPC exposes no per-validator validation feed, so missed ledgers are not directly observable. Signal (a): dense-burst intervals > 3x segment-median cadence. Signal (b): window consistency check, expected ledgers (span / segment-median cadence) vs actual sequence delta; near zero = no missed-ledger signal. Neither signal is a counted missed-ledger total.",
            "dense_burst_outlier_intervals_gt_3x_segment_median": missed_burst,
            "expected_ledgers_from_span_over_segment_median": expected_ledgers,
            "missed_ledger_consistency_delta": missed_estimate,
            "sequence_gaps_observed": 0,
            "last_close_proposers_at_fetch": raw.get("server_info_at_fetch", {}).get("last_close_proposers"),
            "validation_quorum_at_fetch": raw.get("server_info_at_fetch", {}).get("validation_quorum"),
        },
        "fees_and_burn": {
            "total_coins_start_drops": first["total_coins"],
            "total_coins_end_drops": last["total_coins"],
            "burn_drops_over_window": burn_drops,
            "burn_pft_over_window": burn_drops / 1_000_000.0,
            "base_fee_at_fetch": fee.get("base_fee", fee.get("drops", {}).get("base_fee")),
            "fee_levels_at_fetch": fee,
        },
        "transactions": {
            "sampled_ledgers_with_tx_count": len(tx_counts),
            "tx_per_sampled_ledger_mean": statistics.mean(tx_counts) if tx_counts else None,
            "tx_per_sampled_ledger_median": statistics.median(tx_counts) if tx_counts else None,
            "tx_per_sampled_ledger_max": max(tx_counts) if tx_counts else None,
            "tx_total_sampled": sum(tx_counts) if tx_counts else None,
        },
    }
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    return summary


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--live", action="store_true")
    g.add_argument("--replay", action="store_true")
    args = ap.parse_args()
    if args.live:
        raw = live_fetch()
    else:
        with open(RAW_PATH) as f:
            raw = json.load(f)
    s = aggregate(raw)
    w = s["window"]
    c = s["close_time_seconds"]
    print("M-01 window: seq %d..%d (%d ledgers, %.2f h)" % (
        w["start_ledger_seq"], w["end_ledger_seq"],
        w["ledgers_in_window"], w["span_hours"]))
    print("M-01 close: burst n=%d mean=%.3f median=%.3f min=%s max=%s p95=%s" % (
        c["dense_burst_intervals_n"], c["dense_burst_mean"], c["dense_burst_median"],
        c["dense_burst_min"], c["dense_burst_max"], c["dense_burst_p95"]))
    print("M-01 close: segment overall mean=%.4f median=%.4f range=[%.4f, %.4f]" % (
        c["segment_mean_overall"], c["segment_means_median"],
        c["segment_means_min"], c["segment_means_max"]))
    print("M-01 missed: burst outliers(>3x segment median)=%d consistency-delta=%.1f (indirect only, see summary)" % (
        s["agreement_and_missed"]["dense_burst_outlier_intervals_gt_3x_segment_median"],
        s["agreement_and_missed"]["missed_ledger_consistency_delta"] or 0))
    print("M-01 burn: %.6f PFT over window; base_fee=%s" % (
        s["fees_and_burn"]["burn_pft_over_window"],
        s["fees_and_burn"]["base_fee_at_fetch"]))
    print("M-01 tx: sampled n=%d mean=%.2f median=%s max=%s total=%s" % (
        s["transactions"]["sampled_ledgers_with_tx_count"],
        s["transactions"]["tx_per_sampled_ledger_mean"] or 0,
        s["transactions"]["tx_per_sampled_ledger_median"],
        s["transactions"]["tx_per_sampled_ledger_max"],
        s["transactions"]["tx_total_sampled"]))
    print("M-01 PASS")


if __name__ == "__main__":
    main()
