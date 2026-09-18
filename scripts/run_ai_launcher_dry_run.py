from __future__ import annotations

import json
from pathlib import Path

from paper2_model0.ai.launcher import build_dry_run_contract


OUTPUT = Path("outputs/ai_launcher_dry_run_v0.1/launcher_plan.json")


def main() -> None:
    plan = build_dry_run_contract()
    if plan["job_count"] != 15:
        raise AssertionError("launcher dry run did not produce exactly 15 jobs")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(plan, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "AI launcher dry-run only: "
        f"{plan['job_count']} locked jobs; no training executed."
    )


if __name__ == "__main__":
    main()
