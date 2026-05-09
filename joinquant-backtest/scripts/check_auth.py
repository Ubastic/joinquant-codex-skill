#!/usr/bin/env python3
from __future__ import annotations

import argparse

from jq_client import JoinQuantWebClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Check JoinQuant cookie validity")
    parser.add_argument("--auth-file", default="joinquant_auth.local.json")
    parser.add_argument("--cookie", default=None)
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--proxy", default=None)
    args = parser.parse_args()

    auth = JoinQuantWebClient.load_auth(args.auth_file, args.cookie, args.user_agent)
    client = JoinQuantWebClient(cookie=auth["cookie"], user_agent=auth.get("user_agent") or None, proxy=args.proxy)
    try:
        draft = client.create_empty_algorithm(base_capital=100000)
    except Exception as exc:
        print(f"[FAIL] auth invalid: {exc}")
        return 1
    print("[OK] auth valid")
    print(f"[INFO] algorithm_id={draft.algorithm_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
