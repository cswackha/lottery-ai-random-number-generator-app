import html
import io
import random
import re
import base64
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# GAME CONFIGURATION
# ============================================================

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
        "history_url": (
            "https://www.texaslottery.com/export/sites/lottery/"
            "Games/Lotto_Texas/Winning_Numbers/lottotexas.csv"
        ),
    },
    "Texas Two Step": {
        "white_count": 4,
        "white_min": 1,
        "white_max": 35,
        "bonus_name": "Bonus Ball",
        "bonus_min": 1,
        "bonus_max": 35,
        "has_bonus": True,
        "history_url": (
            "https://www.texaslottery.com/export/sites/lottery/"
            "Games/Texas_Two_Step/Winning_Numbers/texastwostep.csv"
        ),
    },
}

HOW_TO_PLAY = {
    "Powerball": {
        "white": "Choose 5 white-ball numbers from 1–69.",
        "bonus": "Choose 1 Powerball number from 1–26.",
        "price": "$2 per play; Power Play is an additional $1.",
        "draws": "Monday, Wednesday and Saturday at 10:12 PM CT.",
        "break": "Texas ticket draw break: 9:00–10:15 PM CT.",
        "odds": "Jackpot odds: 1 in 292,201,338.",
    },
    "Mega Millions": {
        "white": "Choose 5 white-ball numbers from 1–70.",
        "bonus": "Choose 1 Mega Ball number from 1–24.",
        "price": "$5 per play; the multiplier is included.",
        "draws": "Tuesday and Friday at 10:12 PM CT.",
        "break": "Texas ticket draw break: 9:45–10:15 PM CT.",
        "odds": "Jackpot odds: 1 in 290,472,336.",
    },
    "Lotto Texas": {
        "white": "Choose 6 white-ball numbers from 1–54.",
        "bonus": "There is no bonus ball.",
        "price": "$1 per play; Extra! is an additional $1.",
        "draws": "Monday, Wednesday and Saturday at 10:12 PM CT.",
        "break": "Texas ticket draw break: 10:02–10:15 PM CT.",
        "odds": "Jackpot odds: 1 in 25,827,165.",
    },
    "Texas Two Step": {
        "white": "Choose 4 white-ball numbers from 1–35.",
        "bonus": "Choose 1 Bonus Ball number from 1–35.",
        "price": "$1 per play.",
        "draws": "Monday and Thursday at 10:12 PM CT.",
        "break": "Texas ticket draw break: 10:02–10:15 PM CT.",
        "odds": "Jackpot odds: 1 in 1,832,600.",
    },
}

DRAW_WEEKDAYS = {
    "Powerball": {0, 2, 5},       # Monday, Wednesday, Saturday
    "Mega Millions": {1, 4},      # Tuesday, Friday
    "Lotto Texas": {0, 2, 5},     # Monday, Wednesday, Saturday
    "Texas Two Step": {0, 3},     # Monday, Thursday
}

TEXAS_LOTTERY_GAMES_URL = (
    "https://www.texaslottery.com/export/sites/lottery/Games/"
)


# ============================================================
# STREAMLIT PAGE + STYLING
# ============================================================

st.set_page_config(
    page_title="AI Lottery Random Number Generator",
    page_icon="🎲",
    layout="wide",
)

def set_page_background(image_path: str) -> None:
    background_file = Path(image_path)

    if not background_file.exists():
        st.error(
            f"Background image not found: {background_file.resolve()}"
        )
        return

    encoded_image = base64.b64encode(
        background_file.read_bytes()
    ).decode("utf-8")

    st.html(
        f"""
        <style>
        /* Full main-page background */
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        section[data-testid="stMain"] {{
            background-image:
                linear-gradient(
                    rgba(238, 244, 252, 0.10),
                    rgba(238, 244, 252, 0.20)
                ),
                url("data:image/png;base64,{encoded_image}") !important;

            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}

        /* Make the top Streamlit header transparent */
        [data-testid="stHeader"] {{
            background: transparent !important;
        }}

        /* Translucent content area so the image remains visible */
        .block-container,
        [data-testid="stMainBlockContainer"] {{
            background: rgba(248, 250, 252, 0.40) !important;
            border-radius: 18px !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            box-shadow: 0 10px 35px rgba(15, 23, 42, 0.08);
        }}

        /* Keep the sidebar readable */
        [data-testid="stSidebar"] {{
            background: rgba(238, 242, 255, 0.96) !important;
        }}
        </style>
        """
    )

st.markdown(
    """
    <style>
    /* Main page */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1220px;
    }
    .exclusion-notice {
        margin: 0.45rem 0 0.75rem 0;
        padding: 0.65rem 0.85rem;
        border-left: 4px solid #2563eb;
        border-radius: 8px;
        background: #eff6ff;
        color: #334155;
        font-size: clamp(0.78rem, 1.1vw, 0.9rem);
        line-height: 1.45;
    }

    .exclusion-notice strong {
        color: #1e3a8a;
    }
    .hero {
        padding: clamp(1.25rem, 3vw, 2.2rem);
        border-radius: 22px;
        background: linear-gradient(
            135deg,
            #1e3a8a 0%,
            #2563eb 56%,
            #38bdf8 100%
        );
        color: white;
        margin-bottom: 0.8rem;
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.18);
    }

    .hero h1 {
        color: white;
        font-size: clamp(1.55rem, 4vw, 2.65rem);
        line-height: 1.12;
        margin: 0 0 0.55rem 0;
    }

    .hero p {
        font-size: clamp(0.86rem, 1.5vw, 1.05rem);
        line-height: 1.55;
        margin: 0;
        opacity: 0.96;
    }

    /* Responsive summary cards */
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
        gap: 0.8rem;
        margin: 1rem 0 0.8rem 0;
    }

    .summary-card {
        min-width: 0;
        background: rgba(255, 255, 255, 0.86);
        border: 1px solid rgba(148, 163, 184, 0.38);
        border-radius: 15px;
        padding: 0.82rem 0.92rem;
        box-shadow: 0 5px 16px rgba(15, 23, 42, 0.05);
    }

    .summary-label {
        color: #475569;
        font-size: clamp(0.65rem, 0.9vw, 0.78rem);
        font-weight: 700;
        line-height: 1.25;
        margin-bottom: 0.34rem;
        text-transform: uppercase;
        letter-spacing: 0.035em;
    }

    .summary-value {
        color: #0f172a;
        font-size: clamp(1rem, 2.15vw, 1.75rem);
        font-weight: 650;
        line-height: 1.15;
        overflow-wrap: anywhere;
    }

    /* Jackpot ticker */
    .jackpot-shell {
        overflow: hidden;
        border: 1px solid rgba(37, 99, 235, 0.28);
        border-radius: 13px;
        background: linear-gradient(90deg, #eff6ff, #ffffff, #eff6ff);
        margin: 0.75rem 0 1rem 0;
        padding: 0.62rem 0;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.07);
    }

    .jackpot-track {
        display: inline-block;
        min-width: max-content;
        white-space: nowrap;
        padding-left: 100%;
        animation: jackpot-scroll 34s linear infinite;
        will-change: transform;
    }

    .jackpot-item {
        display: inline-block;
        color: #0f172a;
        font-size: clamp(0.83rem, 1.2vw, 0.98rem);
        font-weight: 650;
        margin-right: 3.2rem;
    }

    .jackpot-item strong {
        color: #1d4ed8;
    }

    @keyframes jackpot-scroll {
        from { transform: translateX(0); }
        to { transform: translateX(-100%); }
    }

    @media (prefers-reduced-motion: reduce) {
        .jackpot-track {
            animation: none;
            padding-left: 0;
            white-space: normal;
        }
    }

    /* How-to-play panel */
    .how-play-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(215px, 1fr));
        gap: 0.7rem;
        margin-top: 0.25rem;
    }

    .how-play-item {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.8rem;
        background: #ffffff;
        color: #334155;
        line-height: 1.45;
    }

    .how-play-item b {
        color: #0f172a;
    }

    /* Draw result cards */
    .draw-card {
        padding: 1rem 1.1rem;
        border-radius: 16px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        box-shadow: 0 7px 20px rgba(15, 23, 42, 0.06);
        margin-bottom: 0.8rem;
    }

    .draw-title {
        color: #64748b;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    .draw-numbers {
        color: #0f172a;
        font-size: clamp(1.25rem, 3vw, 1.8rem);
        font-weight: 800;
        margin-top: 0.22rem;
    }

    .bonus-pill {
        display: inline-block;
        margin-top: 0.55rem;
        padding: 0.32rem 0.72rem;
        border-radius: 999px;
        background: #dbeafe;
        color: #1e40af;
        font-weight: 750;
    }

    .draw-details {
        color: #64748b;
        font-size: 0.86rem;
        margin-top: 0.6rem;
    }

    /* ============================================================
    SIDEBAR: COMPACT BUT READABLE
    ============================================================ */

    section[data-testid="stSidebar"]
    div[data-testid="stVerticalBlock"] {
        gap: 0.32rem !important;
    }

    section[data-testid="stSidebar"] hr {
        margin-top: 0.35rem !important;
        margin-bottom: 0.35rem !important;
    }

    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        margin-top: 0.25rem !important;
        margin-bottom: 0.2rem !important;
    }

    section[data-testid="stSidebar"] .stRadio,
    section[data-testid="stSidebar"] .stSelectbox,
    section[data-testid="stSidebar"] .stSlider,
    section[data-testid="stSidebar"] .stCheckbox,
    section[data-testid="stSidebar"] .stTextInput {
        margin-bottom: 0.05rem !important;
    }


    /* ============================================================
    SETTING EXPLANATIONS POPOVER
    ============================================================ */

    /* Make the button match the full width of the select box */
    section[data-testid="stSidebar"]
    .st-key-settings_explanations button {
        position: relative !important;
        display: block !important;
        width: 100% !important;
        min-height: 2.45rem !important;
        padding: 0 !important;
    }

    /* Position the icon and text on the left */
    section[data-testid="stSidebar"]
    .st-key-settings_explanations button
    [data-testid="stMarkdownContainer"] {
        position: absolute !important;
        left: 0.75rem !important;
        right: 2.5rem !important;
        top: 50% !important;
        transform: translateY(-50%) !important;

        width: auto !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
    }

    /* Keep the label text left-aligned */
    section[data-testid="stSidebar"]
    .st-key-settings_explanations button
    [data-testid="stMarkdownContainer"] p {
        margin: 0 !important;
        padding: 0 !important;
        text-align: left !important;
        white-space: nowrap !important;
    }

    /* Position the popover arrow inside the right edge */
    section[data-testid="stSidebar"]
    .st-key-settings_explanations button > svg:last-child {
        position: absolute !important;
        right: 0.95rem !important;
        top: 50% !important;
        transform: translateY(-50%) !important;

        margin: 0 !important;
        padding: 0 !important;
    }

    /* Footer */
    .site-footer {
        margin-top: 1.2rem;
        padding: 1rem 0 0.25rem 0;
        border-top: 1px solid #cbd5e1;
        color: #64748b;
        font-size: 0.77rem;
        line-height: 1.5;
        text-align: center;
    }

    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }

        .summary-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .jackpot-shell {
            width: 100%;
            overflow: hidden;
            padding: 0.55rem 0;
        }

        .jackpot-track {
            display: inline-flex;
            width: max-content;
            min-width: max-content;
            padding-left: 0 !important;
            white-space: nowrap;
            animation: jackpot-scroll-mobile 22s linear infinite !important;
            transform: translate3d(0, 0, 0);
            will-change: transform;
        }

        .jackpot-item {
            flex: 0 0 auto;
            padding: 0 1.25rem;
            font-size: 0.8rem;
        }

        @keyframes jackpot-scroll-mobile {
            from {
                transform: translate3d(100vw, 0, 0);
            }

            to {
                transform: translate3d(-100%, 0, 0);
            }
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Apply the full-page background after the main CSS
set_page_background("assets/page_background.png")

# ============================================================
# DATA FETCHING + PARSING
# ============================================================

@st.cache_data(ttl=3600)
def fetch_history_csv(url: str, texas_style: bool = False) -> pd.DataFrame:
    """Fetch a public past-winners CSV."""
    response = requests.get(
        url,
        timeout=25,
        headers={"User-Agent": "Mozilla/5.0 LotteryAI/1.0"},
    )
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
    normalized = df.copy()
    normalized.columns = [
        re.sub(
            r"_+",
            "_",
            str(column).strip().lower().replace(" ", "_").replace("-", "_"),
        )
        for column in normalized.columns
    ]
    return normalized


def extract_ints(value) -> List[int]:
    if pd.isna(value):
        return []
    return [int(number) for number in re.findall(r"\d+", str(value))]


def parse_date_from_row(row: pd.Series) -> Optional[pd.Timestamp]:
    columns = {str(key).strip().lower(): key for key in row.index}

    for candidate in ["draw_date", "date", "drawing_date"]:
        if candidate in columns:
            parsed = pd.to_datetime(row[columns[candidate]], errors="coerce")
            if not pd.isna(parsed):
                return parsed

    # Texas Lottery headerless CSV:
    # Game Name, Month, Day, Year, ...
    try:
        values = list(row.values)
        if len(values) >= 4:
            month = int(values[1])
            day = int(values[2])
            year = int(values[3])
            return pd.Timestamp(year=year, month=month, day=day)
    except (TypeError, ValueError, IndexError):
        pass

    return None


def parse_history(df: pd.DataFrame, game_name: str) -> pd.DataFrame:
    """
    Normalize history to: draw_date, whites, bonus.

    Supported MVP formats:
      1. NY Open Data winning_numbers format.
      2. Texas Lottery headerless CSV format.
      3. Uploaded files with named number columns.
    """
    cfg = GAMES[game_name]
    white_count = cfg["white_count"]
    has_bonus = cfg["has_bonus"]
    needed = white_count + (1 if has_bonus else 0)

    raw = df.copy()
    normalized = normalize_columns(df)
    records = []

    for index in range(len(raw)):
        raw_row = raw.iloc[index]
        row = normalized.iloc[index]
        draw_date = parse_date_from_row(raw_row)
        numbers: List[int] = []

        # Format 1: NY Open Data.
        winning_column = next(
            (
                column
                for column in normalized.columns
                if column
                in {"winning_numbers", "winning_number", "winning_nums"}
            ),
            None,
        )

        if winning_column is not None:
            numbers = extract_ints(row[winning_column])

            # Mega Millions stores the Mega Ball separately.
            # This also supports any Powerball source that does the same.
            if has_bonus and len(numbers) == white_count:
                for bonus_column in [
                    "powerball",
                    "power_ball",
                    "mega_ball",
                    "megaball",
                    "bonus_ball",
                    "bonus",
                ]:
                    if bonus_column in normalized.columns:
                        bonus_values = extract_ints(row[bonus_column])
                        if bonus_values:
                            numbers.append(bonus_values[0])
                            break

        # Format 2: Texas Lottery headerless CSV.
        if len(numbers) < needed and raw.shape[1] >= 4 + needed:
            values = list(raw_row.values)
            candidate = []

            for position in range(4, 4 + needed):
                try:
                    candidate.append(int(values[position]))
                except (TypeError, ValueError, IndexError):
                    candidate = []
                    break

            if len(candidate) == needed:
                numbers = candidate

        # Format 3: named number columns.
        if len(numbers) < needed:
            white_columns = []
            bonus_column = None

            for column in normalized.columns:
                column_text = str(column).lower()

                if any(
                    excluded in column_text
                    for excluded in [
                        "date",
                        "month",
                        "day",
                        "year",
                        "game",
                        "jackpot",
                        "winner",
                        "multiplier",
                    ]
                ):
                    continue

                if any(
                    bonus_text in column_text
                    for bonus_text in [
                        "bonus",
                        "powerball",
                        "power_ball",
                        "mega_ball",
                        "megaball",
                    ]
                ):
                    bonus_column = column
                    continue

                if re.search(r"(num|ball|white|n)_?\d+", column_text):
                    white_columns.append(column)

            def number_column_sort(column_name):
                matches = re.findall(r"\d+", str(column_name))
                return int(matches[-1]) if matches else 999

            white_columns = sorted(
                white_columns,
                key=number_column_sort,
            )

            named_numbers = []

            for column in white_columns[:white_count]:
                found = extract_ints(row[column])
                if found:
                    named_numbers.append(found[0])

            if has_bonus and bonus_column is not None:
                found = extract_ints(row[bonus_column])
                if found:
                    named_numbers.append(found[0])

            if len(named_numbers) >= white_count:
                numbers = named_numbers

        if len(numbers) < white_count:
            continue

        whites = sorted(numbers[:white_count])
        bonus = (
            numbers[white_count]
            if has_bonus and len(numbers) > white_count
            else None
        )

        if not all(
            cfg["white_min"] <= number <= cfg["white_max"]
            for number in whites
        ):
            continue

        if len(set(whites)) != white_count:
            continue

        if has_bonus:
            if bonus is None:
                continue
            if not cfg["bonus_min"] <= bonus <= cfg["bonus_max"]:
                continue

        records.append(
            {
                "draw_date": draw_date,
                "whites": tuple(whites),
                "bonus": bonus,
            }
        )

    history = pd.DataFrame(records)

    if history.empty:
        return history

    if history["draw_date"].notna().any():
        history = history.sort_values(
            "draw_date",
            ascending=False,
            na_position="last",
        ).reset_index(drop=True)

    return history


# ============================================================
# LIVE JACKPOTS + DRAW SCHEDULE
# ============================================================

def strip_html(raw_html: str) -> str:
    """Convert an HTML page into normalized plain text without extra packages."""
    without_scripts = re.sub(
        r"(?is)<(script|style).*?>.*?</\1>",
        " ",
        raw_html,
    )
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    return " ".join(html.unescape(without_tags).split())


@st.cache_data(ttl=900)
def fetch_current_jackpots() -> Dict[str, Dict[str, str]]:
    """
    Read the official Texas Lottery games page and extract current jackpots.
    Returns an empty dictionary if the source changes or is temporarily down.
    """
    try:
        response = requests.get(
            TEXAS_LOTTERY_GAMES_URL,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 LotteryAI/1.0"},
        )
        response.raise_for_status()
        page_text = strip_html(response.text)

        game_names = [
            "Powerball",
            "Mega Millions",
            "Lotto Texas",
            "Texas Two Step",
        ]

        results: Dict[str, Dict[str, str]] = {}

        for game in game_names:
            start_marker = f"Latest Results for {game}"
            start = page_text.find(start_marker)

            if start == -1:
                continue

            later_starts = [
                page_text.find(f"Latest Results for {other}", start + 1)
                for other in game_names
                if other != game
            ]
            later_starts = [position for position in later_starts if position > start]
            end = min(later_starts) if later_starts else len(page_text)
            section = page_text[start:end]

            jackpot_match = re.search(
                r"(?:Current Est\. Annuitized Jackpot|"
                r"Current Advertised Jackpot)"
                r"\s+for\s+(\d{1,2}/\d{1,2}/\d{4})\s*:\s*"
                r"\$([0-9][0-9,]*(?:\.\d+)?"
                r"(?:\s+(?:Million|Billion))?)",
                section,
                flags=re.IGNORECASE,
            )

            if not jackpot_match:
                continue

            cash_match = re.search(
                r"Est\. Cash Value\s*:\s*"
                r"\$([0-9][0-9,]*(?:\.\d+)?"
                r"(?:\s+(?:Million|Billion))?)",
                section,
                flags=re.IGNORECASE,
            )

            results[game] = {
                "draw_date": jackpot_match.group(1),
                "jackpot": f"${jackpot_match.group(2)}",
                "cash": (
                    f"${cash_match.group(1)}"
                    if cash_match
                    else ""
                ),
            }

        return results

    except requests.RequestException:
        return {}


def next_draw_datetime(
    game_name: str,
    now: Optional[datetime] = None,
) -> datetime:
    central = ZoneInfo("America/Chicago")
    current = now or datetime.now(central)

    if current.tzinfo is None:
        current = current.replace(tzinfo=central)
    else:
        current = current.astimezone(central)

    weekdays = DRAW_WEEKDAYS[game_name]
    draw_clock = time(hour=22, minute=12)

    for offset in range(8):
        candidate_date = current.date() + timedelta(days=offset)

        if candidate_date.weekday() not in weekdays:
            continue

        candidate = datetime.combine(
            candidate_date,
            draw_clock,
            tzinfo=central,
        )

        if candidate >= current:
            return candidate

    raise RuntimeError("Could not calculate the next draw date.")


def format_next_draw(game_name: str) -> str:
    draw = next_draw_datetime(game_name)
    return draw.strftime("%a, %b %-d, %Y")


# Windows strftime does not consistently support %-d.
def format_next_draw_portable(game_name: str) -> str:
    draw = next_draw_datetime(game_name)
    return f"{draw.strftime('%a, %b')} {draw.day}, {draw.year}"


def render_jackpot_ticker(jackpots: Dict[str, Dict[str, str]]) -> None:
    if jackpots:
        ticker_parts = []

        for game in GAMES:
            data = jackpots.get(game)
            if not data:
                continue

            cash_text = (
                f" · Cash {html.escape(data['cash'])}"
                if data.get("cash")
                else ""
            )

            ticker_parts.append(
                '<span class="jackpot-item">'
                f"<strong>{html.escape(game)}</strong>: "
                f"{html.escape(data['jackpot'])}"
                f"{cash_text} · Draw {html.escape(data['draw_date'])}"
                "</span>"
            )

        if ticker_parts:
            # Duplicate the sequence for a smoother continuous loop.
            content = "".join(ticker_parts + ticker_parts)
        else:
            content = (
                '<span class="jackpot-item">'
                "Live jackpot data is temporarily unavailable."
                "</span>"
            )
    else:
        content = (
            '<span class="jackpot-item">'
            "Live jackpot data is temporarily unavailable. "
            "The number generator remains available."
            "</span>"
        )

    st.html(
        '<div class="jackpot-shell" '
        'aria-label="Current lottery jackpots">'
        f'<div class="jackpot-track">{content}</div>'
        '</div>'
    )


# ============================================================
# LOTTERY GENERATION
# ============================================================

def build_frequency(
    history: pd.DataFrame,
    min_number: int,
    max_number: int,
    field: str,
) -> Dict[int, int]:
    counts = {
        number: 0
        for number in range(min_number, max_number + 1)
    }

    if history.empty:
        return counts

    if field == "whites":
        for balls in history["whites"]:
            for number in balls:
                counts[int(number)] += 1
    else:
        for number in history["bonus"].dropna():
            counts[int(number)] += 1

    return counts


def weights_from_frequency(
    numbers: List[int],
    frequency: Dict[int, int],
    mode: str,
) -> np.ndarray:
    values = np.array(
        [frequency.get(number, 0) for number in numbers],
        dtype=float,
    )

    if mode == "Hot":
        weights = values + 1
    elif mode == "Cold":
        weights = (values.max() - values) + 1
    else:
        median = np.median(values)
        weights = np.abs(values - median) + 1

    weights = np.maximum(weights, 0.001)
    return weights / weights.sum()


def has_run_of_three_or_more(numbers: List[int]) -> bool:
    sorted_numbers = sorted(numbers)
    run = 1

    for index in range(1, len(sorted_numbers)):
        if sorted_numbers[index] == sorted_numbers[index - 1] + 1:
            run += 1
            if run >= 3:
                return True
        else:
            run = 1

    return False


def get_shape_ranges(
    history: pd.DataFrame,
    shape: str,
) -> Dict[str, Tuple[float, float]]:
    sums = history["whites"].apply(sum)
    spreads = history["whites"].apply(
        lambda numbers: max(numbers) - min(numbers)
    )

    quantiles = {
        "More Loose": (0.05, 0.95),
        "Loose": (0.10, 0.90),
        "Tight": (0.25, 0.75),
        "More Tight": (0.35, 0.65),
    }

    low_quantile, high_quantile = quantiles.get(
        shape,
        (0.25, 0.75),
    )

    return {
        "sum": (
            float(sums.quantile(low_quantile)),
            float(sums.quantile(high_quantile)),
        ),
        "spread": (
            float(spreads.quantile(low_quantile)),
            float(spreads.quantile(high_quantile)),
        ),
    }


def passes_shape(
    numbers: List[int],
    game_name: str,
    history: pd.DataFrame,
    shape: str,
) -> bool:
    selected_shape = shape

    if selected_shape == "Let AI choose":
        selected_shape = random.choice(
            ["Loose", "Tight", "More Tight"]
        )

    if history.empty:
        return True

    cfg = GAMES[game_name]
    ranges = get_shape_ranges(history, selected_shape)
    total = sum(numbers)
    spread = max(numbers) - min(numbers)

    if not ranges["sum"][0] <= total <= ranges["sum"][1]:
        return False

    if not ranges["spread"][0] <= spread <= ranges["spread"][1]:
        return False

    if selected_shape in {"Tight", "More Tight"}:
        odd_count = sum(number % 2 for number in numbers)
        low_cutoff = (
            cfg["white_min"] + cfg["white_max"]
        ) // 2
        low_count = sum(
            number <= low_cutoff
            for number in numbers
        )
        count = len(numbers)

        if odd_count in {0, count}:
            return False

        if low_count in {0, count}:
            return False

        if selected_shape == "More Tight":
            if abs(odd_count - count / 2) > 1:
                return False
            if abs(low_count - count / 2) > 1:
                return False

    return True


def historical_signature(
    whites: List[int],
    bonus: Optional[int],
) -> Tuple[int, ...]:
    values = tuple(sorted(whites))

    if bonus is not None:
        return values + (int(bonus),)

    return values


def choose_bonus(
    rng: np.random.Generator,
    cfg: Dict,
    whites: List[int],
    bonus_frequency: Dict[int, int],
    recent_bonus_exclusions: set,
) -> Optional[int]:
    if not cfg["has_bonus"]:
        return None

    all_bonus_numbers = list(
        range(cfg["bonus_min"], cfg["bonus_max"] + 1)
    )

    top_ten = sorted(
        all_bonus_numbers,
        key=lambda number: bonus_frequency.get(number, 0),
        reverse=True,
    )[:10]

    candidates = [
        number
        for number in top_ten
        if number not in recent_bonus_exclusions
        and number not in whites
    ]

    if not candidates:
        candidates = [
            number
            for number in all_bonus_numbers
            if number not in recent_bonus_exclusions
            and number not in whites
        ]

    if not candidates:
        candidates = [
            number
            for number in all_bonus_numbers
            if number not in whites
        ]

    weights = np.array(
        [
            bonus_frequency.get(number, 0) + 1
            for number in candidates
        ],
        dtype=float,
    )
    weights = weights / weights.sum()

    return int(rng.choice(candidates, p=weights))

def build_shape_plan(
    selected_shape: str,
    number_of_draws: int,
    rng: np.random.Generator,
) -> List[str]:
    """
    Create the shape assigned to each generated draw.

    Combined selections are split as evenly as possible.
    When the number of draws is odd, the extra draw is
    randomly assigned to either shape.
    """
    combined_shapes = {
        "Tight/Loose": ("Tight", "Loose"),
        "More Tight/More Loose": (
            "More Tight",
            "More Loose",
        ),
    }

    if selected_shape not in combined_shapes:
        return [selected_shape] * number_of_draws

    first_shape, second_shape = combined_shapes[selected_shape]

    first_count = number_of_draws // 2
    second_count = number_of_draws // 2

    if number_of_draws % 2 == 1:
        extra_shape = int(rng.integers(0, 2))

        if extra_shape == 0:
            first_count += 1
        else:
            second_count += 1

    shape_plan = (
        [first_shape] * first_count
        + [second_shape] * second_count
    )

    rng.shuffle(shape_plan)

    return shape_plan

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

    white_pool = list(
        range(cfg["white_min"], cfg["white_max"] + 1)
    )
    white_frequency = build_frequency(
        history,
        cfg["white_min"],
        cfg["white_max"],
        "whites",
    )

    bonus_frequency = {}
    recent_bonus_exclusions = set()

    if cfg["has_bonus"]:
        bonus_frequency = build_frequency(
            history,
            cfg["bonus_min"],
            cfg["bonus_max"],
            "bonus",
        )
        recent_bonus_exclusions = set(
            history["bonus"]
            .dropna()
            .astype(int)
            .head(bonus_exclusion_count)
            .tolist()
        )

    historical_draws = {
        historical_signature(
            list(row["whites"]),
            row["bonus"],
        )
        for _, row in history.iterrows()
    }

    generated = []
    used_across_draws: Dict[int, int] = {}
    max_attempts = max(3000, number_of_draws * 1000)

    shape_plan = build_shape_plan(
        selected_shape=shape,
        number_of_draws=number_of_draws,
        rng=rng,
    )

    for draw_index in range(number_of_draws):
        accepted = None
        draw_shape = shape_plan[draw_index]

        for _ in range(max_attempts):
            base_weights = weights_from_frequency(
                white_pool,
                white_frequency,
                weighting_mode,
            )

            adjusted_weights = []

            for number, weight in zip(
                white_pool,
                base_weights,
            ):
                times_used = used_across_draws.get(number, 0)
                adjusted_weights.append(
                    weight
                    * (
                        cross_draw_repeat_penalty
                        ** times_used
                    )
                )

            adjusted_weights = np.array(
                adjusted_weights,
                dtype=float,
            )
            adjusted_weights = (
                adjusted_weights / adjusted_weights.sum()
            )

            whites = sorted(
                rng.choice(
                    white_pool,
                    size=cfg["white_count"],
                    replace=False,
                    p=adjusted_weights,
                )
                .astype(int)
                .tolist()
            )

            if (
                no_duplicate_numbers
                and len(set(whites)) != len(whites)
            ):
                continue

            if (
                no_three_consecutive
                and has_run_of_three_or_more(whites)
            ):
                continue

            if not passes_shape(
                whites,
                game_name,
                history,
                shape,
            ):
                continue

            bonus = choose_bonus(
                rng,
                cfg,
                whites,
                bonus_frequency,
                recent_bonus_exclusions,
            )

            if (
                cfg["has_bonus"]
                and bonus_not_in_whites
                and bonus in whites
            ):
                continue

            signature = historical_signature(
                whites,
                bonus,
            )

            if (
                no_historical_duplicates
                and signature in historical_draws
            ):
                continue

            low_cutoff = (
                cfg["white_min"] + cfg["white_max"]
            ) // 2
            low_count = sum(
                number <= low_cutoff
                for number in whites
            )
            odd_count = sum(
                number % 2
                for number in whites
            )

            accepted = {
                "Draw": draw_index + 1,
                "White Balls": " - ".join(
                    str(number)
                    for number in whites
                ),
                (
                    cfg["bonus_name"]
                    if cfg["has_bonus"]
                    else "Bonus"
                ): bonus,
                "Sum": sum(whites),
                "Spread": max(whites) - min(whites),
                "Odd/Even": (
                    f"{odd_count}/"
                    f"{len(whites) - odd_count}"
                ),
                "Low/High": (
                    f"{low_count}/"
                    f"{len(whites) - low_count}"
                ),
                "Shape": draw_shape,
            }
            break

        if accepted is None:
            raise RuntimeError(
                "The selected settings are too restrictive. "
                "Try a looser shape, fewer draws, or a smaller "
                "bonus exclusion count."
            )

        generated.append(accepted)

        for number in [
            int(value)
            for value in accepted["White Balls"].split(" - ")
        ]:
            used_across_draws[number] = (
                used_across_draws.get(number, 0) + 1
            )

    return pd.DataFrame(generated)


# ============================================================
# UI HELPERS
# ============================================================

def bonus_range_summary(game_name: str) -> Tuple[str, str]:
    cfg = GAMES[game_name]

    if game_name == "Powerball":
        return "Powerball number range", "1–26"

    if game_name == "Mega Millions":
        return "Mega Ball range", "1–24"

    if game_name == "Texas Two Step":
        return "Bonus Ball range", "1–35"

    return "Bonus ball", "None"


def render_summary_cards(
    game_name: str,
    history: pd.DataFrame,
) -> None:
    cfg = GAMES[game_name]
    latest_date = history["draw_date"].dropna().max()
    latest_text = (
        latest_date.strftime("%b %d, %Y")
        if pd.notna(latest_date)
        else "Unknown"
    )
    bonus_label, bonus_value = bonus_range_summary(game_name)

    cards = [
        ("Game", game_name),
        ("Historical draws parsed", f"{len(history):,}"),
        ("Most recent draw", latest_text),
        ("Next draw date", format_next_draw_portable(game_name)),
        (
            "White ball range",
            f"{cfg['white_min']}–{cfg['white_max']}",
        ),
        (bonus_label, bonus_value),
    ]

    card_html = "".join(
        (
            '<div class="summary-card">'
            f'<div class="summary-label">{html.escape(label)}</div>'
            f'<div class="summary-value">{html.escape(value)}</div>'
            '</div>'
        )
        for label, value in cards
    )

    st.html(
        f'<div class="summary-grid">{card_html}</div>'
    )


def render_how_to_play(game_name: str) -> None:
    details = HOW_TO_PLAY[game_name]

    with st.expander(
        f"How to Play {game_name}",
        expanded=False,
    ):
        items = [
            ("White balls", details["white"]),
            ("Bonus ball", details["bonus"]),
            ("Price", details["price"]),
            ("Draw schedule", details["draws"]),
            ("Draw break", details["break"]),
            ("Jackpot odds", details["odds"]),
        ]

        item_html = "".join(
            (
                '<div class="how-play-item">'
                f'<b>{html.escape(label)}</b><br>'
                f'{html.escape(value)}'
                '</div>'
            )
            for label, value in items
        )

        st.html(
            f'<div class="how-play-grid">{item_html}</div>'
        )

        st.caption(
            "Game information is presented for Texas players. "
            "Official lottery rules and posted draw information prevail."
        )


def render_result_cards(
    results: pd.DataFrame,
    cfg: Dict,
) -> None:
    for _, row in results.iterrows():
        bonus_html = ""

        if cfg["has_bonus"]:
            bonus_label = cfg["bonus_name"]
            bonus_html = (
                '<div class="bonus-pill">'
                f"{html.escape(bonus_label)}: "
                f"{html.escape(str(row[bonus_label]))}"
                "</div>"
            )

        draw_html = (
            '<div class="draw-card">'
            f'<div class="draw-title">Draw {int(row["Draw"])}</div>'
            f'<div class="draw-numbers">'
            f'{html.escape(str(row["White Balls"]))}'
            '</div>'
            f'{bonus_html}'
            '<div class="draw-details">'
            f'Sum: {int(row["Sum"])}'
            '&nbsp; | &nbsp;'
            f'Spread: {int(row["Spread"])}'
            '&nbsp; | &nbsp;'
            f'Odd/Even: {html.escape(str(row["Odd/Even"]))}'
            '&nbsp; | &nbsp;'
            f'Low/High: {html.escape(str(row["Low/High"]))}'
            '</div>'
            '</div>'
        )

        st.html(draw_html)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## DRAW SETTINGS")

    with st.popover(
        "ℹ️ Setting explanations",
        width="stretch",
        key="settings_explanations",
    ):
        st.markdown(
            """
            **Hot/Cold Frequency Weighting**  
            Controls how strongly historical number frequency influences
            number selection.

            **Shape**  
            Controls how closely generated draws follow typical historical
            patterns, including odd/even balance, low/high balance, total sum,
            spread, and consecutive-number behavior.

            **Number of Draws**  
            Selects how many lottery combinations will be generated.

            **Exclude Bonus Ball from Last X Draws**  
            Prevents bonus-ball numbers appearing in the selected number of
            recent drawings from being selected.

            **Cross-draw Repeat Penalty**  
            Reduces repeated white-ball numbers across generated combinations.
            Lower values produce greater diversity between draws.

            **Optional Random Seed**  
            Enter a whole number to reproduce the same results when the source
            data and settings remain unchanged. Leave blank for a fresh random
            result.
            """
        )

    game_name = st.selectbox(
        "Pick a lottery game",
        list(GAMES.keys()),
    )
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
    "Hot/Cold Frequency Weighting",
    options=["Hot/Cold", "Aggressive Hot", "Cold Chaser"],
    help=(
        "Controls how strongly historical number frequency affects the draw. "
        "Hot settings favor numbers drawn more frequently, while cold-oriented "
        "settings give more weight to less frequently drawn numbers."
    ),
)

    shape = st.selectbox(
    "Shape",
    options=["Loose", "Tight", "AI Choose"],
    help=(
        "Controls how closely generated draws follow common historical patterns, "
        "including odd/even balance, low/high balance, total sum, number spread, "
        "and consecutive-number behavior. Tight applies stronger constraints; "
        "Loose allows more variation."
    ),
)

    st.divider()
    st.markdown(
    "<div style='height: 0.45rem;'></div>",
    unsafe_allow_html=True,
    )

    lock_sliders = st.checkbox(
        "🔒 Lock sliders",
        value=True,
        help="Prevents sliders from moving while scrolling on mobile.",
        key="lock_sliders",
    )

    st.markdown(
        """
        <h3 style="
            margin-top: 0.05rem;
            margin-bottom: 0.35rem;
        ">
            Sliders
        </h3>
        """,
        unsafe_allow_html=True,
    )

    number_of_draws = st.slider(
    "Number of draws",
    min_value=1,
    max_value=50,
    value=5,
    step=1,
    disabled=lock_sliders,
    help=(
        "Selects how many unique lottery combinations will be generated. "
        "Increasing this value creates more result rows."
    ),
)

    bonus_exclusion_count = 0

    if cfg["has_bonus"]:
       bonus_exclusion_count = st.slider(
            f"Exclude {cfg['bonus_name']} from last X draws",
            min_value=1,
            max_value=99,
            value=10,
            step=1,
            disabled=lock_sliders,
            help=(
                f"Prevents a recently drawn {cfg['bonus_name']} from being selected. "
                "For example, a value of 10 excludes bonus-ball numbers appearing in "
                "the most recent 10 historical drawings."
            ),
)

    cross_draw_repeat_penalty = st.slider(
    "Cross-draw repeat penalty",
    min_value=0.1,
    max_value=1.5,
    value=0.7,
    step=0.1,
    disabled=lock_sliders,
    help=(
        "Reduces repeated white-ball numbers across the generated combinations. "
        "Lower values apply a stronger repeat penalty and create more diversity. "
        "A value near 1.0 applies little or no penalty."
    ),
)

    st.divider()
    st.markdown("### Constraints")

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
        "No 3+ consecutive white-ball runs",
        value=True,
    )

    seed_text = st.text_input(
        "Optional random seed",
        value="",
        placeholder="Example: 12345",
        help=(
            "Enter a positive whole number to reproduce the same generated "
            "results with the same settings and data. Leave blank for a new "
            "random result."
        ),
    )

    seed = (
        int(seed_text)
        if seed_text.strip().isdigit()
        else None
    )

    generate = st.button(
        "Generate draws",
        type="primary",
        use_container_width=True,
    )
# Close the sidebar after Generate Draws is selected on mobile.
if generate:
    st.html(
        """
        <script>
        (() => {
            const isMobile = window.matchMedia(
                "(max-width: 768px)"
            ).matches;

            if (!isMobile) {
                return;
            }

            const closeSidebar = () => {
                const selectors = [
                    '[data-testid="stSidebarCollapseButton"] button',
                    '[data-testid="stSidebarCollapseButton"]',
                    'button[aria-label="Close sidebar"]',
                    'button[aria-label="Collapse sidebar"]'
                ];

                for (const selector of selectors) {
                    const button = document.querySelector(selector);

                    if (button) {
                        button.click();
                        return true;
                    }
                }

                return false;
            };

            if (!closeSidebar()) {
                let attempts = 0;

                const timer = setInterval(() => {
                    attempts += 1;

                    if (closeSidebar() || attempts >= 20) {
                        clearInterval(timer);
                    }
                }, 100);
            }
        })();
        </script>
        """,
        unsafe_allow_javascript=True,
    )    

# ============================================================
# MAIN PAGE
# ============================================================

st.image(
    "assets/banner.png",
    use_container_width=True,
)

jackpots = fetch_current_jackpots()
render_jackpot_ticker(jackpots)
st.caption(
    "Jackpots are fetched from the Texas Lottery website and cached "
    "for approximately 15 minutes."
)

try:
    if source == "Fetch latest public CSV":
        texas_style = game_name in {
            "Lotto Texas",
            "Texas Two Step",
        }
        raw_df = fetch_history_csv(
            cfg["history_url"],
            texas_style=texas_style,
        )
    else:
        if uploaded_file is None:
            st.info(
                "Upload a past-winners CSV or Excel file "
                "to generate draws."
            )
            st.stop()

        raw_df = read_uploaded_file(uploaded_file)

    history = parse_history(raw_df, game_name)

    if history.empty:
        st.error(
            "The past-winners source was fetched, but no valid draws "
            "could be parsed. Try uploading a file or check the source format."
        )
        st.stop()

    render_summary_cards(game_name, history)

    if cfg["has_bonus"] and bonus_exclusion_count:
        excluded = (
            history["bonus"]
            .dropna()
            .astype(int)
            .head(bonus_exclusion_count)
            .tolist()
        )

        exclusion_numbers = ", ".join(
            str(number)
            for number in sorted(set(excluded))
        )

        st.html(
            '<div class="exclusion-notice">'
            f'<strong>Recent {html.escape(cfg["bonus_name"])} exclusions:</strong> '
            f'{html.escape(exclusion_numbers)}'
            '</div>'
        )

    render_how_to_play(game_name)

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

        st.html('<div id="generated-draws-anchor"></div>')

        st.subheader("Generated Draws")

        table_height = 38 * (len(results) + 1) + 3

        st.dataframe(
            results,
            use_container_width=True,
            hide_index=True,
            height=table_height,
        )

        csv = results.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download generated draws as CSV",
            data=csv,
            file_name=(
                f"{game_name.lower().replace(' ', '_')}"
                "_generated_draws.csv"
            ),
            mime="text/csv",
        )

        st.html(
            """
            <script>
            (() => {
                const isMobile = window.matchMedia(
                    "(max-width: 768px)"
                ).matches;

                if (!isMobile) {
                    return;
                }

                setTimeout(() => {
                    const anchor = document.getElementById(
                        "generated-draws-anchor"
                    );

                    if (anchor) {
                        anchor.scrollIntoView({
                            behavior: "smooth",
                            block: "start"
                        });
                    }
                }, 700);
            })();
            </script>
            """,
            unsafe_allow_javascript=True,
        )

    with st.expander("Preview parsed history"):
        preview = history.head(20).copy()
        preview["whites"] = preview["whites"].apply(
            lambda values: " - ".join(map(str, values))
        )
        st.dataframe(
            preview,
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Frequency preview"):
        white_frequency = build_frequency(
            history,
            cfg["white_min"],
            cfg["white_max"],
            "whites",
        )
        white_frequency_df = pd.DataFrame(
            [
                {
                    "Number": number,
                    "Times Drawn": count,
                }
                for number, count in white_frequency.items()
            ]
        ).sort_values(
            "Times Drawn",
            ascending=False,
        )

        st.write("White-ball frequency")
        st.dataframe(
            white_frequency_df.head(15),
            use_container_width=True,
            hide_index=True,
        )

        if cfg["has_bonus"]:
            bonus_frequency = build_frequency(
                history,
                cfg["bonus_min"],
                cfg["bonus_max"],
                "bonus",
            )
            bonus_frequency_df = pd.DataFrame(
                [
                    {
                        "Number": number,
                        "Times Drawn": count,
                    }
                    for number, count in bonus_frequency.items()
                ]
            ).sort_values(
                "Times Drawn",
                ascending=False,
            )

            st.write(f"{cfg['bonus_name']} frequency")
            st.dataframe(
                bonus_frequency_df.head(15),
                use_container_width=True,
                hide_index=True,
            )

except requests.HTTPError as error:
    st.error(
        "The public source could not be fetched. "
        "Try the upload option instead. "
        f"Details: {error}"
    )
except requests.RequestException as error:
    st.error(
        "A network error occurred while fetching lottery data. "
        f"Details: {error}"
    )
except Exception as error:
    st.error(str(error))


# ============================================================
# FOOTER / COPYRIGHT
# ============================================================

current_year = datetime.now().year

st.markdown(
    f"""
    <div class="site-footer">
        © {current_year} Craig Swackhammer and HammerPoint LLC. All rights reserved.
        Original site code, written content and custom graphics may not
        be reproduced or redistributed without permission.
        <br><br>
        Lottery numbers, jackpots, schedules and game rules are public
        information and are not claimed as proprietary. This site is not
        affiliated with or endorsed by Powerball, Mega Millions or the
        Texas Lottery.
        <br><br>
        Lottery drawings are random. Historical frequency and shape
        filters do not improve the mathematical odds of winning.
    </div>
    """,
    unsafe_allow_html=True,
)
