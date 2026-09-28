# Bonus Hedge Finder

A Python tool to find optimal bonus bet hedging opportunities across multiple sportsbooks using real-time odds from The Odds API.

## What It Does

This tool helps you maximize the value of sportsbook bonus bets (also called free bets, risk-free bets, or second-chance bets) by finding the best hedging opportunities. It:

- Fetches live odds from multiple sportsbooks
- Identifies opportunities where you can place a bonus bet on one book and hedge it on another
- Calculates guaranteed profit and efficiency for each opportunity

## [Here's proof of it working](https://docs.google.com/spreadsheets/d/1iiVInLEaCCOvZZkHrFUrqcXIQZiTEjPqjcVDeYjGgiM/edit?usp=sharing)


## Installation

### Prerequisites

- Python 3.8 or higher
- The Odds API key ([get one free here](https://the-odds-api.com/))

### Setup

1. Clone this repository:
```bash
git clone https://github.com/louaih/bonus-hedge.git
cd bonus-hedge
```

2. Install required packages:
```bash
pip install requests
```

## Usage

### Basic Example

#### Input
```bash
python3 main.py \
    --api-key YOUR_API_KEY \
    --bonus-book fanduel \
    --books draftkings \
    --sports nba \
    --stake 250
```
### Output
```
Event: Dallas Mavericks @ Los Angeles Lakers
Bonus: fanduel | Dallas Mavericks @ +260
Hedge: draftkings | Los Angeles Lakers @ -305
Hedge stake: $489.51
Locked profit: $160.49
Efficiency: 64.20%
```

### Parameters

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `--api-key` | ✅ | Your The Odds API key | - |
| `--mode` | ❌ | `bonus`, `alt_bonus`, or `qualifying` (see below) | `bonus` |
| `--bonus-book` | ✅ | Sportsbook where you have the bonus bet | - |
| `--books` | ✅ | Comma-separated list of books to hedge on | - |
| `--sports` | ❌ | Comma-separated list of sports to check | `nba,ncaab` |
| `--stake` | ❌| Bonus/qualifying bet amount in dollars | `250` |
| `--min-eff` | ❌ | Minimum efficiency threshold, `bonus`/`alt_bonus` mode (0.0 to 1.0) | `0.0` |
| `--max-loss` | ❌ | Max acceptable loss as a fraction of stake, `qualifying` mode | `1.0` |

**Modes:**
- `bonus` — standard free bet: a win pays out only the winnings (the stake itself is forfeited by the book).
- `alt_bonus` — a bonus/free bet variant where a win pays out the stake as well as the winnings (nothing is ever at risk either way, but a win returns the full decimal payout). Sizes the hedge like a qualifying bet but tracks the guaranteed outcome as profit rather than loss, since it's still bonus money.
- `qualifying` — a real cash bet: hedges to minimize guaranteed loss (or find a true arbitrage) since your own stake is at risk.

### Supported Sportsbooks

**US Region:**
- `fanduel` - FanDuel
- `draftkings` - DraftKings
- `caesars` - Caesars (formerly William Hill)
- `betrivers` - BetRivers
- `fanatics` - Fanatics
- `betmgm` - BetMGM

**US2 Region:**
- `ballybet` - Bally Bet
- `espnbet` - ESPN BET
- `betparx` - BetParx
- `fliff` - Fliff
- `hardrockbet` - Hard Rock Bet

**US Exchange Region (`us_ex`):**
- `novig` - Novig
- `polymarket` - Polymarket

Exchange-style books publish a single best price per side rather than a traditional fixed line, but The Odds API normalizes them into the same `{name, price}` shape as every other bookmaker, so they work as both bonus/qualifying books and hedge books without any special handling. Including one adds an extra API call per sport (one per region queried).

### Supported Sports

- `nba` - NBA Basketball
- `ncaab` - NCAA Basketball
- `ncaaf` - NCAA Football
- `nfl` - NFL Football
- `mlb` - MLB Baseball
- `nhl` - NHL Hockey
- `eurobasketball` - Euroleague Basketball

## Web GUI

A browser-based GUI (`web_gui.py`) exposes the same search and manual calculator as the desktop Tkinter GUI, backed by a Flask app. It's meant to be run on a server (e.g. a VPS) so you can use it from any device.

### Local run

```bash
pip install -r requirements.txt
python3 web_gui.py
```

On first run it prints a generated username/password (also saved to `web_gui_auth.json`, which is gitignored). Open `http://localhost:8080` and log in with those credentials. Set `WEBGUI_USER`/`WEBGUI_PASSWORD` env vars to pick your own credentials instead.

The API key is entered in the browser and kept only in that browser's `localStorage` — it is never written to disk on the server. Selected sports/books can optionally be saved server-side via "Save Sports/Books" (stored in `config.json`, same file the CLI/Tkinter GUI use).

### Production deployment (systemd + gunicorn)

Run on the server as root (installs into `/opt/bonus-hedge`, sets up a venv, and enables a systemd service on port 8080):

```bash
curl -fsSL https://raw.githubusercontent.com/louaih/bonus-hedge/claude/web-gui-vps-deploy-snxay6/deploy/deploy.sh | bash
```

Or, if you've already cloned the repo on the server:

```bash
cd /opt/bonus-hedge && bash deploy/deploy.sh
```

Re-running the script later pulls the latest commit on that branch and restarts the service — use it to deploy updates too. Login credentials are generated on first run and printed at the end (also saved to `/opt/bonus-hedge/web_gui_auth.json`); set `WEBGUI_USER`/`WEBGUI_PASSWORD` env vars before running it to pick your own instead.

The service runs gunicorn bound to `0.0.0.0:8080` — since the app is guarded only by HTTP Basic Auth and no TLS, treat the port like an internal admin panel: put it behind a firewall rule (only your IP) or a reverse proxy with HTTPS if it needs to be reachable from the open internet.

## How It Works

1. **Region Detection**: The tool automatically detects which API regions to query based on the sportsbooks you specify
2. **Odds Fetching**: Fetches real-time odds from both regions if needed (e.g., if you want to hedge Bally Bet with FanDuel)
3. **Opportunity Scanning**: Compares all odds to find the best hedging opportunities
4. **Profit Calculation**: Uses the formula for guaranteed profit to calculate your locked-in return
5. **Best Selection**: Returns the opportunity with the highest efficiency

### Efficiency Explained

Efficiency is calculated as: `guaranteed_profit / bonus_stake`

For example, if you have a $250 bonus bet:
- 100% efficiency = You keep the full $250 as profit
- 75% efficiency = You keep $187.50 as profit
- 50% efficiency = You keep $125 as profit

Typical bonus bet conversions achieve 70-90% efficiency depending on the odds available.

## Tips for Best Results

1. **Check multiple sports** - More sports = more opportunities
2. **Time it right** - Odds change frequently; run the tool when you're ready to place bets
3. **Lower your minimum** - Setting `--min-eff 0.0` shows all opportunities, even less efficient ones
4. **Include multiple books** - More hedge options = better chances of finding optimal lines
5. **Act quickly** - Odds can change rapidly, place your bets as soon as you find a good opportunity

## Troubleshooting

### No opportunities found?

- Try lowering `--min-eff` to `0.0`
- Add more sports to `--sports`
- Add more sportsbooks to `--books`
- Check `debug.log` to see which books and events were found

### API errors?

- Verify your API key is correct
- Check your API usage limits at [The Odds API dashboard](https://the-odds-api.com/)
- Each run uses 2 API calls per sport per region

## Debug Logging

All debug information is automatically saved to `debug.log` including:
- API requests and responses
- Region selection logic
- Available bookmakers for each event
- Full list of opportunities considered

This is helpful for troubleshooting or understanding why certain opportunities were or weren't found.

## Important Notes

⚠️ **Disclaimer**: **PROFIT CALCULATIONS APPLY TO BONUS BETS ONLY!!!!!! NOT CASH BETS!!!** This tool is for educational purposes ONLY. Always verify odds manually before placing bets. Odds can change between when the tool fetches them and when you place your bets.

⚠️ **Responsible Gaming**: Follow all terms and conditions of your sportsbooks. Bet responsibly.

⚠️ **API Costs**: The Odds API has a free tier with limited requests. Each run of this tool uses API calls based on the number of sports and regions queried.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter issues:
1. Check the `debug.log` file for detailed information
2. Feed debug info into LLM
3. Make branch and paste changes
4. Submit a PR

If you have questions: open an issue

## Acknowledgments

- Powered by [The Odds API](https://the-odds-api.com/)
- Inspired by the sports betting arbitrage community

---

### **Happy hedging! 🎯**