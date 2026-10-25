### Model review — 25 October 2026
The experimental score is not calibrated to the original V20 score. Applying V20's 30–59 threshold to it does not reproduce the original candidate set or research results. The proxy is retained only for reproducibility, not validated eligibility. S1/S2 must not automatically determine entry or position size.

Known structural limitations: Q2/Q3 do not affect the score; flat low turnover can score 53.75 with Range30=5%; smooth Q=[100,60,30,10] and erratic Q=[100,2,80,10] both score 78.5 at Range30=20%. S1 is broad and S2 permits a 21-day loss of up to 12%. State labels do not establish accumulation. The preserved version is in provisional-1.0-archive.zip. Replacement formulas require a new version and held-out validation; no thresholds have been retuned to fit the displayed chart.

### Transparent provisional research model
Rule version: provisional-1.0. The original V20 score formula was not recovered from accessible files. None of these formulas are claimed to reproduce it.

Data uses CoinGecko USD reference prices, historical circulating market caps, and reported trailing 24h total volumes at daily UTC timestamps. Vol/MC is the arithmetic mean of each day's volume / that day's market cap × 100. The 84 samples are divided into four consecutive non-overlapping periods of 21 observations, Q1 oldest through Q4 newest. This definition of quarterly aggregation is also provisional pending original research recovery. These are not exchange perp candles or traded execution prices.

Provisional score = 40×clip(1−Q4/Q1,0,1) + 30×clip(1−Q4/40,0,1) + 30×clip(1−Range30/60,0,1). Range30 = (max daily reference price / min daily reference price −1)×100. Location84 = (latest / min of 84 daily reference prices −1)×100. These lows are sampled lows, not intraday lows. Momentum = score today minus score 7 calendar days ago.

Classification predicates are evaluated independently with conflict precedence **S0 → S4 → S5 → S3 → S2 → S1**. There is no required state sequence. Insufficient inputs yield UNKNOWN; no matching predicate yields UNCLASSIFIED. Each day's class is raw, with no smoothing or confirmation delay.

| State | Provisional rule |
|---|---|
| S0 Capitulation | 7D return ≤−20%; volume ratio ≥1.5 |
| S1 Stabilization | Range30 ≤50%; 7D return >−20%, after higher-priority matches |
| S2 Early Compression | Score ≥30; Q4 5–20%; Range30 ≤35%; 21D return ≥−12% |
| S3 Mature Compression | Score ≥75; Range30 ≤25%; 21D return ≥−12% |
| S4 Expansion | 7D return ≥15%; price > prior 30-sample high; volume ratio ≥1.3 |
| S5 Distribution | 21D return ≥30%; price ≥10% below latest 21-sample high; volume ratio ≥1.3 |

Volume ratio = latest 7-day mean reported volume / preceding 21-day mean. Directional bias is separate: UP if 7D return >5%, DOWN if <−5%, otherwise NEUTRAL. Distribution is an observable price/volume pattern, not evidence of whale selling. States cannot establish liquidation risk without order books, funding, OI and venue margin rules.

### V20 preservation
Original candidate gates: historical MC $1M–$20M inclusive; score 30–59; Q4 Vol/MC 5–20%; Location84 12–18%; 3D return >0. Exact V20 eligibility stays UNVERIFIED (`v20_candidate=null`). The separate `v20_provisional_proxy` substitutes the explicitly provisional score; it is not a reproduction or validation of V20. Scores are continuous, so the proxy uses 30 ≤ score <60; confirm original integer rounding on recovery.

### Historical integrity and validation limits
Signals use only samples available through their date. The first next daily reference sample is the outcome entry; horizons need the complete next H+1 calendar samples. Incomplete outcomes remain censored; no forced losses or zero returns. MAE/MFE use daily reference prices and underestimate possible intraday extremes. Outcomes exclude fees, funding, spreads and delisting cash settlements; these are descriptive state diagnostics, not strategy P&L.

Historical data retrieved today is provider history, potentially revised, not an archived point-in-time feed. First received observations and classifications are frozen locally; observed_at records retrieval time. This prevents silent revision but cannot prove historical publication latency or remove provider revision bias. Results from currently listed contracts have survivorship bias before our universe snapshots began. Prior delisted contracts must be imported from verified historical archives before claiming unbiased broad historical results. Forward universe snapshots retain inactive/missing symbols. A missing symbol alone does not establish delisting.

Baselines compare S2/S3 against historical MC $1M–$20M and an 84-sample price drawdown ≥80%, using the same next-sample entry and 30D outcome. Within-cohort signals are ≥31 days apart, but cohorts can overlap. Samples are not independent across assets or regimes. No significance, edge, success probability or validated predictive claim is made. The drawdown baseline can be empty due to limited lookback. Perform walk-forward, held-out regime, delisted-asset, and cost-aware analysis before trading.

### Recovered source — separate research version
`recovered-v21-score-1.0` ports the six scoring/category methods from `main_v21_combined_project_test.py` (12 September 2026, Library ID libfile_2c7e3c8b6a3881918446409221aebe25). It does not import or run QuantConnect. Original source is preserved in `recovered-research-source.zip`.

Input requires 114 complete, consecutive, aligned UTC days of genuine OHLC, historical circulating MC and reported volume. The first 30 days support the prior-30-day low comparison, followed by four consecutive 21-day trajectory blocks. Quarter turnover is median daily volume/MC. Quarter return is final close / first close - 1 (20 close-to-close intervals per 21-bar segment, faithfully matching source). Quarter range is (maximum high - minimum low)/median close. New-low counts compare each daily low with the preceding 30 daily lows. Score = .30 turnover + .30 downside + .20 range + .20 new-low score - abandonment penalty, clipped 0–100. Component functions and thresholds are preserved exactly.

Recovered score categories are REPRICING (<40), COOLING (40–<60), EARLY (60–<75), MATURE (75–<90), EXTREME (≥90). These are not S0–S5. Frozen V20 guide gates use latest seven-day median MC inclusive $1M–$20M, score [30,60), median Q4 turnover [5%,20%), close/lowest 84-bar low - 1 in [12%,18%), and positive three-bar return. V21 code adds a Q4-return ≥−12% gate, while the V20 guide explicitly forbids extra entry gates; the port reports that gate separately and does not silently include it in the five-gate candidate.

Missing OHLC yields unavailable recovered results, never a sampled-price proxy. The standard CoinGecko history endpoint returns reference prices, not required daily OHLC. Genuine aligned CSV imports enable recovered computation; current API-only scans record missing-input status. Historical results in `research_states` have a distinct version/table; provisional states remain intact. A newly available valid result may replace an unavailable record of the same research version; complete recovered records are frozen. Data sources, contract multipliers, quote conversions and day alignment must be verified before importing. This is a recovered calculation, not proof of reproduced execution, unbiased historical universe, original performance or profitable trading.
