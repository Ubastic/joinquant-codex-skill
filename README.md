# JoinQuant Codex Skill

Open-source Codex skill for operating JoinQuant/Jukuan web backtests with cookie-based authentication.

The skill can help an agent:

- write and adjust JoinQuant strategy scripts
- run one or many web backtests
- fetch and scan backtest logs
- summarize metrics and flag invalid runs
- clean up temporary JoinQuant strategy drafts

## Install

Install the `joinquant-backtest` skill folder into your Codex skills directory, or install from this repository path with your skill installer.

```bash
mkdir -p ~/.codex/skills
cp -R joinquant-backtest ~/.codex/skills/
```

## Secrets

Do not commit local JoinQuant credentials. The scripts support local-only auth through:

- `joinquant_auth.local.json`
- `JOINQUANT_COOKIE`
- `JOINQUANT_USER_AGENT`
- `JOINQUANT_PROXY`

`joinquant_auth.local.json` should look like:

```json
{
  "cookie": "key=value; key2=value2",
  "user_agent": "browser user agent"
}
```

## Example

```bash
cd joinquant-backtest
python scripts/check_auth.py --auth-file joinquant_auth.local.json --proxy "$JQ_PROXY"
python scripts/run_backtest.py --strategy-file jukuan/champion.py --fetch-log
```

Always inspect logs before trusting backtest metrics.
