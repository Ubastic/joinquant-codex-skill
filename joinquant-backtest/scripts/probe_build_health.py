#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from jq_client import JoinQuantWebClient


MINIMAL_STRATEGY = """from jqdata import *


def initialize(context):
    set_benchmark('000300.XSHG')
    run_daily(trade, time='09:30', reference_security='000300.XSHG')


def trade(context):
    pass
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe JoinQuant build health with a minimal strategy")
    parser.add_argument("--auth-file", default="joinquant_auth.local.json")
    parser.add_argument("--cookie", default=None)
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--sleep-sec", type=float, default=30.0)
    parser.add_argument("--start-date", default="2024-07-02")
    parser.add_argument("--end-date", default="2024-07-15")
    parser.add_argument("--base-capital", type=int, default=10000000)
    parser.add_argument("--frequency", default="day", choices=["day", "minute"])
    parser.add_argument("--py-version", default="3", choices=["2", "3"])
    parser.add_argument("--out", default=None)
    parser.add_argument("--use-credit", action="store_true", help="Add useCredit=1 to the build request")
    args = parser.parse_args()

    auth = JoinQuantWebClient.load_auth(args.auth_file, args.cookie, args.user_agent)
    client = JoinQuantWebClient(cookie=auth["cookie"], user_agent=auth.get("user_agent") or None, proxy=args.proxy)

    out_path = Path(args.out) if args.out else Path("results") / "joinquant" / f"build_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    success = False
    for attempt in range(1, max(args.attempts, 1) + 1):
        started_at = datetime.now().isoformat(timespec="seconds")
        run_name = f"jq-build-probe-{datetime.now().strftime('%m%d-%H%M%S')}-{attempt}"
        record = {
            "attempt": attempt,
            "started_at": started_at,
            "run_name": run_name,
            "ok": False,
        }
        try:
            draft = client.create_empty_algorithm(base_capital=args.base_capital)
            record["algorithm_id"] = draft.algorithm_id
            client.save_algorithm(
                draft,
                MINIMAL_STRATEGY,
                run_name,
                args.start_date,
                args.end_date,
                args.base_capital,
                args.frequency,
                args.py_version,
            )
            build_payload = client.build_backtest(
                draft,
                MINIMAL_STRATEGY,
                run_name,
                args.start_date,
                args.end_date,
                args.base_capital,
                args.frequency,
                args.py_version,
                max_retries=0,
                use_credit=args.use_credit,
            )
            record["ok"] = True
            record["build_payload"] = build_payload
            success = True
        except Exception as exc:
            record["error"] = str(exc)
        record["finished_at"] = datetime.now().isoformat(timespec="seconds")
        records.append(record)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "attempts": args.attempts,
                    "sleep_sec": args.sleep_sec,
                    "start_date": args.start_date,
                    "end_date": args.end_date,
                    "base_capital": args.base_capital,
                    "success": success,
                    "records": records,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"[ATTEMPT] {attempt}/{args.attempts} ok={record['ok']} started={started_at}")
        if success:
            break
        if attempt < args.attempts:
            time.sleep(max(args.sleep_sec, 0.0))

    with open(args.auth_file, "w", encoding="utf-8") as f:
        json.dump({"cookie": client.get_cookie_string(), "user_agent": auth.get("user_agent") or ""}, f, ensure_ascii=False, indent=2)

    print(f"[DONE] probe={out_path}")
    print(f"[RESULT] success={success}")
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
