import io
import re
import random
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st


GAMES = {
    "Powerball": {
        "white_count": 5,
        "white_min": 1,
        "white_max": 69,
        "bonus_name": "Powerball",
        "bonus_min": 1,
        "bonus_max": 26,
        "has_bonus": True,
        "history_url": "https://data.ny.gov/resource/d6yy-54nr.csv?$limit=5000",
    },
    "Mega Millions": {
        "white_count": 5,
        "white_min": 1,
        "white_max": 70,
        "bonus_name": "Mega Ball",
        "bonus_min": 1,
        "bonus_max": 24,
        "has_bonus": True,
        "history_url": "https://data.ny.gov/resource/5xaw-6ayf.csv?$limit=5000",
    },
    "Lotto Texas": {
        "white_count": 6,
        "white_min": 1,
        "white_max": 54,
        "bonus_name": None,
        "bonus_min": None,
        "bonus_max": None,
        "has_bonus": False,
        "history_url": "https://www.texaslottery.com/export/sites/lottery/Games/Lotto_Texas/Winning_Numbers/lottotexas.csv",
    },
    "Texas Two Step": {
        "white_count": 4,
        "white_min": 1,
        "white_max": 35,
        "bonus_name": "Bonus Ball",
        "bonus_min": 1,
        "bonus_max": 35,
        "has_bonus": True,
        "history_url": "https://www.texaslottery.com/export/sites/lottery/Games/Texas_Two_Step/Winning_Numbers/texastwostep.csv",
    },
}


@st.cache_data(ttl=3600)
def fetch_history_csv(url: str, texas_style: bool = False) -> pd.DataFrame:
    """Fetch a CSV from a public source. Texas files are commonly headerless."""
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    if texas_style:
        return pd.read_csv(io.StringIO(response.text), header=None)
    return pd.read_csv(io.StringIO(response.text))


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    raise ValueError("Please upload a CSV or Excel file.")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [
        str(c).strip().lower().replace(" ", "_").replace("-", "_")
        for c in out.columns
    ]
    return out


def extract_ints(value) -> List[int]:
    if pd.isna(value):
        return []
    return [int(x) for x in re.findall(r"\d+", str(value))]


def parse_date_from_row(row: pd.Series) -> Optional[pd.Timestamp]:
    cols = {str(k).lower(): k for k in row.index}

    for candidate in ["draw_date", "date", "drawing_date"]:
        if candidate in cols:
            parsed = pd.to_datetime(row[cols[candidate]], errors="coerce")
            if not pd.isna(parsed):
                return parsed

    # Texas Lottery CSV style: Game Name, Month, Day, Year, ...
    try:
        values = list(row.values)
        if len(values) >= 4:
            month, day, year = int(values[1]), int(values[2]), int(values[3])
            return pd.Timestamp(year=year, month=month, day=day)
    except Exception:
        pass

    try:
        if {"month", "day", "year"}.issubset(set(cols.keys())):
            return pd.Timestamp(
                year=int(row[cols["year"]]),
                month=int(row[cols["month"]]),
                day=int(row[cols["day"]]),
            )
    except Exception:
        pass

    return None


def parse_history(df: pd.DataFrame, game_name: str) -> pd.DataFrame:
    """
    Return normalized history with columns: draw_date, whites, bonus.

    Accepted MVP formats:
    1. NY Open Data winning_numbers style.
    2. Texas Lottery headerless CSV style.
    3. User CSV/XLSX with Num1...Num6 and Bonus Ball columns.
    """
    cfg = GAMES[game_name]
    white_count = cfg["white_count"]
    has_bonus = cfg["has_bonus"]
    needed = white_count + (1 if has_bonus else 0)

    raw = df.copy()
    norm = normalize_columns(df)
    records = []

    for idx in range(len(raw)):
        raw_row = raw.iloc[idx]
        norm_row = norm.iloc[idx]
        draw_date = parse_date_from_row(raw_row)
        nums: List[int] = []

        winning_col = None
        for c in norm.columns:
            if c in ["winning_numbers", "winning_number", "winning_nums"]:
                winning_col = c
                break

        if winning_col:
            nums = extract_ints(norm_row[winning_col])

        # Texas headerless CSV: Game Name, Month, Day, Year, Num1...
        if not nums and raw.shape[1] >= 4 + needed:
            values = list(raw_row.values)
            candidate = []
            for j in range(4, 4 + needed):
                try:
                    candidate.append(int(values[j]))
                except Exception:
                    pass
            if len(candidate) == needed:
                nums = candidate

        # Named number columns.
        if not nums:
            white_cols = []
            bonus_col = None

            for c in norm.columns:
                c_str = str(c).lower()
                if any(skip in c_str for skip in ["date", "month", "day", "year", "game", "jackpot", "winner", "multiplier"]):
                    continue

                if any(b in c_str for b in ["bonus", "powerball", "power_ball", "mega_ball", "megaball"]):
                    bonus_col = c
                    continue

                if re.search(r"(num|ball|white|n)_?\d+", c_str):
                    white_cols.append(c)

            def sort_key(col):
                found = re.findall(r"\d+", str(col))
                return int(found[-1]) if found else 999

            white_cols = sorted(white_cols, key=sort_key)

            for c in white_cols[:white_count]:
                found = extract_ints(norm_row[c])
                if found:
                    nums.append(found[0])

            if has_bonus and bonus_col:
                found = extract_ints(norm_row[bonus_col])
                if found:
                    nums.append(found[0])

        if len(nums) < white_count:
            continue

        whites = sorted(nums[:white_count])
        bonus = nums[white_count] if has_bonus and len(nums) > white_count else None

        if not all(cfg["white_min"] <= n <= cfg["white_max"] for n in whites):
            continue
        if len(set(whites)) != len(whites):
            continue
        if has_bonus and not (cfg["bonus_min"] <= bonus <= cfg["bonus_max"]):
            continue

        records.append({"draw_date": draw_date, "whites": tuple(whites), "bonus": bonus})

    history = pd.DataFrame(records)
    if history.empty:
        return history

    if history["draw_date"].notna().any():
        history = history.sort_values("draw_date", ascending=False, na_position="last").reset_index(drop=True)

    return history


def build_frequency(history: pd.DataFrame, min_num: int, max_num: int, field: str) -> Dict[int, int]:
    counts = {n: 0 for n in range(min_num, max_num + 1)}
    if history.empty:
        return counts

    if field == "whites":
        for balls in history["whites"]:
            for n in balls:
                counts[int(n)] += 1
    else:
        for n in history["bonus"].dropna():
            counts[int(n)] += 1
    return counts


def weights_from_frequency(numbers: List[int], freq: Dict[int, int], mode: str) -> np.ndarray:
    values = np.array([freq.get(n, 0) for n in numbers], dtype=float)

    if mode == "Hot":
        weights = values + 1
    elif mode == "Cold":
        weights = (values.max() - values) + 1
    else:
        # Hot/Cold favors both high and low outliers instead of the middle.
        median = np.median(values)
        weights = np.abs(values - median) + 1

    weights = np.maximum(weights, 0.001)
    return weights / weights.sum()


def has_run_of_three_or_more(nums: List[int]) -> bool:
    nums = sorted(nums)
    run = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            run += 1
            if run >= 3:
                return True
        else:
            run = 1
    return False


def get_shape_ranges(history: pd.DataFrame, shape: str) -> Dict[str, Tuple[float, float]]:
    sums = history["whites"].apply(sum)
    spreads = history["whites"].apply(lambda x: max(x) - min(x))

    if shape == "More Loose":
        q_low, q_high = 0.05, 0.95
    elif shape == "Loose":
        q_low, q_high = 0.10, 0.90
    elif shape == "Tight":
        q_low, q_high = 0.25, 0.75
    elif shape == "More Tight":
        q_low, q_high = 0.35, 0.65
    else:
        q_low, q_high = 0.25, 0.75

    return {
        "sum": (float(sums.quantile(q_low)), float(sums.quantile(q_high))),
        "spread": (float(spreads.quantile(q_low)), float(spreads.quantile(q_high))),
    }


def passes_shape(nums: List[int], game_name: str, history: pd.DataFrame, shape: str) -> bool:
    if shape == "Let AI choose":
        shape = random.choice(["Loose", "Tight", "More Tight"])

    if history.empty:
        return True

    cfg = GAMES[game_name]
    ranges = get_shape_ranges(history, shape)
    total = sum(nums)
    spread = max(nums) - min(nums)

    if not (ranges["sum"][0] <= total <= ranges["sum"][1]):
        return False
    if not (ranges["spread"][0] <= spread <= ranges["spread"][1]):
        return False

    if shape in ["Tight", "More Tight"]:
        odd_count = sum(n % 2 for n in nums)
        low_cutoff = (cfg["white_min"] + cfg["white_max"]) // 2
        low_count = sum(n <= low_cutoff for n in nums)
        n = len(nums)

        if odd_count in [0, n]:
            return False
        if low_count in [0, n]:
            return False

        if shape == "More Tight":
            if abs(odd_count - n / 2) > 1:
                return False
            if abs(low_count - n / 2) > 1:
                return False

    return True


def historical_signature(whites: List[int], bonus: Optional[int]) -> Tuple[int, ...]:
    values = tuple(sorted(whites))
    if bonus is not None:
        return values + (int(bonus),)
    return values


def choose_bonus(
    rng: np.random.Generator,
    cfg: Dict,
    whites: List[int],
    bonus_freq: Dict[int, int],
    recent_bonus_exclusions: set,
) -> Optional[int]:
    if not cfg["has_bonus"]:
        return None

    all_bonus = list(range(cfg["bonus_min"], cfg["bonus_max"] + 1))

    # MVP bonus logic: choose from top 10 bonus-frequency numbers,
    # excluding recent bonus values and selected white balls.
    top10 = sorted(all_bonus, key=lambda n: bonus_freq.get(n, 0), reverse=True)[:10]
    candidates = [n for n in top10 if n not in recent_bonus_exclusions and n not in whites]

    if not candidates:
        candidates = [n for n in all_bonus if n not in recent_bonus_exclusions and n not in whites]
    if not candidates:
        candidates = [n for n in all_bonus if n not in whites]

    weights = np.array([bonus_freq.get(n, 0) + 1 for n in candidates], dtype=float)
    weights = weights / weights.sum()
    return int(rng.choice(candidates, p=weights))


def generate_draws(
    game_name: str,
    history: pd.DataFrame,
    number_of_draws: int,
    weighting_mode: str,
    shape: str,
    no_historical_duplicates: bool,
    no_duplicate_numbers: bool,
    bonus_not_in_whites: bool,
    bonus_exclusion_count: int,
    cross_draw_repeat_penalty: float,
    no_three_consecutive: bool,
    seed: Optional[int] = None,
) -> pd.DataFrame:
    cfg = GAMES[game_name]
    rng = np.random.default_rng(seed)

    white_pool = list(range(cfg["white_min"], cfg["white_max"] + 1))
    white_freq = build_frequency(history, cfg["white_min"], cfg["white_max"], "whites")

    bonus_freq = {}
    recent_bonus_exclusions = set()
    if cfg["has_bonus"]:
        bonus_freq = build_frequency(history, cfg["bonus_min"], cfg["bonus_max"], "bonus")
        recent_bonus_exclusions = set(
            history["bonus"].dropna().astype(int).head(bonus_exclusion_count).tolist()
        )

    historical = set()
    for _, row in history.iterrows():
        historical.add(historical_signature(list(row["whites"]), row["bonus"]))

    generated = []
    used_across_draws = {}
    max_attempts = max(3000, number_of_draws * 1000)

    for draw_idx in range(number_of_draws):
        accepted = None

        for _ in range(max_attempts):
            base_weights = weights_from_frequency(white_pool, white_freq, weighting_mode)

            adjusted = []
            for number, weight in zip(white_pool, base_weights):
                times_used = used_across_draws.get(number, 0)
                adjusted.append(weight * (cross_draw_repeat_penalty ** times_used))

            adjusted = np.array(adjusted, dtype=float)
            adjusted = adjusted / adjusted.sum()

            whites = sorted(
                rng.choice(
                    white_pool,
                    size=cfg["white_count"],
                    replace=False,
                    p=adjusted,
                ).astype(int).tolist()
            )

            if no_duplicate_numbers and len(set(whites)) != len(whites):
                continue
            if no_three_consecutive and has_run_of_three_or_more(whites):
                continue
            if not passes_shape(whites, game_name, history, shape):
                continue

            bonus = choose_bonus(rng, cfg, whites, bonus_freq, recent_bonus_exclusions)

            if cfg["has_bonus"] and bonus_not_in_whites and bonus in whites:
                continue

            signature = historical_signature(whites, bonus)
            if no_historical_duplicates and signature in historical:
                continue

            low_cutoff = (cfg["white_min"] + cfg["white_max"]) // 2
            low_count = sum(n <= low_cutoff for n in whites)
            odd_count = sum(n % 2 for n in whites)

            accepted = {
                "Draw": draw_idx + 1,
                "White Balls": " - ".join(str(n) for n in whites),
                cfg["bonus_name"] if cfg["has_bonus"] else "Bonus": bonus,
                "Sum": sum(whites),
                "Spread": max(whites) - min(whites),
                "Odd/Even": f"{odd_count}/{len(whites) - odd_count}",
                "Low/High": f"{low_count}/{len(whites) - low_count}",
                "Shape": shape,
            }
            break

        if accepted is None:
            raise RuntimeError(
                "Could not generate enough draws with the selected settings. "
                "Try a looser shape, fewer draws, or a smaller bonus exclusion count."
            )

        generated.append(accepted)
        for n in [int(x) for x in accepted["White Balls"].split(" - ")]:
            used_across_draws[n] = used_across_draws.get(n, 0) + 1

    return pd.DataFrame(generated)


st.set_page_config(
    page_title="AI Lottery Random Number Generator",
    page_icon="🎲",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* Make sidebar more compact */
    section[data-testid="stSidebar"] {
        width: 275px !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        margin-top: 0.25rem !important;
        margin-bottom: 0.25rem !important;
    }

    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stRadio,
    section[data-testid="stSidebar"] .stSelectbox,
    section[data-testid="stSidebar"] .stSlider,
    section[data-testid="stSidebar"] .stCheckbox,
    section[data-testid="stSidebar"] .stTextInput {
        margin-bottom: 0.25rem !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0.35rem !important;
    }

    section[data-testid="stSidebar"] hr {
        margin-top: 0.45rem !important;
        margin-bottom: 0.45rem !important;
    }

    section[data-testid="stSidebar"] label {
        margin-bottom: 0.1rem !important;
    }

    section[data-testid="stSidebar"] .stButton {
        margin-top: 0.4rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.image("assets/logo.png", use_container_width=True)

    # st.markdown("## Lottery AI")
    # st.caption("Random Number Generator")

    st.header("Settings")

    game_name = st.selectbox("Pick a Lottery Game", list(GAMES.keys()))
    cfg = GAMES[game_name]

    source = st.radio(
        "Past winners source",
        ["Fetch latest public CSV", "Upload my file"],
        index=0,
    )

    uploaded_file = None
    if source == "Upload my file":
        uploaded_file = st.file_uploader(
            "Upload past winners CSV/XLSX",
            type=["csv", "xlsx", "xls"],
        )

    weighting_mode = st.selectbox(
        "Hot/cold frequency weighting",
        ["Hot", "Cold", "Hot/Cold"],
        index=2,
    )

    shape = st.selectbox(
        "Shape",
        ["Loose", "More Loose", "Tight", "More Tight", "Let AI choose"],
        index=2,
    )

    st.divider()

    st.subheader("Sliders")

    number_of_draws = st.slider(
        "Number of draws",
        1,
        50,
        5,
    )

    bonus_exclusion_count = 0
    if cfg["has_bonus"]:
        bonus_exclusion_count = st.slider(
            f"Exclude {cfg['bonus_name']} from last X draws",
            1,
            99,
            10,
        )

    cross_draw_repeat_penalty = st.slider(
        "Cross-draw repeat penalty",
        0.10,
        1.50,
        0.70,
        0.05,
        help="Below 1.0 discourages reuse across generated draws. Above 1.0 allows more repeats.",
    )

    st.divider()

    st.subheader("Constraints")

    no_historical_duplicates = st.checkbox(
        "No historical draw duplicates",
        value=True,
    )

    no_duplicate_numbers = st.checkbox(
        "No duplicate numbers within a draw",
        value=True,
    )

    bonus_not_in_whites = True
    if cfg["has_bonus"]:
        bonus_not_in_whites = st.checkbox(
            f"{cfg['bonus_name']} cannot be one of the white balls",
            value=True,
        )

    no_three_consecutive = st.checkbox(
        "No 3+ consecutive white ball runs",
        value=True,
    )

    st.divider()

    seed_text = st.text_input("Optional random seed", value="")
    seed = int(seed_text) if seed_text.strip().isdigit() else None

    generate = st.button(
        "Generate draws",
        type="primary",
        use_container_width=True,
    )

try:
    if source == "Fetch latest public CSV":
        texas_style = game_name in ["Lotto Texas", "Texas Two Step"]
        raw_df = fetch_history_csv(cfg["history_url"], texas_style=texas_style)
    else:
        if uploaded_file is None:
            st.info("Upload a past winners file to generate draws.")
            st.stop()
        raw_df = read_uploaded_file(uploaded_file)

    history = parse_history(raw_df, game_name)

    if history.empty:
        st.error("I could not parse the past winners file. Check the file format and columns.")
        st.stop()

    latest_date = history["draw_date"].dropna().max()
    latest_text = latest_date.strftime("%Y-%m-%d") if pd.notna(latest_date) else "Unknown"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Game", game_name)
    c2.metric("Historical draws parsed", f"{len(history):,}")
    c3.metric("Most recent draw", latest_text)
    c4.metric("White ball range", f"{cfg['white_min']}–{cfg['white_max']}")

    if cfg["has_bonus"] and bonus_exclusion_count:
        excluded = history["bonus"].dropna().astype(int).head(bonus_exclusion_count).tolist()
        st.caption(f"Recent {cfg['bonus_name']} exclusions: {sorted(set(excluded))}")

    if generate:
        results = generate_draws(
            game_name=game_name,
            history=history,
            number_of_draws=number_of_draws,
            weighting_mode=weighting_mode,
            shape=shape,
            no_historical_duplicates=no_historical_duplicates,
            no_duplicate_numbers=no_duplicate_numbers,
            bonus_not_in_whites=bonus_not_in_whites,
            bonus_exclusion_count=bonus_exclusion_count,
            cross_draw_repeat_penalty=cross_draw_repeat_penalty,
            no_three_consecutive=no_three_consecutive,
            seed=seed,
        )

        st.subheader("Generated Draws")
        
        for _, row in results.iterrows():
            bonus_label = cfg["bonus_name"] if cfg["has_bonus"] else None

            bonus_html = ""
            if cfg["has_bonus"]:
                bonus_html = f'<div class="bonus-pill">{bonus_label}: {row[bonus_label]}</div>'

        #    st.markdown(
        #        f"""
        #         <div class="draw-card">
        #             <div class="draw-title">Draw {row["Draw"]}</div>
        #             <div class="draw-numbers">{row["White Balls"]}</div>
        #             {bonus_html}
        #             <p style="margin-top: 0.75rem; color: #64748B;">
        #                 Sum: {row["Sum"]} &nbsp; | &nbsp;
        #                 Spread: {row["Spread"]} &nbsp; | &nbsp;
        #                 Odd/Even: {row["Odd/Even"]} &nbsp; | &nbsp;
        #                 Low/High: {row["Low/High"]}
        #             </p>
        #         </div>
        #         """,
        #         unsafe_allow_html=True,
        #     )

        st.dataframe(results, use_container_width=True, hide_index=True)
        csv = results.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download generated draws as CSV",
            data=csv,
            file_name=f"{game_name.lower().replace(' ', '_')}_generated_draws.csv",
            mime="text/csv",
        )

    with st.expander("Preview parsed history"):
        preview = history.head(20).copy()
        preview["whites"] = preview["whites"].apply(lambda x: " - ".join(map(str, x)))
        st.dataframe(preview, use_container_width=True, hide_index=True)

    with st.expander("Frequency preview"):
        white_freq = build_frequency(history, cfg["white_min"], cfg["white_max"], "whites")
        white_freq_df = pd.DataFrame([{"Number": k, "Times Drawn": v} for k, v in white_freq.items()])
        white_freq_df = white_freq_df.sort_values("Times Drawn", ascending=False)

        st.write("White ball frequency")
        st.dataframe(white_freq_df.head(15), use_container_width=True, hide_index=True)

        if cfg["has_bonus"]:
            bonus_freq = build_frequency(history, cfg["bonus_min"], cfg["bonus_max"], "bonus")
            bonus_freq_df = pd.DataFrame([{"Number": k, "Times Drawn": v} for k, v in bonus_freq.items()])
            bonus_freq_df = bonus_freq_df.sort_values("Times Drawn", ascending=False)

            st.write(f"{cfg['bonus_name']} frequency")
            st.dataframe(bonus_freq_df.head(15), use_container_width=True, hide_index=True)

except requests.HTTPError as e:
    st.error(f"Could not fetch the public CSV. Try uploading a file instead. Details: {e}")
except Exception as e:
    st.error(str(e))

st.divider()
st.caption(
    "Responsible use: lottery drawings are random. Historical frequency and shape filters do not improve the mathematical odds of winning."
)
