#!/usr/bin/env python3
"""Gate 27: targeted public verification provenance and scoped proxy version boundary.

- Queries only three specifically identified public addresses (no indexing crawl).
- Never infers original Standard JSON from ABI/source display.
- Boundary search assumes version difference at endpoints; detects one transition,
  not an exhaustive upgrade-event census.
- All RPC calls are read-only; no API keys are needed other than existing RPC secret.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import urllib.error

CHAIN = 8453
POOL = "0x20b048fa035d5763685d695e66adf62c5d9f5055"
CALC = "0x6a4549759c475d845d4ae074b3656dc257490da5"
OLD_IMPL = "0xb61763cf40e53df924856925461d5914c274ecd8"
NEW_IMPL = "0x23da31aa73720f770c21e9ec0a8382ec279e0c85"
SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
BEFORE = 15709581
AFTER = 58258072
DEPLOY_JSON = ("https://raw.githubusercontent.com/ToucanProtocol/contracts/"
               "9afe1809bd4840cad82fc49d26d8286a7c6728e1/"
               "deployments/production/base/Biochar.json")


def public_json(url, cap=5_000_000):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Paper2-CHAR-provenance-audit/1.0 (+https://github.com/plinhnguyende-svg/Paper-2-model0)",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read(cap + 1)
            if len(raw) > cap:
                raise ValueError("PUBLIC_RESPONSE_TOO_LARGE")
        return json.loads(raw), hashlib.sha256(raw).hexdigest(), len(raw)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("HTTP_" + str(exc.code)) from None
    except urllib.error.URLError:
        raise RuntimeError("PUBLIC_HOST_UNREACHABLE") from None


def discover_fields(obj, max_depth=6):
    """Extract only keys indicating verified source/build provenance."""
    found = []
    interesting = (
        "standardjson", "standard_json", "compiler", "compilation",
        "match", "metadata", "optimization", "sources", "settings",
        "verified", "is_verified", "file_path", "language"
    )
    def visit(v, path, depth):
        if depth > max_depth or len(found) >= 70:
            return
        if isinstance(v, dict):
            for k, child in v.items():
                low = k.lower()
                if any(w in low for w in interesting):
                    found.append(dict(path=path + "." + k,
                                      type=type(child).__name__,
                                      length=len(child) if hasattr(child, "__len__") else None,
                                      preview=(str(child)[:150] if isinstance(child, (bool, int, str))
                                               else None)))
                if isinstance(child, (dict, list)):
                    visit(child, path + "." + k, depth + 1)
        elif isinstance(v, list):
            for i, child in enumerate(v[:8]):
                if isinstance(child, (dict, list)):
                    visit(child, path + "[" + str(i) + "]", depth + 1)
    visit(obj, "root", 0)
    return found


def json_inputs(obj, max_depth=6):
    """Locate actual Standard JSON {language,sources,settings}; do not invent it."""
    matches = []
    def visit(v, path, depth):
        if depth > max_depth:
            return
        if isinstance(v, str):
            # Some explorers embed compiler Standard JSON as escaped string.
            if len(v) < 6_000_000 and "sources" in v[:1000] and "settings" in v[:1000]:
                try:
                    parsed = json.loads(v)
                except (ValueError, TypeError):
                    return
                visit(parsed, path + "/decoded", depth + 1)
        elif isinstance(v, dict):
            if v.get("language") == "Solidity" and isinstance(v.get("sources"), dict) \
                    and isinstance(v.get("settings"), dict):
                matches.append((path, v))
            for k, child in v.items():
                if k in ("source_code", "abi", "constructor_args", "constructor_args", "deployed_bytecode"):
                    continue
                if isinstance(child, (dict, list, str)):
                    visit(child, path + "." + k, depth + 1)
        elif isinstance(v, list):
            for i, child in enumerate(v[:5]):
                visit(child, path + "[" + str(i) + "]", depth + 1)
    visit(obj, "root", 0)
    return matches


def fetch_verified_sources(out):
    results = []
    for name, address in [
        ("fee_calculator", CALC), ("early_pool_implementation", OLD_IMPL),
        ("later_pool_implementation", NEW_IMPL)
    ]:
        entry = dict(role=name, address=address, providers=[])
        for source, url in [
            ("sourcify_v2", f"https://sourcify.dev/server/v2/contract/{CHAIN}/{address}?fields=all"),
            ("blockscout_v2", f"https://base.blockscout.com/api/v2/smart-contracts/{address}"),
        ]:
            record = dict(provider=source, status="NOT_VERIFIED")
            try:
                obj, sha, size = public_json(url)
                record.update(status="RESPONSE_RECEIVED", response_sha256=sha,
                              response_bytes=size, top_level_keys=sorted(obj.keys()) if isinstance(obj, dict) else [],
                              available_fields=discover_fields(obj))
                matches = json_inputs(obj)
                record["standard_json_inputs_found"] = len(matches)
                for idx, (path, item) in enumerate(matches):
                    filename = name + "_" + source + "_standard_input_" + str(idx) + ".json"
                    (out / filename).write_text(json.dumps(item, indent=2) + "\n")
                    record.setdefault("standard_json_files", []).append(dict(
                        path=path, filename=filename,
                        sha256=hashlib.sha256((out / filename).read_bytes()).hexdigest(),
                        source_files=len(item["sources"]),
                        settings=item["settings"]
                    ))
                # Persist the raw *public provenance response* to enable later audit.
                # These are not secret on-chain credentials.
                filename = name + "_" + source + "_verification.json"
                (out / filename).write_text(json.dumps(obj, indent=2) + "\n")
                record["raw_response_file"] = filename
            except Exception as exc:
                record.update(status="UNAVAILABLE", failure_type=type(exc).__name__,
                              failure_code=str(exc) if isinstance(exc, (RuntimeError, ValueError)) else "REDACTED")
            entry["providers"].append(record)
        results.append(entry)
    return results


class RPC:
    def __init__(self):
        self.url = os.environ.get("BASE_RPC_URL", "").strip()
        if not self.url.startswith("https://"):
            raise ValueError("CONFIGURED_HTTPS_BASE_RPC_REQUIRED")
    def call(self, method, params):
        data = json.dumps(dict(jsonrpc="2.0", id=27, method=method, params=params)).encode()
        req = urllib.request.Request(self.url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                output = json.load(response)
        except Exception as exc:
            raise RuntimeError("RPC_TRANSPORT_" + type(exc).__name__) from None
        if "error" in output or "result" not in output:
            raise RuntimeError("RPC_METHOD_" + method)
        return output["result"]


def implementation(rpc, block):
    word = rpc.call("eth_getStorageAt", [POOL, SLOT, hex(block)])
    if not isinstance(word, str) or len(word) != 66:
        raise ValueError("INVALID_IMPLEMENTATION_SLOT")
    return "0x" + word[-40:].lower()


def transition_boundary(rpc, left=BEFORE, right=AFTER):
    """Find first block with different slot value under monotone-version assumption.
    If version has switched back in between, other events remain undetected.
    """
    low_val = implementation(rpc, left)
    high_val = implementation(rpc, right)
    result = dict(left=left, right=right,
                  left_impl=low_val, right_impl=high_val,
                  method="binary search of first different EIP1967 storage value",
                  upgrade_census_complete=False, monotone_version_assumption_unproven=True,
                  probes=[])
    if low_val == high_val:
        result["status"] = "NO_ENDPOINT_VERSION_DIFFERENCE"
        return result
    while left + 1 < right:
        m = (left + right) // 2
        val = implementation(rpc, m)
        result["probes"].append(dict(block=m, implementation=val))
        if val == low_val:
            left = m
        else:
            right = m
    result["boundary_block"] = right
    result["before_implementation"] = implementation(rpc, right - 1)
    result["after_implementation"] = implementation(rpc, right)
    result["status"] = "BOUNDED_VERSION_CHANGE_FOUND"
    topics = []
    for sig in ("Upgraded(address)", "AdminChanged(address,address)",
                "BeaconUpgraded(address)"):
        topic = subprocess.check_output(["cast", "keccak", sig], text=True).strip()
        topics.append(topic)
    logs = rpc.call("eth_getLogs", [{
        "address": POOL, "fromBlock": hex(max(0, right - 1)),
        "toBlock": hex(right + 1), "topics": [topics]
    }])
    result["adjacent_upgrade_logs"] = [{
        "block": int(x["blockNumber"], 16),
        "transaction_hash": x["transactionHash"],
        "log_index": int(x["logIndex"], 16),
        "topic0": x["topics"][0],
        "topics": x["topics"],
        "address": x["address"]
    } for x in logs]
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = dict(gate=27, chain=8453, status="NOT_EXECUTED",
                   verified_standard_json="UNCONFIRMED",
                   proxy_change="NOT_EXECUTED", full_upgrade_census=False,
                   calculator_metadata_exact_match="NOT_ESTABLISHED",
                   economic_inference="NONE")
    try:
        summary["verification_queries"] = fetch_verified_sources(out)
        found = [x for e in summary["verification_queries"] for x in e["providers"]
                 if x.get("standard_json_inputs_found", 0) > 0]
        summary["verified_standard_json"] = (
            "PUBLIC_STANDARD_JSON_INPUT_LOCATED_NEEDS_COMPILER_REPRODUCTION"
            if found else "NO_EXACT_STANDARD_JSON_INPUT_FOUND_IN_RETURNED_FIELDS"
        )
        rpc = RPC()
        assert int(rpc.call("eth_chainId", []), 16) == CHAIN, "WRONG_NETWORK"
        summary["proxy_boundary"] = transition_boundary(rpc)
        summary["proxy_change"] = summary["proxy_boundary"]["status"]
        summary["status"] = "EVIDENCE_COLLECTED_WITH_EXPLICIT_LIMITS"
    except Exception as exc:
        summary["status"] = "INCOMPLETE"
        summary["failure"] = type(exc).__name__ + ": " + (
            str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "REDACTED"
        )
    finally:
        (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
        (out / "SHA256.json").write_text(json.dumps({
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in out.iterdir() if p.is_file() and p.name != "SHA256.json"
        }, indent=2) + "\n")
        print(json.dumps({k: v for k, v in summary.items() if k not in ("verification_queries",)},
                         indent=2))
        for e in summary.get("verification_queries", []):
            print(json.dumps(dict(role=e["role"], results=[
                dict(provider=x["provider"], status=x["status"],
                     standard_inputs=x.get("standard_json_inputs_found", 0),
                     failure_code=x.get("failure_code"))
                for x in e["providers"]
            ])))
    return 0 if summary["status"] == "EVIDENCE_COLLECTED_WITH_EXPLICIT_LIMITS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
