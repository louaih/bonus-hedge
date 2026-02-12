"""
bonus_hedge_finder.py
Correct region routing for us vs us2 using canonical bookmaker keys.
"""

from __future__ import annotations
import argparse
from dataclasses import dataclass
from typing import List, Optional
import requests
import sys
from datetime import datetime


# -----------------------
# LOGGING SETUP
# -----------------------

class Logger:
    def __init__(self, debug_file="debug.log"):
        self.debug_file = debug_file
        # Clear the debug file at start
        with open(self.debug_file, 'w') as f:
            f.write(f"=== Debug Log Started: {datetime.now()} ===\n\n")
    
    def debug(self, msg):
        """Write to debug file only"""
        with open(self.debug_file, 'a') as f:
            f.write(f"{msg}\n")
    
    def info(self, msg):
        """Write to console only"""
        print(msg)
    
    def both(self, msg):
        """Write to both console and debug file"""
        print(msg)
        with open(self.debug_file, 'a') as f:
            f.write(f"{msg}\n")

logger = Logger()


# -----------------------
# BOOK ALIASES (CRITICAL)
# -----------------------

BOOK_ALIASES = {
    # us
    "fanduel": "fanduel",
    "draftkings": "draftkings",
    "caesars": "williamhill_us",
    "betrivers": "betrivers",
    "fanatics": "fanatics",
    "betmgm": "betmgm",

    # us2
    "ballybet": "ballybet",
    "espnbet": "espnbet",
    "betparx": "betparx",
    "fliff": "fliff",
    "hardrockbet": "hardrockbet",
}

US_BOOKS = {
    "fanduel",
    "draftkings",
    "williamhill_us",
    "betrivers",
    "fanatics",
    "betmgm",
}

US2_BOOKS = {
    "ballybet",
    "espnbet",
    "betparx",
    "fliff",
    "hardrockbet",
}


def get_regions_needed(all_books: set[str]) -> list[str]:
    """Determine which region(s) to query based on books needed."""
    regions = []
    if all_books & US_BOOKS:
        regions.append("us")
    if all_books & US2_BOOKS:
        regions.append("us2")
    logger.debug(f"\n[DEBUG get_regions_needed] Books span regions: {regions}")
    return regions if regions else ["us"]


# -----------------------
# SPORTS
# -----------------------

SPORT_KEYS = {
    "nba": "basketball_nba",
    "ncaab": "basketball_ncaab",
    "ncaaf": "americanfootball_ncaaf",
    "eurobasketball": "basketball_euroleague",
    "nfl": "americanfootball_nfl",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl"
}


MARKETS = ["h2h"]


# -----------------------
# MATH
# -----------------------

def american_to_decimal(o: float) -> float:
    return 1 + (o / 100 if o > 0 else 100 / abs(o))


def bonus_hedge(stake: float, ob: float, oh: float):
    dA = american_to_decimal(ob)
    dB = american_to_decimal(oh)
    hedge = stake * (dA - 1) / dB
    profit = min(
        stake * (dA - 1) - hedge,
        hedge * (dB - 1),
    )
    return hedge, profit, profit / stake


# -----------------------
# DATA
# -----------------------

@dataclass
class Quote:
    event: str
    selection: str
    opposite: str
    bonus_book: str
    bonus_odds: float
    hedge_book: str
    hedge_odds: float
    hedge_stake: float
    profit: float
    efficiency: float


# -----------------------
# API
# -----------------------

def fetch_odds(api_key: str, sport_key: str, region: str):
    logger.debug(f"\n[DEBUG fetch_odds] Fetching odds for sport={sport_key}, region={region}")
    r = requests.get(
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
        params={
            "apiKey": api_key,
            "regions": region,
            "markets": "h2h",
            "oddsFormat": "american",
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    logger.debug(f"[DEBUG fetch_odds] Received {len(data)} events from {region}")
    return data


# -----------------------
# CORE
# -----------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--api-key", required=True)
    p.add_argument("--bonus-book", required=True)
    p.add_argument("--books", required=True)
    p.add_argument("--sports", default="nba,ncaab")
    p.add_argument("--stake", type=float, default=250)
    p.add_argument("--min-eff", type=float, default=0.0)
    args = p.parse_args()

    logger.debug("\n" + "="*60)
    logger.debug("DEBUG INFO - BONUS HEDGE FINDER")
    logger.debug("="*60)
    
    logger.debug(f"\n[DEBUG] Raw args.bonus_book: '{args.bonus_book}'")
    logger.debug(f"[DEBUG] Raw args.books: '{args.books}'")

    # Resolve user books → API books
    api_books = {
        BOOK_ALIASES[b.strip().lower()]
        for b in args.books.split(",")
    }
    
    logger.debug(f"\n[DEBUG] Parsed hedge books from --books: {api_books}")

    bonus_book = BOOK_ALIASES[args.bonus_book.lower()]
    logger.debug(f"[DEBUG] Resolved bonus_book: '{bonus_book}'")
    
    # Include bonus book when determining regions
    all_books = api_books | {bonus_book}
    logger.debug(f"\n[DEBUG] All books (hedge + bonus): {all_books}")
    
    regions = get_regions_needed(all_books)
    logger.debug(f"\n[DEBUG] REGIONS TO QUERY: {regions}")
    logger.debug("="*60 + "\n")

    rows = []

    for s in args.sports.split(","):
        sport_key = SPORT_KEYS[s.strip()]
        
        # Fetch from all needed regions
        for region in regions:
            events = fetch_odds(args.api_key, sport_key, region)

            for e in events:
                event = f"{e['away_team']} @ {e['home_team']}"
                logger.debug(f"\n[DEBUG] Processing event: {event} (region: {region})")
                logger.debug(f"[DEBUG] Available bookmakers in API response:")
                for bm in e["bookmakers"]:
                    logger.debug(f"  - {bm['key']}")
                
                for bm in e["bookmakers"]:
                    # Accept books if they're in api_books OR if they're the bonus book
                    if bm["key"] not in all_books:
                        logger.debug(f"[DEBUG] Skipping {bm['key']} (not in all_books)")
                        continue
                    logger.debug(f"[DEBUG] Including {bm['key']} (in all_books)")
                    for m in bm["markets"]:
                        if m["key"] != "h2h":
                            continue
                        a, b = m["outcomes"]
                        rows.append((event, a["name"], b["name"], bm["key"], a["price"]))
                        rows.append((event, b["name"], a["name"], bm["key"], b["price"]))

    logger.debug(f"\n[DEBUG] Total rows collected: {len(rows)}")
    logger.debug(f"[DEBUG] Books represented in rows:")
    unique_books = set(r[3] for r in rows)
    for book in unique_books:
        count = sum(1 for r in rows if r[3] == book)
        logger.debug(f"  - {book}: {count} rows")
    
    logger.debug(f"\n[DEBUG] Looking for bonus_book '{bonus_book}' in rows...")
    bonus_rows = [r for r in rows if r[3] == bonus_book]
    logger.debug(f"[DEBUG] Found {len(bonus_rows)} rows with bonus_book '{bonus_book}'")

    best = None

    for e, sel, opp, book, odds in rows:
        if book != bonus_book:
            continue
        for e2, sel2, _, book2, odds2 in rows:
            if e2 == e and sel2 == opp and book2 != book:
                hedge, profit, eff = bonus_hedge(args.stake, odds, odds2)
                if eff >= args.min_eff and (not best or eff > best.efficiency):
                    best = Quote(
                        e, sel, opp, book, odds,
                        book2, odds2, hedge, profit, eff
                    )

    if not best:
        logger.info("No valid bonus hedge found.")
        logger.debug("\n[DEBUG] No valid bonus hedge found.")
        logger.debug("[DEBUG] Possible reasons:")
        logger.debug(f"  - No matching opposite side found for bonus_book '{bonus_book}'")
        logger.debug(f"  - Efficiency below minimum threshold ({args.min_eff})")
        return

    # Print results to console
    logger.info(f"Event: {best.event}")
    logger.info(f"Bonus: {best.bonus_book} | {best.selection} @ {best.bonus_odds:+}")
    logger.info(f"Hedge: {best.hedge_book} | {best.opposite} @ {best.hedge_odds:+}")
    logger.info(f"Hedge stake: ${best.hedge_stake:.2f}")
    logger.info(f"Locked profit: ${best.profit:.2f}")
    logger.info(f"Efficiency: {best.efficiency*100:.2f}%")
    
    # Also log to debug file
    logger.debug(f"\n[RESULT] Event: {best.event}")
    logger.debug(f"[RESULT] Bonus: {best.bonus_book} | {best.selection} @ {best.bonus_odds:+}")
    logger.debug(f"[RESULT] Hedge: {best.hedge_book} | {best.opposite} @ {best.hedge_odds:+}")
    logger.debug(f"[RESULT] Hedge stake: ${best.hedge_stake:.2f}")
    logger.debug(f"[RESULT] Locked profit: ${best.profit:.2f}")
    logger.debug(f"[RESULT] Efficiency: {best.efficiency*100:.2f}%")


if __name__ == "__main__":
    main()
