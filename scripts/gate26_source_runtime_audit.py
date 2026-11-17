#!/usr/bin/env python3
"""Gate 26 — fail-closed Solidity runtime provenance audit for Base CHAR.

Compares exact compiled runtime vs eth_getCode at declared blocks, plus a
separate CBOR-metadata-stripped *executable prefix* test. Runtime matching
does NOT prove historical pre-transaction state or producer financing.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

POOL = "0x20b048fa035d5763685d695e66adf62c5d9f5055"
CALCULATOR = "0x6a4549759c475d845d4ae074b3656dc257490da5"
IMPLEMENTATION_SLOT = (
    "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
)
GATE25_CALCULATOR_HASH = "0x18a0f3dc9ce66d94741ad4e13edf136a497154f96c828bfa9148bc0591a1900b"
GATE25_POOL_IMPL_HASH = "0x9e01a24f7396330a59b37961a59c3ea2db412674f62570fdbb29bb0c73204c80"
GATE25_BLOCKS = {13826401, 15709581}


def parse_code(raw):
    if not isinstance(raw, str) or not raw.startswith("0x"):
        raise ValueError("not an EVM bytecode string")
    payload = raw[2:]
    if len(payload) % 2 or any(c not in "0123456789abcdefABCDEF" for c in payload):
        raise ValueError("invalid hex bytecode or unlinked references")
    return bytes.fromhex(payload)


def split_metadata(runtime):
    """Verify Solidity CBOR map envelope and two-byte length, never strip blindly."""
    if len(runtime) < 4:
        return runtime, None
    length = int.from_bytes(runtime[-2:], "big")
    start = len(runtime) - 2 - length
    if length < 3 or start < 0 or start >= len(runtime) - 2:
        return runtime, None
    marker = runtime[start]
    if not (0xa0 <= marker <= 0xbf):  # CBOR major type 5 (map)
        return runtime, None
    return runtime[:start], runtime[start:-2]


def first_diff(a, b):
    for n, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return n
    return min(len(a), len(b)) if len(a) != len(b) else None


def comparison(compiled, deployed, unresolved_links=False):
    if unresolved_links:
        return {"status": "UNRESOLVED_LINK_OR_IMMUTABLE_REFERENCES"}
    a, ameta = split_metadata(compiled)
    b, bmeta = split_metadata(deployed)
    result = {
        "compiled_length_bytes": len(compiled), "deployed_length_bytes": len(deployed),
        "compiled_cbor_bytes": len(ameta) if ameta is not None else None,
        "deployed_cbor_bytes": len(bmeta) if bmeta is not None else None,
        "compiled_sha256": hashlib.sha256(compiled).hexdigest(),
        "deployed_sha256": hashlib.sha256(deployed).hexdigest(),
        "full_first_diff_byte": first_diff(compiled, deployed),
        "executable_first_diff_byte": first_diff(a, b) if ameta is not None and bmeta is not None else None,
    }
    if compiled == deployed:
        result["status"] = "EXACT_RUNTIME_MATCH"
    elif ameta is not None and bmeta is not None and a == b:
        result["status"] = "EXECUTABLE_PREFIX_MATCH_METADATA_DIFFERS"
    elif ameta is not None and bmeta is not None:
        result["status"] = "EXECUTABLE_MISMATCH"
    else:
        result["status"] = "RUNTIME_MISMATCH_METADATA_UNRESOLVED"
    return result


def get_artifact(path):
    v = json.loads(Path(path).read_text())
    code = v.get("deployedBytecode")
    if isinstance(code, dict):
        artifact = code
        code = code.get("object")
    else:
        artifact = {}
    if not code:
        # Alternative Foundry build output layouts
        evm = v.get("evm", {}).get("deployedBytecode", {})
        artifact = evm
        code = evm.get("object")
    if not code:
        raise ValueError("missing deployed runtime in compilation artifact")
    unresolved = bool(artifact.get("linkReferences") or artifact.get("immutableReferences"))
    return parse_code(code), unresolved, {
        "contract_name": v.get("contractName") or "FeeCalculator",
        "compiler": v.get("metadata", {}).get("compiler") if isinstance(v.get("metadata"), dict) else None,
        "source_path": str(path),
        "has_link_or_immutable_references": unresolved,
    }


def keccak(runtime):
    # cast keccak is Ethereum Keccak-256; hashlib.sha3_256 is NOT equivalent.
    answer = subprocess.check_output(
        ["cast", "keccak", "0x" + runtime.hex()], text=True, stderr=subprocess.DEVNULL, timeout=25
    ).strip()
    if len(answer) != 66 or not answer.startswith("0x"):
        raise ValueError("invalid cast keccak output")
    return answer.lower()


class RPC:
    def __init__(self):
        url = os.environ.get("BASE_RPC_URL", "").strip()
        if not url.startswith("https://"):
            raise ValueError("BASE_RPC_URL must be complete HTTPS RPC endpoint")
        self.url = url
    def call(self, method, params):
        payload = json.dumps({"jsonrpc": "2.0", "id": 26, "method": method, "params": params}).encode()
        req = urllib.request.Request(self.url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                data = json.load(response)
        except Exception as exc:
            # NEVER include URLs, raw response bodies or provider exceptions in public logs.
            raise RuntimeError("RPC_TRANSPORT_FAILURE_" + type(exc).__name__) from None
        if "error" in data or "result" not in data:
            raise RuntimeError("RPC_METHOD_FAILURE_" + method)
        return data["result"]


def snapshot(rpc, block, output):
    suffix = hex(block)
    calldata = subprocess.check_output(["cast", "sig", "feeCalculator()"], text=True).strip()
    raw_slot = rpc.call("eth_getStorageAt", [POOL, IMPLEMENTATION_SLOT, suffix])
    if not isinstance(raw_slot, str) or len(raw_slot) != 66:
        raise ValueError("INVALID_PROXY_SLOT_RESPONSE")
    implementation = "0x" + raw_slot[-40:]
    raw_calc = rpc.call("eth_call", [{"to": POOL, "data": calldata}, suffix])
    if not isinstance(raw_calc, str) or len(raw_calc) != 66:
        raise ValueError("INVALID_ACTIVE_CALCULATOR_RESPONSE")
    active_calc = "0x" + raw_calc[-40:]
    if int(implementation, 16) == 0 or int(active_calc, 16) == 0:
        raise ValueError("ZERO_ACTIVE_IMPLEMENTATION_OR_CALCULATOR")
    calculator = parse_code(rpc.call("eth_getCode", [active_calc, suffix]))
    pool_impl = parse_code(rpc.call("eth_getCode", [implementation, suffix]))
    if not calculator or not pool_impl:
        raise ValueError("EMPTY_RUNTIME_BYTECODE")
    key = str(block)
    (output / f"calculator_runtime_{key}.hex").write_text("0x" + calculator.hex() + "\n")
    (output / f"pool_implementation_runtime_{key}.hex").write_text("0x" + pool_impl.hex() + "\n")
    return dict(
        block=block, eip1967_implementation=implementation.lower(),
        active_calculator=active_calc.lower(),
        calculator_bytes=len(calculator), pool_implementation_bytes=len(pool_impl),
        calculator_codehash=keccak(calculator), pool_implementation_codehash=keccak(pool_impl),
        calculator=calculator, pool_impl=pool_impl,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--blocks", nargs="+", type=int, default=[13826400,13826401,15709580,15709581,58258072])
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = dict(
        gate="26", chain_id=8453, scope="runtime equivalence at declared end-of-block snapshots",
        target_source="ToucanProtocol/dynamic-fee-pools@7aef954dae1bd0c7add4ed66d216251110521b16",
        status="NOT_VERIFIED", block_results=[], compiled_candidates=[],
        gate25_transaction_prestates="INDEPENDENT_GATE25_ONLY",
        bytecode_matching_is_not_economic_attribution=True,
    )
    def save():
        (out / "SUMMARY.json").write_text(json.dumps(report, indent=2) + "\n")
        (out / "FILE_SHA256.json").write_text(json.dumps(
            {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in out.iterdir() if p.is_file() and p.name not in ("FILE_SHA256.json", "SUMMARY.json")},
            indent=2
        ) + "\n")
    try:
        artifacts = sorted(Path(args.artifact_dir).glob("*.json"))
        if not artifacts:
            raise ValueError("NO_COMPILED_CANDIDATES")
        built = []
        for f in artifacts:
            item = {"candidate": f.stem}
            try:
                raw, unresolved, props = get_artifact(f)
                item.update(props)
                item.update({"compiled_bytes": len(raw), "compiled_codehash": keccak(raw)})
                built.append((f.stem, raw, unresolved))
            except Exception as exc:
                item["status"] = "COMPILED_ARTIFACT_INVALID_" + type(exc).__name__
            report["compiled_candidates"].append(item)
        rpc = RPC()
        if int(rpc.call("eth_chainId", []), 16) != 8453:
            raise ValueError("WRONG_CHAIN_ID")
        snaps = []
        for block in args.blocks:
            s = snapshot(rpc, block, out)
            row = {k: v for k, v in s.items() if k not in ("calculator", "pool_impl")}
            row["gate25_same_codehash"] = (
                "NOT_ANCHORED"
                if block not in GATE25_BLOCKS
                else ("MATCHED" if
                      row["calculator_codehash"] == GATE25_CALCULATOR_HASH
                      and row["pool_implementation_codehash"] == GATE25_POOL_IMPL_HASH
                      else "MISMATCH")
            )
            row["active_calculator_matches_gate25"] = s["active_calculator"] == CALCULATOR
            row["comparisons"] = {}
            for name, raw, unresolved in built:
                row["comparisons"][name] = comparison(raw, s["calculator"], unresolved)
            report["block_results"].append(row)
            snaps.append(s)
        actual_hashes = set(s["calculator_codehash"] for s in snaps)
        report["all_snapshots_same_calculator_runtime"] = len(actual_hashes) == 1
        report["all_snapshots_calculator_address_expected"] = all(
            s["active_calculator"] == CALCULATOR for s in snaps
        )
        anchors = [row["gate25_same_codehash"] for row in report["block_results"]
                   if row["gate25_same_codehash"] != "NOT_ANCHORED"]
        report["gate25_codehash_anchors_pass"] = bool(anchors) and all(x == "MATCHED" for x in anchors)
        found_exact = any(x["status"] == "EXACT_RUNTIME_MATCH"
                          for row in report["block_results"] for x in row["comparisons"].values())
        found_exec = any(x["status"] == "EXECUTABLE_PREFIX_MATCH_METADATA_DIFFERS"
                         for row in report["block_results"] for x in row["comparisons"].values())
        if not report["gate25_codehash_anchors_pass"]:
            report["status"] = "INCONSISTENT_WITH_GATE25_CODEHASH"
        elif found_exact and report["all_snapshots_same_calculator_runtime"]:
            report["status"] = "EXACT_SOURCE_RUNTIME_MATCH_DECLARED_SNAPSHOTS"
        elif found_exec and report["all_snapshots_same_calculator_runtime"]:
            report["status"] = "EXECUTABLE_PREFIX_MATCH_ONLY_METADATA_DIFFERS"
        else:
            report["status"] = "NO_SOURCE_EQUIVALENCE_ESTABLISHED_IN_TESTED_CONFIGS"
        report["historical_pool_source_equivalence"] = "NOT_TESTED_NO_PINNED_POOL_IMPL_SOURCE"
        report["complete_historical_coverage"] = False
        report["deployment_creation_provenance"] = "NOT_ESTABLISHED"
    except Exception as exc:
        report["status"] = "AUDIT_INCOMPLETE"
        report["failure"] = type(exc).__name__ + ": " + (
            str(exc) if isinstance(exc, ValueError) else "redacted"
        )
    finally:
        save()
        print(json.dumps({
            "status": report["status"],
            "snapshots": [(x["block"], x["calculator_codehash"], x["gate25_same_codehash"])
                          for x in report["block_results"]],
            "candidate_statuses": {
                x["candidate"]: sorted(set(row["comparisons"].get(x["candidate"], {}).get("status")
                                                 for row in report["block_results"]))
                for x in report["compiled_candidates"]
            },
        }, indent=2))
    # Scientific nonmatching is a valid audit outcome. Collection failures fail CI.
    return 1 if report["status"] in ("AUDIT_INCOMPLETE", "INCONSISTENT_WITH_GATE25_CODEHASH") else 0

if __name__ == "__main__":
    sys.exit(main())
