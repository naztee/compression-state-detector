# Compression Observatory
Python / Streamlit lifecycle detector, free CoinGecko API, CCXT perpetual universe, SQLite daily tracking. No trading, paid APIs, paid hosting or QuantConnect.

## Run locally
Python 3.10–3.12 recommended (3.11 for cloud).

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Windows activation: `.venv\Scripts\activate`. On Mac, double-click `Launch.command` after installation. Open http://localhost:8501. To stop, close the terminal or press Ctrl+C.

The detector supports any CoinGecko ID for which complete 84-day daily USD price, historical circulating MC and reported volume are returned. Search and confirm the ID. CSV import accepts genuine daily `date,price,market_cap,volume` records with positive values, ISO dates and no duplicates. Never label synthetic fixtures as market observations.

## Automated scanner
Bybit identities are automatically cross-checked using CoinGecko’s explicit venue contract-ID → coin-ID links and CCXT’s native contract IDs. Ambiguous or missing links stay unverified. Reviewed overrides in `mappings.json` take precedence. Other venues currently require reviewed overrides. Review `mappings.json` before scanning. Keys are exact exchange bases, values are verified CoinGecko IDs. BTC, ETH, SOL are seeded as identity examples; small-cap mappings without provider contract links must be reviewed and added. Suggestions appear in `data/universe_latest.csv` after a scan. They are NOT auto-approved because ticker collisions and redenominations can corrupt research. Unlinked contracts are retained in coverage reports and skipped; coverage is not guaranteed complete. Inactive contracts are retained but not scanned.

```sh
python scanner.py --exchange bybit --limit 25
python -m pytest -q
```

Binance USDM and OKX are alternative explicit exchange choices; no silent venue fallback. Limits are API-budget controls, not complete-market claims. Coins meeting current MC $1M–$20M are prioritized, followed by other mapped contracts. Within each tier, least-recently scanned assets come first. The 25-coin default is a bounded daily batch, not a promise to refresh the entire supported market each day; lower-priority assets can be delayed by continual high-priority demand. Historical classifications use each historical MC. All observations have completed UTC sample dates. The dashboard is updated when the database is refreshed.

Optional **FREE Demo** key: set `COINGECKO_DEMO_API_KEY` in the environment. Only api.coingecko.com is used; no Pro endpoint. Unauthenticated access can be limited. A request failure is shown, never replaced by invented values. Cache TTL is 6h for history and 24h for identities. Provider quotas and access policies can change. Default 25 histories/day plus lookup calls, paced at 12 seconds between requests; lower limit or increase delay for your free allowance. Logs show attempted and successful coverage. Do not enable paid quota overage.

## Free deployment
1. Sign in to GitHub and create a **public** repository (review code/data visibility). Push this directory to its default branch. No billing required for this workflow's standard public-repository runner. Private repositories are explicitly disabled by the workflow to avoid consuming paid runner minutes.
2. In repository Settings → Actions, allow workflow read/write permissions. Scheduled scans run at 01:35 UTC (09:35 Singapore), may be delayed by GitHub, and run only on the default branch. The supplied job is capped at 20 minutes and 25 coins. GitHub can disable inactive schedules; monitor last_run.json.
3. Optional: add the free Demo key as the Actions secret `COINGECKO_DEMO_API_KEY`. Never commit keys. Trigger `Free daily scan` manually to verify an initial real scan.
4. In Streamlit Community Cloud, authenticate GitHub, Create app, choose the repository/default branch, entrypoint `app.py`, Python 3.11. Deploy on Community Cloud's free service only. Add the optional Demo key via environment/secrets supported by your hosting setup (app reads st.secrets as fallback).
5. Verify the app URL, current observation date, last-run report and all dashboard pages.

SQLite on Community Cloud is ephemeral. Durable daily scanner data is committed by Actions into `data/`; each deployment reads that snapshot. Interactive single-coin writes on Cloud are session/instance-local and may be lost on reboot; the interface is research-only. To retain a coin automatically, add its verified perp mapping so Actions records it. On your Mac, SQLite persists normally. Simultaneous local readers use WAL. Do not manually commit the database while a writer is running.

## Research limitations
Read RULES.md before interpreting any score. Original V20 score was not recovered. Exact V20 is unverified and its proxy is visibly provisional. No calibrated probabilities or predictive edge claims. S5 is a heuristic, not observable dealer inventory. Missing historical MC blocks classification. Intraday extremes, futures positioning and liquidation distances are not represented. Forward returns are reference-price diagnostics, not executable perp returns. Full pre-installation survivorship-free delisted coverage and point-in-time publication audits are not available; do not market historical output as an unbiased backtest.

## Project files
- app.py: six dashboard views and CSV import/export
- engine.py: causal features, classifications, next-sample outcomes and baselines
- data.py: free endpoint cache, failures, CCXT contract inventory and strict identity mapping
- store.py: SQLite, frozen observations and universe/run audit trail
- scanner.py: bounded daily scanning CLI
- .github/workflows/daily-scan.yml: free public-repository scheduled job
- tests/: classifier, causality, persistence, data failure and dashboard tests

Keep all thresholds versioned; recover and implement the original score as a new rule version, preserving older classifications for comparison. Tests use deterministic synthetic fixtures, clearly isolated from production data.
