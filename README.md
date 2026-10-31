# Sandwich Radar: MEV sandwich detector

Scans Ethereum mainnet blocks for sandwich attacks on Uniswap V2 pools and shows the results on a live dashboard.

Live dashboard: https://gdp-dashboard-80unodhf577.streamlit.app/

## How it works

1. Pulls every Uniswap V2 Swap event for a block range through the Alchemy RPC (eth_getLogs).
2. Groups swaps by pool and block, ordered by log index.
3. Flags a sandwich when one address swaps right before and right after another user's swap in the same pool and block, in opposite directions.
4. Requires the back-run to sell about what the front-run bought (within 10 percent) and to end with more than it started with.
5. Saves detections to Postgres (Supabase), which the Streamlit dashboard reads.

## Results

In one 300-block scan: 25 candidates, 20 inside the 0.05 to 5 percent gross profit range, 8 unique attacker addresses. Candidates outside the range are hidden on the dashboard as likely false positives.

## Run it

    export ALCHEMY_KEY=your_key
    python3 mev_detector.py 300
    export SUPABASE_URL=your_url
    export SUPABASE_KEY=your_secret_key
    python3 save_to_supabase.py

## Limitations

- Uniswap V2 pools only (no V3, Curve or private order flow)
- Pattern-based heuristic, so false positives and misses are possible. Spot-check detections on Etherscan.
- Profit is a gross estimate before gas and does not measure the victim's loss
- Multi-hop or bundled attacks can be missed
