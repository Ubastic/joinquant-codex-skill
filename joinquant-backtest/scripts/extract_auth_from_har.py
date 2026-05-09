#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jq_client import extract_joinquant_auth_from_har


def _mask_cookie(cookie: str) -> str:
    return "; ".join(part.split("=", 1)[0] for part in cookie.split(";") if "=" in part)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract JoinQuant cookie and user-agent from a local HAR")
    parser.add_argument("--har", required=True)
    parser.add_argument("--out", default="joinquant_auth.local.json")
    args = parser.parse_args()

    auth = extract_joinquant_auth_from_har(args.har)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(auth, f, ensure_ascii=False, indent=2)
    print(f"[OK] auth saved: {out}")
    print(f"[INFO] request_url={auth.get('request_url')}")
    print(f"[INFO] cookie_keys={_mask_cookie(auth.get('cookie', ''))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
