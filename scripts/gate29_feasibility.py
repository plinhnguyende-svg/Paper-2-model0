#!/usr/bin/env python3
"""Gate29 empirical feasibility decisions from actual event panel and coverage.

No significance testing, elasticity or causal coefficient can be inferred from
transaction-conditioned observed fees alone. Never silently turn B-1 into
transaction-index prestate, wallet addresses into producers, or q/Q into HHI.
"""
import argparse
from collections import Counter,defaultdict
import csv
from datetime import datetime,timezone
from decimal import Decimal
import json
from pathlib import Path


def load_json(p):
    return json.loads(p.read_text()) if p.exists() else {}


def read_rows(p):
    if not p.exists():
        return []
    with p.open(newline="") as f:
        return list(csv.DictReader(f))


def clean(x):
    return x not in (None,"","None","null","UNKNOWN","NOT_VERIFIED")


def empirical_diagnostics(out):
    status=load_json(out/"SUMMARY.json")
    coverage=load_json(out/"COVERAGE_MANIFEST.json")
    events=load_json(out/"ALL_DECODED_EVENTS.json")
    rows=read_rows(out/"EVENT_LEVEL_PANEL_ENRICHED.csv")
    if not rows:
        rows=read_rows(out/"EVENT_LEVEL_PANEL.csv")
    receipts=[r for r in rows if r.get("receipt_status")=="RECEIPT_ACCOUNTING_MATCH"]
    fee_known=[r for r in receipts if clean(r.get("effective_fee_rate"))]
    exact=[r for r in rows if r.get("transaction_index_aware_prestate")==
           "EXACT_PRE_TX_GATE25_VALIDATED"]
    bb=[r for r in rows if r.get("block_boundary_source")==
        "HISTORICAL_RPC_B_MINUS_ONE_AND_B"]
    time_known=[r for r in receipts if clean(r.get("timestamp_utc"))]
    unique_days=len(set(x["timestamp_utc"][:10] for x in time_known))
    token_freq=Counter(x.get("token","") for x in rows if clean(x.get("token")))
    actor_freq=Counter(x.get("actor","") for x in receipts if clean(x.get("actor")))
    kind=Counter(x.get("transaction_type","") for x in rows)
    config_records=[x for x in events if x.get("event") in (
      "DepositFeeScaleUpdated","DepositFeeRatioUpdated",
      "RedemptionFeeScaleUpdated","RedemptionFeeShift",
      "SingleAssetDepositRelativeFeeUpdated",
      "SingleAssetRedemptionRelativeFeeUpdated",
      "DustAssetRedemptionRelativeFeeUpdated")]
    config_by_type=Counter(x["event"] for x in config_records)
    qshares=[Decimal(x["B_minus_1_project_share"]) for x in bb if
             clean(x.get("B_minus_1_project_share"))]
    rates=[Decimal(x["effective_fee_rate"]) for x in fee_known]
    total_tx=len({r.get("tx_hash") for r in rows if clean(r.get("tx_hash"))})
    full=bool(coverage.get("pool_complete") and
              coverage.get("calculator_complete") and
              status.get("receipts_remaining")==0)
    types=[k for k in ("deposit","redemption") if kind[k]>0]
    numeric={
       "unique_trade_txs":total_tx,"trade_action_rows":len(rows),
       "trade_types":dict(kind),
       "canonical_matched_receipt_actions":len(receipts),
       "known_fee_rate_actions":len(fee_known),
       "distinct_tokens_with_trades":len(token_freq),
       "distinct_actor_wallets_in_matched_receipts":len(actor_freq),
       "dated_receipt_days":unique_days,
       "exact_tx_prestate_gate25_references":len(exact),
       "B_minus_1_inventory_snapshots":len(bb),
       "distinct_B_minus_1_project_share_values":len(set(qshares)),
       "min_B_minus_1_project_share":str(min(qshares)) if qshares else None,
       "max_B_minus_1_project_share":str(max(qshares)) if qshares else None,
       "distinct_exact_fee_rate_values":len(set(rates)),
       "min_effective_fee_rate":str(min(rates)) if rates else None,
       "max_effective_fee_rate":str(max(rates)) if rates else None,
       "observed_fee_parameter_updates":dict(config_by_type),
       "unique_parameter_update_transactions":len(set(x["tx_hash"] for x in config_records)),
       "unique_fee_rate_by_token":{
          k:len(set(x["effective_fee_rate"] for x in fee_known if x["token"]==k))
          for k,v in token_freq.most_common(10)},
       "treat_q_share_as_HHI":False,
       "observed_failed_attempts_or_nonparticipants":False
    }
    conditions={
       "event_census_complete":coverage.get("pool_complete",False),
       "all_config_address_census_complete":coverage.get("calculator_complete",False),
       "all_discovered_trade_receipts_checked":status.get("receipts_remaining")==0,
       "all_trade_rows_have_canonical_accounting":len(rows)>0 and len(receipts)==len(rows),
       "all_trade_rows_have_exact_pre_transaction_state":len(rows)>0 and
           all(x.get("transaction_index_aware_prestate")==
               "EXACT_PRE_TX_GATE25_VALIDATED" for x in rows),
       "has_both_trade_directions":len(types)==2,
       "multiple_fee_schedule_changes_observed":len(set(x["tx_hash"] for x in config_records))>=2,
       "rich_within_token_observations":any(v>=20 for v in token_freq.values()),
       "counterfactual_behavior_identified":False,
       "causal_fee_elasticity_identified":False,
       "full_project_inventory_vectors_for_actual_HHI":False
    }
    steps={
      "descriptive_accounting":"Proceed on verified receipt rows only; report range and censoring",
      "replay_mechanical":"Allowed once initial state/fees and implementation are verified for each transaction path; hold observed arrivals fixed and clearly label conditional accounting",
      "behavioral_reduced_form":"Do not estimate as a causal claim on transaction-conditioned fee rates. Assess policy-change variation, demand opportunity set, project/time effects, and common market shocks.",
      "behavioral_simulation":"Only under independently justified elasticities or transparent sensitivity assumptions",
      "analytical_extension":"Optional; retain Gate20/28 as explanatory sensitivity, not primary identified result"
    }
    if not full:
        decision="EMPIRICAL_FEASIBILITY_PENDING_FULL_COVERAGE"
    elif not conditions["all_trade_rows_have_exact_pre_transaction_state"]:
        decision="EVENT_CENSUS_ESTABLISHED_PRESTATE_REPLAY_INCOMPLETE"
    elif not conditions["multiple_fee_schedule_changes_observed"]:
        decision="DESCRIPTIVE_AND_MECHANICAL_PRIMARY_LIMITED_POLICY_VARIATION"
    else:
        decision="DESCRIPTIVE_AND_MECHANICAL_PRIMARY_CAUSAL_IDENTIFICATION_AUDIT_REQUIRED"
    result=dict(
       collected_at_utc=datetime.now(timezone.utc).isoformat(),
       decision=decision, evidence_type="ACTUAL_ONCHAIN_RECORDS_WITH_EXPLICIT_MISSINGNESS",
       mathematical_mode="EMPIRICAL_FIRST_WITH_OPTIONAL_ANALYTICAL_MODEL",
       full_history_claim_permitted=full,
       descriptive_statistics=numeric,
       prerequisite_checks=conditions,
       recommended_empirical_strategy=steps,
       identification_threats=[
          "Fee rates and project composition are mechanically jointly determined by transaction arrivals",
          "Transactions themselves update subsequent inventory state and dynamic fees",
          "Receipts condition on successful execution; non-participants and failed intentions unobserved",
          "Admin-controlled fee schedule changes may coincide with unobserved market shocks",
          "Pool receiver wallet or protocol fee recipient is not necessarily carbon producer",
          "Block-boundary inventory cannot be labeled transaction-index-aware prestate",
          "Actual pool may have >2 projects; q/Q alone cannot identify observed HHI",
          "Whole-pool policy simulation with different volume/routing requires behavioral structural assumptions"
       ])
    save=out/"EMPIRICAL_FEASIBILITY.json"
    save.write_text(json.dumps(result,indent=2)+"\n")
    lines=[
        "# Gate29 Empirical Feasibility Audit",
        "",
        f"**Decision:** {decision}",
        "",
        "All counts below describe actually retrieved Base-chain records, not a probabilistic or representative sample unless complete coverage is separately demonstrated.",
        "",
        f"- Pool block coverage complete: **{conditions['event_census_complete']}**",
        f"- Calculator history complete for discovered addresses: **{conditions['all_config_address_census_complete']}**",
        f"- Trade action rows: **{len(rows)}**; distinct transactions **{total_tx}**",
        f"- Canonically reconciled trade receipt rows: **{len(receipts)}**",
        f"- Exact transaction-index prestate rows (Gate25 references): **{len(exact)}**",
        f"- Historical B-1/B inventory snapshots, explicitly not exact prestate: **{len(bb)}**",
        f"- Fee parameter update events in scanned windows: **{sum(config_by_type.values())}**",
        f"- Matched actor wallets **{len(actor_freq)}**, distinct tokens **{len(token_freq)}**, observed days **{unique_days}**",
        "",
        "## Identification",
        "",
        "Mechanical accounting replay under fixed historical arrivals does not identify participation, entry, outside-option selection or producer output response. An observed conditional fee rate is endogenous to the pre-transaction project inventory and transaction quantity. Policy-setter fee changes are not automatically exogenous.",
        "",
        "## Empirical-first next analysis",
        "",
        "1. Finish missing block ranges in the coverage ledger using resumable historical RPC log queries.",
        "2. Reconcile all new trade receipts, historical token/project metadata, configuration setters and pool versions.",
        "3. Extend exact transaction-index-aware prestate beyond the two already verified historical examples. Do not substitute B-1 or B-end.",
        "4. Construct complete inventory vector for actual project HHI (rather than synthetic two-project HHI).",
        "5. Only if policy changes/variation and credible comparison groups exist, pre-register a behavioral event study or structural demand exercise. Otherwise publish descriptive fee accounting plus mechanical counterfactual replay.",
        "",
        "## Explicit limits",
        "",
        "No actor wallet is automatically identified with the physical producer. No commercial beta, early producer liquidity, non-participant opportunity set, additional carbon removal or causal response has been established.",
        ""
    ]
    (out/"EMPIRICAL_FEASIBILITY.md").write_text("\n".join(lines))
    print(json.dumps({k:v for k,v in result.items()
                      if k in ("decision","full_history_claim_permitted","descriptive_statistics")},
                     indent=2),flush=True)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    args=p.parse_args()
    empirical_diagnostics(Path(args.out))


if __name__=="__main__":
    main()
