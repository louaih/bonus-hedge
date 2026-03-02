# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Bonus Hedge Finder** — finds optimal hedging opportunities for sportsbook bonus bets using real-time odds from [The Odds API](https://the-odds-api.com/). Given a bonus bet on one book, it identifies the best counter-bet on another book to guarantee a locked profit.

**Important**: Profit calculations apply to bonus bets only, not cash bets.

## Running the Application

### CLI
```bash
python3 main.py \
    --api-key YOUR_API_KEY \
    --bonus-book fanduel \
    --books draftkings,betrivers \
    --sports nba,ncaab \
    --stake 250 \
    --min-eff 0.0
```

### GUI
```bash
python3 gui.py
```

### Dependencies
Only one external dependency:
```bash
pip install requests
```

## Architecture

Two entry points, one shared core:

- **`main.py`** — core logic + CLI. Can be imported by `gui.py`.
- **`gui.py`** — Tkinter GUI that calls into `main.py`'s functions directly (`collect_all_odds`, `find_all_opportunities`). Runs searches on a background thread with a progress callback.

### Core data flow (main.py)

```
parse_arguments()
  → parse_books() [resolve aliases e.g. "caesars" → "williamhill_us"]
  → get_regions_needed() [US vs US2 API endpoint]
  → collect_all_odds() [fetch_odds_for_sport() per sport/region → parse_event_odds()]
  → find_all_opportunities() [find_hedge_for_bonus() → calculate_hedge()]
  → select_best_opportunity() + log_best_opportunity()
```

### Key types (main.py ~line 98)
- `OddsRow` — a single odds line: event, selection, opposite side, book, odds (American)
- `HedgeOpportunity` — a matched pair: bonus book/odds, hedge book/odds, calculated stake, profit, efficiency

### Efficiency metric
`efficiency = guaranteed_profit / bonus_stake` (0.0–1.0). Typical good conversions are 70–90%.

### Sportsbook regions
- **US**: fanduel, draftkings, williamhill_us (caesars), betrivers, fanatics, betmgm
- **US2**: ballybet, espnbet, betparx, fliff, hardrockbet

Region is auto-detected from the books list. Cross-region searches make API calls to both endpoints.

## Configuration

`config.json` (gitignored) stores API key, allowed books, and sports for the GUI. See `config.json.example` for the format.

## Debugging

All activity is logged to `debug.log` (cleared on each run). Check this file when:
- No opportunities are found
- API errors occur (each run uses 2 API calls per sport per region)
- Investigating which bookmakers were available for a given event
