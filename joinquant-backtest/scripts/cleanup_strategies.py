#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import List, Set

from jq_client import JoinQuantWebClient


def _prefix_variants(prefix: str) -> List[str]:
    variants: Set[str] = {prefix}
    try:
        variants.add(prefix.encode("utf-8").decode("latin1"))
    except Exception:
        pass
    return [x for x in variants if x]


def _chunks(items: List[str], n: int):
    for i in range(0, len(items), n):
        yield items[i : i + n]


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete JoinQuant strategy drafts by name prefix")
    parser.add_argument("--auth-file", default="joinquant_auth.local.json")
    parser.add_argument("--cookie", default=None)
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    auth = JoinQuantWebClient.load_auth(args.auth_file, args.cookie, args.user_agent)
    client = JoinQuantWebClient(cookie=auth["cookie"], user_agent=auth.get("user_agent") or None, proxy=args.proxy)
    rows = client.list_all_algorithms()
    variants = _prefix_variants(args.prefix)
    hits = [r for r in rows if any((r.get("name") or "").startswith(v) for v in variants)]
    print(f"[INFO] total_strategies={len(rows)} matched={len(hits)} prefix={args.prefix!r}")
    for r in hits:
        print(f"  - {r.get('algorithm_id')} {r.get('name')}")

    if args.dry_run:
        print("[DONE] dry-run only")
        return 0
    if not args.yes:
        print("[STOP] add --yes to execute deletion")
        return 2

    deleted = 0
    for grp in _chunks([r["algorithm_id"] for r in hits], max(1, args.batch_size)):
        payload = client.delete_algorithms(grp)
        deleted += len(grp)
        print(f"[DEL] batch={len(grp)} status={payload.get('status')} code={payload.get('code')}")

    with open(args.auth_file, "w", encoding="utf-8") as f:
        json.dump({"cookie": client.get_cookie_string(), "user_agent": auth.get("user_agent") or ""}, f, ensure_ascii=False, indent=2)
    print(f"[DONE] deleted={deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
