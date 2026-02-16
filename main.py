from __future__ import annotations
import argparse
from dataclasses import dataclass
from typing import List, Optional, Tuple
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
            f.write(f"[DEBUG] {msg}\n")
    
    def info(self, msg):
        """Write to log file only"""
        with open(self.debug_file, 'a') as f:
            f.write(f"[INFO] {msg}\n")
    
    def console(self, msg):
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

SPORT_KEYS = {
    "nba": "basketball_nba",
    "ncaab": "basketball_ncaab",
    "ncaaf": "americanfootball_ncaaf",
    "eurobasketball": "basketball_euroleague",
    "nfl": "americanfootball_nfl",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl"
}


# -----------------------
# DATA STRUCTURES
# -----------------------

@dataclass
class OddsRow:
    """Single odds entry from a bookmaker"""
    event: str
    selection: str
    opposite: str
    book: str
    odds: float


@dataclass
class HedgeOpportunity:
    """Calculated hedge opportunity"""
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
# CONFIGURATION
# -----------------------

def parse_books(book_string: str) -> set[str]:
    """Parse comma-separated book names into API book keys"""
    return {
        BOOK_ALIASES[b.strip().lower()]
        for b in book_string.split(",")
    }


def get_regions_needed(all_books: set[str]) -> list[str]:
    """Determine which region(s) to query based on books needed."""
    regions = []
    if all_books & US_BOOKS:
        regions.append("us")
    if all_books & US2_BOOKS:
        regions.append("us2")
    return regions if regions else ["us"]


# -----------------------
# MATH
# -----------------------

def american_to_decimal(o: float) -> float:
    """Convert American odds to decimal odds"""
    return 1 + (o / 100 if o > 0 else 100 / abs(o))


def calculate_hedge(stake: float, bonus_odds: float, hedge_odds: float) -> Tuple[float, float, float]:
    """
    Calculate hedge stake, profit, and efficiency
    
    Returns:
        (hedge_stake, profit, efficiency)
    """
    dA = american_to_decimal(bonus_odds)
    dB = american_to_decimal(hedge_odds)
    hedge = stake * (dA - 1) / dB
    profit = min(
        stake * (dA - 1) - hedge,
        hedge * (dB - 1),
    )
    efficiency = profit / stake
    return hedge, profit, efficiency


# -----------------------
# API
# -----------------------

def fetch_odds_for_sport(api_key: str, sport_key: str, region: str) -> list:
    """Fetch odds for a single sport from a single region"""
    logger.debug(f"\n[API] Fetching {sport_key} odds from {region}")
    
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
    
    logger.debug(f"[API] Received {len(data)} events")
    return data


# -----------------------
# DATA EXTRACTION
# -----------------------

def extract_event_name(event_data: dict) -> str:
    """Extract formatted event name from API response"""
    return f"{event_data['away_team']} @ {event_data['home_team']}"


def extract_outcomes(market: dict) -> Tuple[dict, dict]:
    """Extract the two outcomes from a market"""
    outcomes = market["outcomes"]
    if len(outcomes) != 2:
        raise ValueError(f"Expected 2 outcomes, got {len(outcomes)}")
    return outcomes[0], outcomes[1]


def parse_event_odds(event_data: dict, allowed_books: set[str]) -> List[OddsRow]:
    """
    Parse all odds from a single event
    
    Args:
        event_data: Raw event data from API
        allowed_books: Set of book keys to include
        
    Returns:
        List of OddsRow objects
    """
    event_name = extract_event_name(event_data)
    rows = []
    
    logger.debug(f"\n[PARSE] Event: {event_name}")
    logger.debug(f"[PARSE] Available books: {[bm['key'] for bm in event_data['bookmakers']]}")
    
    for bookmaker in event_data["bookmakers"]:
        book_key = bookmaker["key"]
        
        if book_key not in allowed_books:
            logger.debug(f"[PARSE] Skipping {book_key} (not in allowed books)")
            continue
            
        logger.debug(f"[PARSE] Including {book_key}")
        
        for market in bookmaker["markets"]:
            if market["key"] != "h2h":
                continue
                
            outcome_a, outcome_b = extract_outcomes(market)
            
            # Create rows for both sides of the market
            rows.append(OddsRow(
                event=event_name,
                selection=outcome_a["name"],
                opposite=outcome_b["name"],
                book=book_key,
                odds=outcome_a["price"]
            ))
            rows.append(OddsRow(
                event=event_name,
                selection=outcome_b["name"],
                opposite=outcome_a["name"],
                book=book_key,
                odds=outcome_b["price"]
            ))
    
    return rows


def collect_all_odds(api_key: str, sports: List[str], regions: List[str], allowed_books: set[str]) -> List[OddsRow]:
    """
    Collect all odds across sports and regions
    
    Args:
        api_key: API key for odds service
        sports: List of sport keys to fetch
        regions: List of regions to query
        allowed_books: Set of book keys to include
        
    Returns:
        List of all OddsRow objects
    """
    all_rows = []
    
    for sport in sports:
        sport_key = SPORT_KEYS[sport.strip()]
        
        for region in regions:
            events = fetch_odds_for_sport(api_key, sport_key, region)
            
            for event in events:
                rows = parse_event_odds(event, allowed_books)
                all_rows.extend(rows)
    
    return all_rows


def log_collection_summary(rows: List[OddsRow]):
    """Log summary of collected odds data"""
    logger.debug(f"\n[SUMMARY] Total odds collected: {len(rows)}")
    logger.debug("[SUMMARY] Books represented:")
    
    unique_books = set(r.book for r in rows)
    for book in unique_books:
        count = sum(1 for r in rows if r.book == book)
        logger.debug(f"  - {book}: {count} entries")


# -----------------------
# HEDGE FINDING
# -----------------------

def find_hedge_for_bonus(
    bonus_row: OddsRow,
    all_rows: List[OddsRow],
    stake: float
) -> List[HedgeOpportunity]:
    """
    Find all possible hedge opportunities for a given bonus bet
    
    Args:
        bonus_row: The bonus bet to hedge
        all_rows: All available odds
        stake: Bonus bet stake amount
        
    Returns:
        List of HedgeOpportunity objects
    """
    opportunities = []
    
    for row in all_rows:
        # Must be same event, opposite selection, different book
        if (row.event == bonus_row.event and 
            row.selection == bonus_row.opposite and 
            row.book != bonus_row.book):
            
            hedge_stake, profit, efficiency = calculate_hedge(
                stake, bonus_row.odds, row.odds
            )
            
            opportunities.append(HedgeOpportunity(
                event=bonus_row.event,
                selection=bonus_row.selection,
                opposite=bonus_row.opposite,
                bonus_book=bonus_row.book,
                bonus_odds=bonus_row.odds,
                hedge_book=row.book,
                hedge_odds=row.odds,
                hedge_stake=hedge_stake,
                profit=profit,
                efficiency=efficiency
            ))
    
    return opportunities


def find_all_opportunities(
    rows: List[OddsRow],
    bonus_book: str,
    stake: float,
    min_efficiency: float
) -> List[HedgeOpportunity]:
    """
    Find all hedge opportunities that meet minimum efficiency
    
    Args:
        rows: All available odds
        bonus_book: The book offering the bonus
        stake: Bonus bet stake amount
        min_efficiency: Minimum efficiency threshold (0.0 to 1.0)
        
    Returns:
        List of HedgeOpportunity objects meeting criteria
    """
    logger.debug(f"\n[SEARCH] Looking for hedges with bonus_book='{bonus_book}'")
    
    bonus_rows = [r for r in rows if r.book == bonus_book]
    logger.debug(f"[SEARCH] Found {len(bonus_rows)} bonus opportunities")
    
    all_opportunities = []
    
    for bonus_row in bonus_rows:
        opportunities = find_hedge_for_bonus(bonus_row, rows, stake)
        all_opportunities.extend(opportunities)
    
    # Filter by minimum efficiency
    filtered = [opp for opp in all_opportunities if opp.efficiency >= min_efficiency]
    
    logger.debug(f"[SEARCH] Found {len(all_opportunities)} total opportunities")
    logger.debug(f"[SEARCH] {len(filtered)} meet minimum efficiency of {min_efficiency*100:.2f}%")
    
    return filtered


def select_best_opportunity(opportunities: List[HedgeOpportunity]) -> Optional[HedgeOpportunity]:
    """Select the opportunity with highest efficiency"""
    if not opportunities:
        return None
    return max(opportunities, key=lambda x: x.efficiency)


# -----------------------
# OUTPUT
# -----------------------

def log_opportunity(opp: HedgeOpportunity, stake: float):
    """Log a single hedge opportunity to log file"""
    logger.info(f"\n{opp.event}")
    logger.info(f"  Bonus: {opp.bonus_book} | {opp.selection} @ {opp.bonus_odds:+} (stake: ${stake:.2f})")
    logger.info(f"  Hedge: {opp.hedge_book} | {opp.opposite} @ {opp.hedge_odds:+} (stake: ${opp.hedge_stake:.2f})")
    logger.info(f"  → Profit: ${opp.profit:.2f} | Efficiency: {opp.efficiency*100:.2f}%")


def log_all_opportunities(opportunities: List[HedgeOpportunity], stake: float):
    """Log all tested opportunities"""
    logger.info("\n" + "="*80)
    logger.info(f"TESTING {len(opportunities)} BONUS HEDGE OPPORTUNITIES")
    logger.info("="*80)
    
    for opp in opportunities:
        log_opportunity(opp, stake)


def log_best_opportunity(opp: HedgeOpportunity):
    """Log the best opportunity - summary to console, details to log"""
    # Console output - clean and concise
    logger.console("\n" + "="*80)
    logger.console("BEST BONUS HEDGE OPPORTUNITY")
    logger.console("="*80)
    logger.console(f"Event: {opp.event}")
    logger.console(f"Bonus: {opp.bonus_book} | {opp.selection} @ {opp.bonus_odds:+}")
    logger.console(f"Hedge: {opp.hedge_book} | {opp.opposite} @ {opp.hedge_odds:+}")
    logger.console(f"Hedge stake: ${opp.hedge_stake:.2f}")
    logger.console(f"Locked profit: ${opp.profit:.2f}")
    logger.console(f"Efficiency: {opp.efficiency*100:.2f}%")
    logger.console("="*80)
    
    # Log file output
    logger.info("\n[RESULT] Best opportunity found:")
    logger.info(f"[RESULT] Event: {opp.event}")
    logger.info(f"[RESULT] Bonus: {opp.bonus_book} | {opp.selection} @ {opp.bonus_odds:+}")
    logger.info(f"[RESULT] Hedge: {opp.hedge_book} | {opp.opposite} @ {opp.hedge_odds:+}")
    logger.info(f"[RESULT] Hedge stake: ${opp.hedge_stake:.2f}")
    logger.info(f"[RESULT] Profit: ${opp.profit:.2f}")
    logger.info(f"[RESULT] Efficiency: {opp.efficiency*100:.2f}%")


def log_no_opportunities():
    """Log when no valid opportunities are found"""
    logger.console("\n" + "="*80)
    logger.console("No valid bonus hedge found.")
    logger.console("="*80)
    
    logger.info("\n[RESULT] No valid bonus hedge found")
    logger.info("[RESULT] Check minimum efficiency threshold or available odds")


# -----------------------
# MAIN
# -----------------------

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Find optimal bonus bet hedges")
    parser.add_argument("--api-key", required=True, help="API key for odds service")
    parser.add_argument("--bonus-book", required=True, help="Book offering the bonus")
    parser.add_argument("--books", required=True, help="Comma-separated list of books to hedge with")
    parser.add_argument("--sports", default="nba,ncaab", help="Comma-separated list of sports")
    parser.add_argument("--stake", type=float, default=250, help="Bonus bet stake amount")
    parser.add_argument("--min-eff", type=float, default=0.0, help="Minimum efficiency (0.0 to 1.0)")
    return parser.parse_args()


def main():
    args = parse_arguments()
    
    # Log startup info
    logger.debug("\n" + "="*60)
    logger.debug("BONUS HEDGE FINDER")
    logger.debug("="*60)
    logger.debug(f"Bonus book: {args.bonus_book}")
    logger.debug(f"Hedge books: {args.books}")
    logger.debug(f"Sports: {args.sports}")
    logger.debug(f"Stake: ${args.stake}")
    logger.debug(f"Min efficiency: {args.min_eff*100}%")
    
    # Parse configuration
    hedge_books = parse_books(args.books)
    bonus_book = BOOK_ALIASES[args.bonus_book.lower()]
    all_books = hedge_books | {bonus_book}
    regions = get_regions_needed(all_books)
    sports = args.sports.split(",")
    
    logger.debug(f"\n[CONFIG] Resolved bonus book: {bonus_book}")
    logger.debug(f"[CONFIG] Hedge books: {hedge_books}")
    logger.debug(f"[CONFIG] Regions to query: {regions}")
    
    # Collect odds data
    odds_rows = collect_all_odds(args.api_key, sports, regions, all_books)
    log_collection_summary(odds_rows)
    
    # Find opportunities
    opportunities = find_all_opportunities(
        odds_rows,
        bonus_book,
        args.stake,
        args.min_eff
    )
    
    # Display results
    if not opportunities:
        log_no_opportunities()
        return
    
    log_all_opportunities(opportunities, args.stake)
    
    best = select_best_opportunity(opportunities)
    log_best_opportunity(best)


if __name__ == "__main__":
    main()