"""Public agent-surface probes (M-03).

READ-ONLY, UNAUTHENTICATED probes of the public task-platform surface
(https://tasknode.postfiat.org/). No session, no credentials, no user
identity, no signed requests. Six requests total, seconds apart.

Probes:
  P-01 GET  /                  (public landing page)
  P-02 GET  /robots.txt        (crawl policy)
  P-03 GET  /api               (API root, if any)
  P-04 GET  /api/tasks         (work-request listing without auth)
  P-05 POST /api/tasks  {}     (work-request submission without auth)
  P-06 POST /api/tasks  text/plain body (malformed content type)

Expected outcomes are authentication failures (401/403) or
not-found/routing responses (404/405). A 2xx on an unauthenticated
write would be a finding, not a success to exploit: the script records
it and stops.

Privacy: only status codes, response headers (with set-cookie values
redacted), a 300-character body prefix, and the body SHA-256 are
recorded. No full bodies are stored, so no per-user record can leak
into the pack. If a body prefix ever contained an identifier it would
be caught by the pack-wide identifier grep before release.

Replay mode (--replay) recomputes the probe table from
data/agent_surface_raw.json with no network. Live mode (--live)
performs the probes and writes that file.

Usage:
  python3 scripts/agent_surface_probe.py --live
  python3 scripts/agent_surface_probe.py --replay
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(HERE)
DATA = os.path.join(PACK, "data")
RAW_PATH = os.path.join(DATA, "agent_surface_raw.json")
SUMMARY_PATH = os.path.join(DATA, "agent_surface_summary.json")

BASE = "https://tasknode.postfiat.org"
USER_AGENT = "postfiatd-second-window-reference/1.0 (read-only public probe)"
DELAY_S = 2.0

PROBES = [
    ("P-01", "GET", "/", None, None),
    ("P-02", "GET", "/robots.txt", None, None),
    ("P-03", "GET", "/api", None, None),
    ("P-04", "GET", "/api/tasks", None, None),
    ("P-05", "POST", "/api/tasks", b"{}", "application/json"),
    ("P-06", "POST", "/api/tasks", b"not-json", "text/plain"),
]


def one_probe(pid, method, path, body, ctype):
    url = BASE + path
    headers = {"User-Agent": USER_AGENT}
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            raw = resp.read()
            resp_headers = dict(resp.headers.items())
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read()
        resp_headers = dict(e.headers.items())
    except Exception as e:  # noqa: BLE001 - transport failure is a finding
        return {"id": pid, "method": method, "path": path,
                "status": None, "error": str(e)[:200],
                "elapsed_ms": int((time.time() - t0) * 1000)}
    resp_headers = {k: ("REDACTED" if k.lower() in ("set-cookie", "cookie")
                        else v) for k, v in resp_headers.items()}
    prefix = raw[:300].decode("utf-8", "replace")
    return {
        "id": pid,
        "method": method,
        "path": path,
        "status": status,
        "elapsed_ms": int((time.time() - t0) * 1000),
        "content_type": resp_headers.get("Content-Type"),
        "headers": resp_headers,
        "body_prefix_300": prefix,
        "body_sha256": hashlib.sha256(raw).hexdigest(),
        "body_bytes": len(raw),
    }


def live_probe():
    results = []
    for pid, method, path, body, ctype in PROBES:
        results.append(one_probe(pid, method, path, body, ctype))
        time.sleep(DELAY_S)
    raw = {
        "base": BASE,
        "method": "Unauthenticated read-only probes; no session, no credentials, no user identity.",
        "probed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "probe_count": len(results),
        "results": results,
    }
    with open(RAW_PATH, "w") as f:
        json.dump(raw, f, indent=2, sort_keys=True)
    return raw


def summarize(raw):
    # Body-shape classification from the stored 300-char prefix:
    # HTML shell (SPA fallback) vs JSON API response.
    shells = {}
    for r in raw["results"]:
        if r.get("body_prefix_300", "").lstrip().startswith("<!doctype"):
            shells[r["id"]] = r.get("body_sha256")
    rows = []
    for r in raw["results"]:
        status = r.get("status")
        prefix = r.get("body_prefix_300", "").lstrip()
        is_html = prefix.startswith("<!doctype")
        is_json = prefix.startswith("{")
        if status is None:
            verdict = "TRANSPORT-ERROR"
        elif status in (401, 403):
            verdict = "AUTH-REQUIRED (expected)"
        elif status == 404:
            verdict = "NOT-FOUND (route absent or hidden)"
        elif status == 405:
            verdict = "METHOD-NOT-ALLOWED"
        elif status == 415:
            verdict = "UNSUPPORTED-MEDIA-TYPE"
        elif status == 429:
            verdict = "RATE-LIMITED"
        elif 200 <= status < 300 and is_html:
            if r["id"] == "P-01":
                verdict = "PUBLIC-HTML-SHELL (landing page, expected)"
            elif shells.get(r["id"]) == shells.get("P-01"):
                verdict = "SPA-FALLBACK (byte-identical to / shell)"
            else:
                verdict = "PUBLIC-HTML-SHELL"
        elif 200 <= status < 300 and is_json:
            verdict = "UNAUTHENTICATED-JSON-READ (finding)"
        elif 200 <= status < 300:
            verdict = "UNEXPECTED-2xx (finding: unauthenticated access)"
        else:
            verdict = "OTHER-%s" % status
        rows.append({"id": r["id"], "method": r["method"], "path": r["path"],
                     "status": status, "verdict": verdict,
                     "elapsed_ms": r.get("elapsed_ms"),
                     "body_sha256": r.get("body_sha256")})
    summary = {
        "base": raw["base"],
        "probe_count": raw["probe_count"],
        "auth_required_count": sum(1 for x in rows if x["status"] in (401, 403)),
        "unexpected_2xx_count": sum(1 for x in rows if x["verdict"].startswith("UNEXPECTED-2xx")),
        "unauthenticated_json_read_count": sum(1 for x in rows if x["verdict"].startswith("UNAUTHENTICATED-JSON-READ")),
        "rate_limited_count": sum(1 for x in rows if x["status"] == 429),
        "transport_errors": sum(1 for x in rows if x["status"] is None),
        "rows": rows,
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
        raw = live_probe()
    else:
        with open(RAW_PATH) as f:
            raw = json.load(f)
    s = summarize(raw)
    for row in s["rows"]:
        print("M-03 %s %s %s -> %s : %s" % (
            row["id"], row["method"], row["path"], row["status"], row["verdict"]))
    print("M-03 probes=%d auth-required=%d unauth-json-read=%d unexpected-2xx=%d rate-limited=%d transport-errors=%d" % (
        s["probe_count"], s["auth_required_count"], s["unauthenticated_json_read_count"],
        s["unexpected_2xx_count"],
        s["rate_limited_count"], s["transport_errors"]))
    print("M-03 PASS")


if __name__ == "__main__":
    main()
