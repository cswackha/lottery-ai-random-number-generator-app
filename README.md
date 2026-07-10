# AI Lottery Random Number Generator

A minimal Streamlit MVP for generating random lottery number draws using historical draw data, frequency weighting, and simple shape filters.

## Supported games

- Powerball
- Mega Millions
- Lotto Texas
- Texas Two Step

## MVP features

- Select lottery game
- Generate 1–50 draws
- Choose Hot, Cold, or Hot/Cold weighting
- Choose Loose, More Loose, Tight, More Tight, or Let AI choose
- Parse past winning numbers
- Prevent historical draw duplicates
- Prevent duplicate white balls within a draw
- Prevent bonus/powerball/mega ball from matching selected white balls
- Exclude bonus balls used in the last X draws
- Apply cross-draw repeat penalty
- Block 3+ consecutive white ball runs
- Download generated results as CSV

## Important note

This app does not predict winning lottery numbers. It generates random combinations using historical frequency and shape filters. Lottery drawings are random.

## Local setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR-GITHUB-USERNAME/lottery-AI-random-number-generator-app.git
cd lottery-AI-random-number-generator-app
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Mac/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
streamlit run app.py
```

## GitHub push steps

```bash
git status
git add .
git commit -m "Add minimal Streamlit lottery generator MVP"
git branch -M main
git remote add origin https://github.com/YOUR-GITHUB-USERNAME/lottery-AI-random-number-generator-app.git
git push -u origin main
```

If the remote already exists:

```bash
git remote set-url origin https://github.com/YOUR-GITHUB-USERNAME/lottery-AI-random-number-generator-app.git
git push -u origin main
```

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to Streamlit Community Cloud.
3. Select **New app**.
4. Choose your GitHub repo.
5. Set the main file path to:

```text
app.py
```

6. Deploy.

## Suggested next improvements

- Add a cleaner card-based results layout
- Add number-locking so users can lock favorite numbers
- Add detailed draw explanation cards
- Add charting for hot/cold frequency
- Add unit tests for each game parser
- Move game definitions to a YAML config file
