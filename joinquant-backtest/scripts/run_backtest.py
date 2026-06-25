#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from jq_client import JoinQuantWebClient, extract_log_text, scan_log_text


def _fetch_all_log_pages(client: JoinQuantWebClient, backtest_id: str, token: str, page_size: int = 100) -> dict:
    payloads = []
    offset = 0
    while True:
        payload = client.get_log(backtest_id, token, offset=offset)
        payloads.append(payload)
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        if not isinstance(data, dict) or bool(data.get("max")):
            break
        lines = data.get("logArr", [])
        if not isinstance(lines, list) or not lines:
            break
        offset += max(int(page_size), 1)

    if len(payloads) == 1:
        return payloads[0]

    merged_lines = []
    for page in payloads:
        data = page.get("data", {}) if isinstance(page, dict) else {}
        lines = data.get("logArr", []) if isinstance(data, dict) else []
        if isinstance(lines, list):
            merged_lines.extend(lines)

    merged = dict(payloads[0])
    merged_data = dict(merged.get("data", {}) if isinstance(merged.get("data"), dict) else {})
    merged_data["logArr"] = merged_lines
    merged_data["page_count"] = len(payloads)
    merged_data["page_offsets"] = [idx * max(int(page_size), 1) for idx in range(len(payloads))]
    merged_data["max"] = True
    merged["data"] = merged_data
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a JoinQuant web backtest")
    parser.add_argument("--strategy-file", required=True)
    parser.add_argument("--name", default=None)
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
    parser.add_argument("--fetch-log", action="store_true", help="Fetch and scan log before saving final JSON")
    parser.add_argument("--out", default=None)
    parser.add_argument("--strategy-variant-name", default=None, help="Optional local variant identifier to persist in result JSON")
    parser.add_argument("--use-credit", action="store_true", help="Add useCredit=1 to the build request")
    args = parser.parse_args()

    auth = JoinQuantWebClient.load_auth(args.auth_file, args.cookie, args.user_agent)
    client = JoinQuantWebClient(cookie=auth["cookie"], user_agent=auth.get("user_agent") or None, proxy=args.proxy)

    strategy_path = Path(args.strategy_file)
    code = strategy_path.read_text(encoding="utf-8")
    run_name = args.name or f"jq-{strategy_path.stem}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out_path = Path(args.out) if args.out else Path("results") / "joinquant" / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = client.run_backtest(
            code=code,
            name=run_name,
            start_time=args.start_date,
            end_time=args.end_date,
            base_capital=args.base_capital,
            frequency=args.frequency,
            py_version=args.py_version,
            wait_timeout_sec=args.wait_timeout_sec,
            poll_interval=args.poll_interval,
            use_credit=args.use_credit,
        )
        if args.fetch_log:
            log_payload = _fetch_all_log_pages(client, result["backtest_id"], result["token"])
            log_text = extract_log_text(log_payload)
            result["log"] = log_payload
            result["log_scan"] = scan_log_text(log_text)
        result["ok"] = True
        result["name"] = run_name
        result["strategy_file"] = str(strategy_path.resolve())
        result["strategy_variant_name"] = args.strategy_variant_name or strategy_path.stem
        result["requested_start_date"] = args.start_date
        result["requested_end_date"] = args.end_date
        result["requested_base_capital"] = args.base_capital
    except Exception as exc:
        failure_payload = {
            "ok": False,
            "strategy_file": str(strategy_path),
            "name": run_name,
            "strategy_variant_name": args.strategy_variant_name or strategy_path.stem,
            "start_date": args.start_date,
            "end_date": args.end_date,
            "base_capital": args.base_capital,
            "frequency": args.frequency,
            "py_version": args.py_version,
            "error": str(exc),
            "failed_at": datetime.now().isoformat(timespec="seconds"),
        }
        fail_path = out_path.with_suffix(".error.json")
        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(failure_payload, f, ensure_ascii=False, indent=2)
        print(f"[FAIL] backtest failed: {exc}")
        print(f"[INFO] failure details saved: {fail_path}")
        return 1
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open(args.auth_file, "w", encoding="utf-8") as f:
        json.dump({"cookie": client.get_cookie_string(), "user_agent": auth.get("user_agent") or ""}, f, ensure_ascii=False, indent=2)

    stats = result.get("stats", {}).get("data", {})
    print(f"[OK] backtest done: {out_path}")
    print(f"[INFO] algorithm_id={result.get('algorithm_id')} backtest_id={result.get('backtest_id')}")
    print(
        "[SUMMARY] "
        f"annual_algo_return={stats.get('annual_algo_return')} "
        f"sharpe={stats.get('sharpe')} "
        f"max_drawdown={stats.get('max_drawdown')}"
    )
    if "log_scan" in result:
        print(f"[LOG] has_critical={result['log_scan']['has_critical']} patterns={result['log_scan']['matched_patterns']}")
    else:
        print("[WARN] log not fetched. Run fetch_log.py before trusting metrics.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
