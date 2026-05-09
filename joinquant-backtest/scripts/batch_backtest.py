#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from glob import glob
from pathlib import Path

from jq_client import JoinQuantWebClient, extract_log_text, scan_log_text


def _f(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def main() -> int:
    parser = argparse.ArgumentParser(description="Run many JoinQuant strategy backtests and rank candidates")
    parser.add_argument("--strategy-glob", default="jukuan/*.py")
    parser.add_argument("--name-prefix", default="jq")
    parser.add_argument("--start-date", default="2024-01-02")
    parser.add_argument("--end-date", default="2026-04-17")
    parser.add_argument("--base-capital", type=int, default=100000)
    parser.add_argument("--frequency", default="day", choices=["day", "minute"])
    parser.add_argument("--py-version", default="3", choices=["2", "3"])
    parser.add_argument("--auth-file", default="joinquant_auth.local.json")
    parser.add_argument("--cookie", default=None)
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--wait-timeout-sec", type=int, default=600)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--min-annual-return", type=float, default=0.10)
    parser.add_argument("--max-drawdown", type=float, default=0.10)
    parser.add_argument("--fetch-log", action="store_true", help="Fetch and scan logs for every candidate")
    parser.add_argument("--out-csv", default=None)
    parser.add_argument("--out-json", default=None)
    args = parser.parse_args()

    auth = JoinQuantWebClient.load_auth(args.auth_file, args.cookie, args.user_agent)
    client = JoinQuantWebClient(cookie=auth["cookie"], user_agent=auth.get("user_agent") or None, proxy=args.proxy)
    strategy_files = sorted(glob(args.strategy_glob))
    if not strategy_files:
        print(f"[FAIL] no strategy files matched: {args.strategy_glob}")
        return 1

    run_dir = Path("results") / "joinquant"
    run_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for path in strategy_files:
        p = Path(path)
        run_name = f"{args.name_prefix}-{p.stem}-{datetime.now().strftime('%m%d-%H%M%S')}"
        try:
            result = client.run_backtest(
                code=p.read_text(encoding="utf-8"),
                name=run_name,
                start_time=args.start_date,
                end_time=args.end_date,
                base_capital=args.base_capital,
                frequency=args.frequency,
                py_version=args.py_version,
                wait_timeout_sec=args.wait_timeout_sec,
                poll_interval=args.poll_interval,
            )
            log_has_critical = ""
            log_patterns = ""
            if args.fetch_log:
                log_payload = client.get_log(result["backtest_id"], result["token"])
                result["log"] = log_payload
                result["log_scan"] = scan_log_text(extract_log_text(log_payload))
                log_has_critical = result["log_scan"]["has_critical"]
                log_patterns = "|".join(result["log_scan"]["matched_patterns"])

            stats = result.get("stats", {}).get("data", {})
            annual = _f(stats.get("annual_algo_return"))
            sharpe = _f(stats.get("sharpe"))
            max_dd = _f(stats.get("max_drawdown"))
            constraint_met = annual >= args.min_annual_return and max_dd <= args.max_drawdown and log_has_critical is not True
            save_path = run_dir / f"{p.stem}_{result.get('backtest_id')}.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            rec = {
                "strategy_file": str(p),
                "strategy_name": run_name,
                "algorithm_id": result.get("algorithm_id"),
                "backtest_id": result.get("backtest_id"),
                "annual_algo_return": annual,
                "sharpe": sharpe,
                "max_drawdown": max_dd,
                "turnover_rate": _f(stats.get("turnover_rate")),
                "alpha": _f(stats.get("alpha")),
                "information": _f(stats.get("information")),
                "log_has_critical": log_has_critical,
                "log_patterns": log_patterns,
                "constraint_met": constraint_met,
                "result_json": str(save_path),
                "error": "",
            }
            print(f"[DONE] {p.name} annual={annual:.4f} sharpe={sharpe:.4f} max_dd={max_dd:.4f} ok={constraint_met}")
        except Exception as exc:
            rec = {"strategy_file": str(p), "strategy_name": run_name, "algorithm_id": "", "backtest_id": "", "annual_algo_return": "", "sharpe": "", "max_drawdown": "", "turnover_rate": "", "alpha": "", "information": "", "log_has_critical": "", "log_patterns": "", "constraint_met": False, "result_json": "", "error": str(exc)}
            print(f"[FAIL] {p.name}: {exc}")
        records.append(rec)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = Path(args.out_csv) if args.out_csv else run_dir / f"champion_search_{now}.csv"
    fieldnames = ["strategy_file", "strategy_name", "algorithm_id", "backtest_id", "annual_algo_return", "sharpe", "max_drawdown", "turnover_rate", "alpha", "information", "log_has_critical", "log_patterns", "constraint_met", "result_json", "error"]
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    valid = [r for r in records if isinstance(r.get("annual_algo_return"), (int, float))]
    qualified = [r for r in valid if r.get("constraint_met") is True]
    best = None
    if qualified:
        best = sorted(qualified, key=lambda x: (x["annual_algo_return"], x["sharpe"], -x["max_drawdown"]), reverse=True)[0]
    elif valid:
        best = sorted(valid, key=lambda x: (x["annual_algo_return"], x["sharpe"], -x["max_drawdown"]), reverse=True)[0]

    out_json = Path(args.out_json) if args.out_json else run_dir / f"champion_best_{now}.json"
    if best:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(best, f, ensure_ascii=False, indent=2)

    with open(args.auth_file, "w", encoding="utf-8") as f:
        json.dump({"cookie": client.get_cookie_string(), "user_agent": auth.get("user_agent") or ""}, f, ensure_ascii=False, indent=2)

    print(f"[DONE] csv={out_csv}")
    if best:
        print(f"[BEST] {best['strategy_file']} annual={best['annual_algo_return']} sharpe={best['sharpe']} max_dd={best['max_drawdown']}")
        print(f"[DONE] best={out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
