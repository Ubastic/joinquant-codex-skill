# JoinQuant Strategy Guardrails

## Compatibility

- Keep strategy scripts self-contained. JoinQuant will not have local project imports unless explicitly uploaded.
- Use JoinQuant APIs available in the target runtime.
- Prefer Python 3 unless the user has a legacy reason for Python 2.
- Use explicit start/end dates and capital in the backtest command rather than hardcoding them in strategy code.

## Order Safety

- A-share orders must respect 100-share lots for normal stock trading.
- Avoid sending tiny target changes; add a rebalance threshold to prevent zero-share or sub-lot orders.
- Before submitting sell orders, account for current position and lot size.
- Handle suspended securities and limit-up/limit-down cases defensively.
- Avoid repeated `target=0` orders when already flat.

## Smoke Testing

Before long runs or batch searches:

1. Run a recent 1-2 year smoke range.
2. Fetch logs immediately.
3. Confirm expected trades occurred and no critical log patterns exist.
4. Only then run longer ranges or batches.
