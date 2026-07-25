# Lottery AI Random Number Generator

A Streamlit application that generates randomized lottery combinations
using historical draw data, number-frequency weighting, shape filters,
recent bonus-ball exclusions, and cross-draw overlap controls.

## Supported games

- Powerball
- Mega Millions
- Lotto Texas
- Texas Two Step

## Current features

- Fetches public past-winner data or accepts CSV/XLSX uploads
- Hot, Cold, and Hot/Cold weighting
- Loose, More Loose, Tight, More Tight, and AI-selected shape profiles
- Historical draw duplicate prevention
- No duplicate white balls within one draw
- Recent bonus-ball exclusion
- Cross-draw repeat penalty
- No runs of three or more consecutive white balls
- Responsive game-summary cards
- Calculated next draw date
- Game-specific How to Play panel
- Scrolling current-jackpot ticker with graceful fallback
- CSV result export

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

Push `app.py`, `requirements.txt`, the `.streamlit` folder, and `assets/logo.png`
to GitHub. In Streamlit Community Cloud, select the repository, branch `main`,
and entry point `app.py`.

## Disclaimer

This app is for entertainment and experimentation. Lottery drawings are
random. Historical frequency and shape filters do not improve the
mathematical odds of winning.
