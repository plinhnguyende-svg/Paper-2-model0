#!/usr/bin/env python3
"""Read-only Base transaction discovery. No broadcast or private key required."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess


POOL = "0x20b048fa035d5763685d695e66adf62c5d9f5055"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO = "0x" + "0" * 64

def transfers(receipt):
    rows = []
    for log in receipt.get("logs", []):
        topics = log.get("topics", [])
        if len(topics) == 3 and topics[0].lower() == TRANSFER and len(log.get("data", "")) == 66:
            rows.append(dict(token=log["address"].lower(), sender="0x"+topics[1][-40:],
                             recipient="0x"+topics[2][-40:], amount_wei=str(int(log["data"], 16)),
                             log_index=int(log["logIndex"], 16)))
    return rows

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--end", type=int, required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    if not 0 <= args.start <= args.end:
        p.error("invalid block interval")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rpc = os.environ.get("BASE_RPC_URL") or "https://mainnet.base.org"
    summary = dict(chain_id=8453, pool=POOL, start=args.start, end=args.end,
                   selection="first three distinct CHAR mint/burn txs ordered by block, tx index, log index",
                   evidence_status="UNVERIFIED", candidates=[], scan_errors=[],
                   economic_status="producer identity, cash realization, beta and additional removal unverified")
    def save(name, data):
        (out/name).write_text(json.dumps(data, indent=2)+"\n")
    def call(method, params):
        result = subprocess.run(["cast", "rpc", method, *[json.dumps(v) for v in params],
                                 "--rpc-url", rpc], capture_output=True, text=True, timeout=25)
        if result.returncode:
            detail = re.sub(r"https?://[^\\s]+", "[URL_REDACTED]", result.stderr.replace(rpc, "[RPC_REDACTED]"))
            save("RPC_ERROR.json", dict(method=method, detail=detail[:1500]))
            raise RuntimeError(f"{method}: cast RPC failed")
        return json.loads(result.stdout)
    try:
        if int(call("eth_chainId", []), 16) != 8453:
            raise RuntimeError("wrong chain")
        logs = []
        # Chunked scan, with explicit gaps. Empty window is not evidence of no activity elsewhere.
        for start in range(args.start, args.end+1, 1000):
            end = min(start+999, args.end)
            try:
                batch = call("eth_getLogs", [dict(address=POOL, fromBlock=hex(start),
                              toBlock=hex(end), topics=[TRANSFER])])
                save(f"logs_{start}_{end}.json", batch)
                logs.extend(batch)
                print(f"Scanned blocks {start}-{end}: {len(batch)} logs", flush=True)
            except Exception as exc:
                summary["scan_errors"].append(dict(start=start, end=end, error=type(exc).__name__))
                break  # Preserve partial evidence promptly instead of repeating an unavailable RPC.
        logs.sort(key=lambda x: tuple(int(x[k],16) for k in ("blockNumber","transactionIndex","logIndex")))
        hashes = []
        for log in logs:
            if len(log["topics"]) == 3 and ZERO in log["topics"][1:] and log["transactionHash"] not in hashes:
                hashes.append(log["transactionHash"])
        summary["mint_burn_candidates_in_successfully_scanned_ranges"] = len(hashes)
        for txhash in hashes[:3]:
            print(f"Collecting candidate {txhash}", flush=True)
            row = dict(tx_hash=txhash, status="CANDIDATE_ONLY", fee_matching="NOT_DONE")
            summary["candidates"].append(row)
            try:
                tx = call("eth_getTransactionByHash", [txhash])
                receipt = call("eth_getTransactionReceipt", [txhash])
                block = call("eth_getBlockByNumber", [tx["blockNumber"], False])
                assert receipt["transactionHash"] == txhash
                assert receipt["blockHash"] == block["hash"] == tx["blockHash"]
                assert receipt["transactionIndex"] == tx["transactionIndex"]
                assert block["transactions"][int(tx["transactionIndex"],16)] == txhash
                save(txhash+"_tx.json", tx)
                save(txhash+"_receipt.json", receipt)
                save(txhash+"_block.json", block)
                save(txhash+"_erc20_transfers.json", transfers(receipt))
                row.update(block=int(tx["blockNumber"],16), tx_index=int(tx["transactionIndex"],16),
                           receipt_status=int(receipt["status"],16), selector=tx["input"][:10],
                           erc20_transfers=len(transfers(receipt)), receipt_identity="MATCHED")
                # Native node tracing uses exact intra-block execution, if supported.
                for tracer in ("callTracer", "prestateTracer"):
                    try:
                        trace = call("debug_traceTransaction", [txhash, dict(tracer=tracer, timeout="20s")])
                        save(txhash+"_"+tracer+".json", trace)
                        row[tracer] = "CAPTURED_NOT_YET_RECONCILED"
                    except Exception:
                        row[tracer] = "UNAVAILABLE"
                # Deliberately omit --quick: cast run replays earlier txs in the block.
                # Successful command execution alone does not establish fee/transfer equality.
                try:
                    result = subprocess.run(["cast","run",txhash,"--rpc-url",rpc],
                                            capture_output=True, text=True, timeout=65)
                    text = (result.stdout+"\n"+result.stderr).replace(rpc, "[RPC_REDACTED]")
                    (out/(txhash+"_replay.txt")).write_text(text)
                    row["cast_run_exit"] = result.returncode
                except subprocess.TimeoutExpired:
                    row["cast_run"] = "TIMEOUT"
                except FileNotFoundError:
                    row["cast_run"] = "UNAVAILABLE"
            except Exception as exc:
                row["error"] = type(exc).__name__
        summary["evidence_status"] = "COLLECTED_REQUIRES_FEE_AND_TRANSFER_RECONCILIATION" if summary["candidates"] else "NO_CANDIDATES_IN_SCANNED_RANGES"
        if summary["scan_errors"]:
            summary["evidence_status"] += "_INCOMPLETE_SCAN"
    except Exception as exc:
        summary["error"] = type(exc).__name__
    finally:
        save("SUMMARY.json", summary)
        manifest = {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file() and f.name != "SHA256.json"}
        save("SHA256.json", manifest)
        print(json.dumps(summary, indent=2))
    return 1 if summary.get("error") or summary["scan_errors"] or any("error" in r for r in summary["candidates"]) else 0

if __name__ == "__main__":
    raise SystemExit(main())
