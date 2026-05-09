#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jq_client import JoinQuantWebClient, extract_log_text, scan_log_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and scan a JoinQuant backtest log")
    parser.add_argument("--auth-file", default="joinquant_auth.local.json")
    parser.add_argument("--cookie", default=None)
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--result-json", default=None, help="JSON produced by run_backtest.py")
    parser.add_argument("--backtest-id", default=None)
    parser.add_argument("--token", default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    source = {}
    if args.result_json:
        with open(args.result_json, "r", encoding="utf-8") as f:
            source = json.load(f)
    backtest_id = args.backtest_id or source.get("backtest_id")
    token = args.token or source.get("token")
    if not backtest_id or not token:
        print("[FAIL] provide --result-json containing backtest_id/token or pass --backtest-id and --token")
        return 1

    auth = JoinQuantWebClient.load_auth(args.auth_file, args.cookie, args.user_agent)
    client = JoinQuantWebClient(cookie=auth["cookie"], user_agent=auth.get("user_agent") or None, proxy=args.proxy)
    try:
        payload = client.get_log(backtest_id, token, offset=args.offset)
    except Exception as exc:
        print(f"[FAIL] fetch log failed: {exc}")
        return 1

    text = extract_log_text(payload)
    scan = scan_log_text(text) if args.scan else None
    out_obj = {"backtest_id": backtest_id, "offset": args.offset, "log": payload}
    if scan is not None:
        out_obj["log_scan"] = scan

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(out_obj, f, ensure_ascii=False, indent=2)
        print(f"[OK] log saved: {out}")

    print(text[:4000])
    if len(text) > 4000:
        print("\n[INFO] log truncated in console; use --out to save full payload")
    if scan is not None:
        print(f"[SCAN] has_critical={scan['has_critical']} patterns={scan['matched_patterns']}")
        return 2 if scan["has_critical"] else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
