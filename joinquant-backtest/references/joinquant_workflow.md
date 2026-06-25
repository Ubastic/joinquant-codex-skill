# JoinQuant Backtest Workflow

## Authentication

Supported local auth sources, in priority order:

1. CLI args: `--cookie`, `--user-agent`
2. Environment: `JOINQUANT_COOKIE`, `JOINQUANT_USER_AGENT`, `JOINQUANT_PROXY`
3. Auth JSON: `joinquant_auth.local.json`

Auth JSON format:

```json
{
  "cookie": "key=value; key2=value2",
  "user_agent": "browser user agent"
}
```

Create it from a local browser HAR only when the user provides a HAR:

```bash
python scripts/extract_auth_from_har.py --har path/to/joinquant.har --out joinquant_auth.local.json
```

Never commit auth JSON or HAR files.

## Standard Commands

Check auth:

```bash
python scripts/check_auth.py --auth-file joinquant_auth.local.json --proxy "$JQ_PROXY"
```

Run one strategy:

```bash
python scripts/run_backtest.py \
  --auth-file joinquant_auth.local.json \
  --proxy "$JQ_PROXY" \
  --strategy-file jukuan/my_strategy.py \
  --name jq-smoke-my-strategy \
  --start-date 2025-01-02 \
  --end-date 2026-04-17 \
  --wait-timeout-sec 1200 \
  --poll-interval 2
```

Credit-based backtest (`msg=50000`):

JoinQuant's build endpoint may return `status=2` with `msg=50000` when the request must include `useCredit=1`. In that case, rerun with the `--use-credit` flag:

```bash
python scripts/run_backtest.py \
  --auth-file joinquant_auth.local.json \
  --proxy "$JQ_PROXY" \
  --strategy-file jukuan/my_strategy.py \
  --name jq-smoke-my-strategy \
  --start-date 2025-01-02 \
  --end-date 2026-04-17 \
  --wait-timeout-sec 1200 \
  --poll-interval 2 \
  --use-credit
```

The client automatically retries a few times on retryable build responses (`status=2`, `code=20000` or `msg=50000`), but you should still pass `--use-credit` when the account/run requires credit mode.

Fetch and scan logs:

```bash
python scripts/fetch_log.py \
  --auth-file joinquant_auth.local.json \
  --proxy "$JQ_PROXY" \
  --result-json results/joinquant/backtest_20260509_120000.json \
  --scan
```

Batch search:

```bash
python scripts/batch_backtest.py \
  --auth-file joinquant_auth.local.json \
  --proxy "$JQ_PROXY" \
  --strategy-glob 'jukuan/search/*.py' \
  --name-prefix jq-search \
  --start-date 2025-01-02 \
  --end-date 2026-04-17 \
  --min-annual-return 0.10 \
  --max-drawdown 0.10
```

Cleanup:

```bash
python scripts/cleanup_strategies.py --auth-file joinquant_auth.local.json --prefix jq-search --dry-run
python scripts/cleanup_strategies.py --auth-file joinquant_auth.local.json --prefix jq-search --yes
```

## Required Log Review

Metrics alone are insufficient. Always inspect logs after a run.

Critical patterns include:

- `Traceback`, `Exception`, `ERROR`, `错误`, `异常`
- order failures: `下单失败`, `开仓数量不能小于100`, `平仓数量不能小于100`, `数量为0`
- execution blockers: `停牌`, `涨停`, `跌停`, `无法成交`, `不能买入`, `不能卖出`
- invalid data/runtime warnings that make trades unreliable

If critical patterns are present, report the backtest as invalid or requiring investigation even if annual return looks good.

## Result Files

`run_backtest.py` saves JSON with:

- `algorithm_id`
- `backtest_id`
- `token`
- `runtime`
- `stats`
- `result_page_0`
- optional `log` and `log_scan` when `--fetch-log` is used

The `token` is needed to fetch logs later. Treat result JSON as local output and avoid committing it.
