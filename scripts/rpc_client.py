"""Shared JSON-RPC client for the public PFTL testnet node.

Endpoint: https://rpc.testnet.postfiat.org (foundation node, public,
no credentials). Only read-only rippled methods are used: server_info,
ledger, fee. Retries with exponential backoff on 429/5xx and transport
errors; never sends credentials or identity material.
"""

import json
import time
import urllib.request
import urllib.error

RPC_URL = "https://rpc.testnet.postfiat.org"
USER_AGENT = "postfiatd-second-window-reference/1.0 (read-only measurement)"
MAX_ATTEMPTS = 4
BASE_DELAY_S = 1.0


class RpcError(Exception):
    pass


def rpc_call(method, params=None, timeout_s=30):
    """One JSON-RPC call with bounded retries. Returns the `result` dict."""
    body = json.dumps({"method": method, "params": params or [{}]}).encode()
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(
            RPC_URL,
            data=body,
            headers={"Content-Type": "application/json",
                     "User-Agent": USER_AGENT},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last_err = RpcError("HTTP %s on %s" % (e.code, method))
            if e.code == 429 or e.code >= 500:
                if attempt < MAX_ATTEMPTS:
                    time.sleep(BASE_DELAY_S * (2 ** (attempt - 1)))
                    continue
            raise last_err
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = RpcError("transport error on %s: %s" % (method, e))
            if attempt < MAX_ATTEMPTS:
                time.sleep(BASE_DELAY_S * (2 ** (attempt - 1)))
                continue
            raise last_err
        if "error" in payload:
            raise RpcError("RPC error for %s: %s" % (
                method, json.dumps(payload["error"])[:400]))
        if "result" not in payload:
            raise RpcError("RPC response without result for %s: %s" % (
                method, json.dumps(payload)[:400]))
        return payload["result"]
    raise last_err
