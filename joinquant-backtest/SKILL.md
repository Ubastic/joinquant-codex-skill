---
name: joinquant-backtest
description: Operate JoinQuant/Jukuan web backtests with cookie-based authentication. Use when Codex needs to create or modify JoinQuant strategy scripts, run one or many backtests through the JoinQuant web API, check authentication, fetch and inspect backtest logs, summarize metrics, clean up test strategies, or diagnose JoinQuant order/runtime failures without exposing credentials.
---

# JoinQuant Backtest

## Core Rules

- Treat all auth material as local-only secrets. Never commit cookies, HAR files, auth JSON, usernames, passwords, proxy credentials, raw logs that may include account details, or generated result archives.
- Prefer cookie auth from `joinquant_auth.local.json`, `JOINQUANT_COOKIE`, or explicit `--cookie`. Do not ask for plain credentials unless the user explicitly chooses that workflow outside this skill.
- After every JoinQuant backtest, fetch and inspect the log before trusting metrics. Reject or flag results with tracebacks, runtime errors, failed orders, zero-share orders, non-lot orders, suspended stocks, limit-up/limit-down failures, or other execution warnings.
- Start with a short smoke range before long or batch runs when strategy code changed.
- Use a proxy when required by the user's environment: pass `--proxy "$JQ_PROXY"` or set `JOINQUANT_PROXY`.
- If JoinQuant responds with `msg=50000` on build, resubmit with `useCredit=1` by passing `--use-credit` to `run_backtest.py`.

## Quick Start

Copy or use the bundled scripts directly from `scripts/`.

```bash
python scripts/check_auth.py --auth-file joinquant_auth.local.json --proxy "$JQ_PROXY"

python scripts/run_backtest.py \
  --auth-file joinquant_auth.local.json \
  --proxy "$JQ_PROXY" \
  --strategy-file jukuan/champion.py \
  --name smoke-test \
  --start-date 2025-01-02 \
  --end-date 2026-04-17 \
  --wait-timeout-sec 1200

python scripts/fetch_log.py \
  --auth-file joinquant_auth.local.json \
  --proxy "$JQ_PROXY" \
  --result-json results/joinquant/backtest_YYYYmmdd_HHMMSS.json \
  --scan
```

## Workflow

1. Inspect the target strategy file for JoinQuant compatibility. Keep strategy code self-contained and compatible with JoinQuant's Python runtime.
2. Validate auth with `scripts/check_auth.py`.
3. Run a smoke backtest with `scripts/run_backtest.py`.
4. Immediately run `scripts/fetch_log.py --result-json ... --scan`.
5. Treat the run as usable only if `log_scan.has_critical` is false and the strategy performed expected trades.
6. For candidate searches, use `scripts/batch_backtest.py`, then fetch logs for finalists before selecting a champion.
7. Clean throwaway strategies with `scripts/cleanup_strategies.py --dry-run` first, then add `--yes`.

## Script Guide

- `scripts/jq_client.py`: reusable cookie-authenticated JoinQuant Web API client.
- `scripts/extract_auth_from_har.py`: extract cookie and user-agent from a local browser HAR into `joinquant_auth.local.json`; keep the output untracked.
- `scripts/check_auth.py`: verify cookie validity by opening a new strategy draft.
- `scripts/run_backtest.py`: upload strategy code, build a backtest, wait for completion, fetch stats/result page, save JSON, and update cookie cache.
- `scripts/fetch_log.py`: fetch raw logs by `backtest_id` and token, scan for critical warnings/errors, and optionally save JSON.
- `scripts/batch_backtest.py`: run a glob of strategies, write per-run JSON and a CSV summary, and rank candidates by annual return, Sharpe, and drawdown constraints.
- `scripts/cleanup_strategies.py`: list and delete JoinQuant strategy drafts by name prefix.

## References

- Read `references/joinquant_workflow.md` for operational details, command patterns, result interpretation, and log review criteria.
- Read `references/strategy_guardrails.md` before writing or modifying JoinQuant strategy code.
