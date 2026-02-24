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
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": region,
        "markets": "h2h",
        "oddsFormat": "american",
    }
    
    logger.debug(f"\n[API] === Starting API Request ===")
    logger.debug(f"[API] URL: {url}")
    logger.debug(f"[API] Sport: {sport_key}")
    logger.debug(f"[API] Region: {region}")
    logger.debug(f"[API] Markets: h2h")
    logger.debug(f"[API] API Key length: {len(api_key)} chars")
    logger.debug(f"[API] API Key (first 10 chars): {api_key[:10]}...")
    logger.debug(f"[API] API Key (last 4 chars): ...{api_key[-4:]}")
    logger.debug(f"[API] Full params: {params}")
    
    try:
        logger.debug(f"[API] Sending GET request...")
        r = requests.get(url, params=params, timeout=30)
        
        logger.debug(f"[API] Response received")
        logger.debug(f"[API] Status code: {r.status_code}")
        logger.debug(f"[API] Response headers:")
        for key, value in r.headers.items():
            logger.debug(f"[API]   {key}: {value}")
        
        logger.debug(f"[API] Response URL: {r.url}")
        logger.debug(f"[API] Response encoding: {r.encoding}")
        logger.debug(f"[API] Response size: {len(r.content)} bytes")
        
        if r.status_code != 200:
            logger.debug(f"[API] ERROR - Non-200 status code")
            logger.debug(f"[API] Response text: {r.text}")
            logger.debug(f"[API] Reason: {r.reason}")
        
        r.raise_for_status()
        
        logger.debug(f"[API] Attempting to parse JSON...")
        data = r.json()
        
        logger.debug(f"[API] Successfully parsed JSON")
        logger.debug(f"[API] Response data type: {type(data)}")
        logger.debug(f"[API] Number of events: {len(data)}")
        
        if len(data) > 0:
            logger.debug(f"[API] First event preview:")
            first_event = data[0]
            logger.debug(f"[API]   Keys: {list(first_event.keys())}")
            logger.debug(f"[API]   ID: {first_event.get('id', 'N/A')}")
            logger.debug(f"[API]   Sport: {first_event.get('sport_key', 'N/A')}")
            logger.debug(f"[API]   Home: {first_event.get('home_team', 'N/A')}")
            logger.debug(f"[API]   Away: {first_event.get('away_team', 'N/A')}")
            logger.debug(f"[API]   Bookmakers: {len(first_event.get('bookmakers', []))}")
        else:
            logger.debug(f"[API] WARNING - Empty response (0 events)")
            logger.debug(f"[API] This could mean:")
            logger.debug(f"[API]   - No games currently available for this sport")
            logger.debug(f"[API]   - Region doesn't have odds for this sport")
            logger.debug(f"[API]   - API key may not have access to this region")
        
        logger.debug(f"[API] === Request Complete ===\n")
        return data
        
    except requests.exceptions.Timeout as e:
        logger.debug(f"[API] TIMEOUT ERROR after 30 seconds")
        logger.debug(f"[API] Error details: {str(e)}")
        logger.debug(f"[API] Check your internet connection")
        raise
    except requests.exceptions.HTTPError as e:
        logger.debug(f"[API] HTTP ERROR: {str(e)}")
        logger.debug(f"[API] Status code: {r.status_code}")
        logger.debug(f"[API] This typically means:")
        if r.status_code == 401:
            logger.debug(f"[API]   - Invalid API key")
        elif r.status_code == 403:
            logger.debug(f"[API]   - API key doesn't have permission")
        elif r.status_code == 429:
            logger.debug(f"[API]   - Rate limit exceeded")
        elif r.status_code >= 500:
            logger.debug(f"[API]   - Server error, try again later")
        raise
    except requests.exceptions.RequestException as e:
        logger.debug(f"[API] REQUEST ERROR: {type(e).__name__}")
        logger.debug(f"[API] Error details: {str(e)}")
        logger.debug(f"[API] This could be a network connectivity issue")
        raise
    except ValueError as e:
        logger.debug(f"[API] JSON PARSE ERROR: {str(e)}")
        logger.debug(f"[API] Response was not valid JSON")
        logger.debug(f"[API] First 500 chars of response: {r.text[:500]}")
        raise
    except Exception as e:
        logger.debug(f"[API] UNEXPECTED ERROR: {type(e).__name__}")
        logger.debug(f"[API] Error details: {str(e)}")
        import traceback
        logger.debug(f"[API] Traceback:\n{traceback.format_exc()}")
        raise


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
    
    logger.debug(f"\n[COLLECT] Starting odds collection")
    logger.debug(f"[COLLECT] Sports to fetch: {sports}")
    logger.debug(f"[COLLECT] Regions to query: {regions}")
    logger.debug(f"[COLLECT] Books to include: {allowed_books}")
    
    for sport in sports:
        sport_key = SPORT_KEYS[sport.strip()]
        logger.debug(f"\n[COLLECT] Processing sport: {sport} -> {sport_key}")
        
        for region in regions:
            logger.debug(f"[COLLECT] Fetching from region: {region}")
            
            try:
                events = fetch_odds_for_sport(api_key, sport_key, region)
                logger.debug(f"[COLLECT] Got {len(events)} events from API")
                
                events_processed = 0
                for event in events:
                    rows = parse_event_odds(event, allowed_books)
                    all_rows.extend(rows)
                    events_processed += 1
                    if rows:
                        logger.debug(f"[COLLECT] Event {events_processed}: extracted {len(rows)} odds rows")
                    
            except Exception as e:
                logger.debug(f"[COLLECT] ERROR fetching {sport_key} from {region}: {str(e)}")
                raise
    
    logger.debug(f"\n[COLLECT] Collection complete: {len(all_rows)} total odds rows")
    return all_rows


def log_collection_summary(rows: List[OddsRow]):
    """Log summary of collected odds data"""
    logger.debug(f"\n[SUMMARY] === Odds Collection Summary ===")
    logger.debug(f"[SUMMARY] Total odds collected: {len(rows)}")
    
    if len(rows) == 0:
        logger.debug(f"[SUMMARY] WARNING - No odds were collected!")
        logger.debug(f"[SUMMARY] Possible reasons:")
        logger.debug(f"[SUMMARY]   - No games available for selected sports")
        logger.debug(f"[SUMMARY]   - API key invalid or expired")
        logger.debug(f"[SUMMARY]   - Network connectivity issues")
        logger.debug(f"[SUMMARY]   - Books requested not available in region")
        return
    
    logger.debug(f"[SUMMARY] Books represented:")
    unique_books = set(r.book for r in rows)
    for book in unique_books:
        count = sum(1 for r in rows if r.book == book)
        logger.debug(f"[SUMMARY]   - {book}: {count} entries")
    
    logger.debug(f"[SUMMARY] Events represented:")
    unique_events = set(r.event for r in rows)
    logger.debug(f"[SUMMARY]   Total unique events: {len(unique_events)}")
    for event in sorted(unique_events)[:5]:  # Show first 5
        logger.debug(f"[SUMMARY]   - {event}")
    if len(unique_events) > 5:
        logger.debug(f"[SUMMARY]   ... and {len(unique_events) - 5} more")


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
    
    if len(bonus_rows) == 0:
        logger.debug(f"[SEARCH] WARNING - No odds found for bonus book '{bonus_book}'")
        logger.debug(f"[SEARCH] Available books in data: {set(r.book for r in rows)}")
    
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
    try:
        hedge_books = parse_books(args.books)
        bonus_book = BOOK_ALIASES[args.bonus_book.lower()]
    except KeyError as e:
        logger.debug(f"\n[ERROR] Invalid book name: {e}")
        logger.debug(f"[ERROR] Valid book names: {list(BOOK_ALIASES.keys())}")
        raise
    
    all_books = hedge_books | {bonus_book}
    regions = get_regions_needed(all_books)
    sports = args.sports.split(",")
    
    logger.debug(f"\n[CONFIG] Resolved bonus book: {bonus_book}")
    logger.debug(f"[CONFIG] Hedge books: {hedge_books}")
    logger.debug(f"[CONFIG] All books: {all_books}")
    logger.debug(f"[CONFIG] Regions to query: {regions}")
    logger.debug(f"[CONFIG] Sports to query: {sports}")
    
    # Collect odds data
    try:
        odds_rows = collect_all_odds(args.api_key, sports, regions, all_books)
    except Exception as e:
        logger.debug(f"\n[ERROR] Failed to collect odds: {str(e)}")
        logger.debug(f"[ERROR] Check debug.log for detailed API diagnostics")
        raise
    
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