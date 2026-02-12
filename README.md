# Bonus Hedge Finder

A Python tool to find optimal bonus bet hedging opportunities across multiple sportsbooks using real-time odds from The Odds API.

## What It Does

This tool helps you maximize the value of sportsbook bonus bets (also called free bets or risk-free bets) by finding the best hedging opportunities. It:

- Fetches live odds from multiple sportsbooks
- Identifies opportunities where you can place a bonus bet on one book and hedge it on another
- Calculates guaranteed profit and efficiency for each opportunity
- Handles both US and US2 region sportsbooks automatically

## Features

- ✅ **Multi-region support** - Automatically queries both US and US2 regions when needed
- ✅ **Real-time odds** - Fetches current odds from The Odds API
- ✅ **Multiple sports** - Supports NBA, NCAAB, NFL, MLB, NHL, ATP, WTA
- ✅ **Customizable filters** - Set minimum efficiency thresholds
- ✅ **Clean output** - Formatted console display with all key information
- ✅ **Debug logging** - Detailed logs saved to `debug.log` for troubleshooting

## Installation

### Prerequisites

- Python 3.8 or higher
- The Odds API key ([get one free here](https://the-odds-api.com/))

### Setup

1. Clone this repository:
```bash
git clone https://github.com/louaih/bonus-hedge-finder.git
cd bonus-hedge-finder
```

2. Install required packages:
```bash
pip install requests
```

## Usage

### Basic Example

```bash
python bonus_hedge_finder.py \
  --api-key YOUR_API_KEY \
  --bonus-book ballybet \
  --books fanduel,draftkings,betmgm,betrivers \
  --sports nba,ncaab \
  --stake 250
```

### Parameters

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `--api-key` | Yes | Your The Odds API key | - |
| `--bonus-book` | Yes | Sportsbook where you have the bonus bet | - |
| `--books` | Yes | Comma-separated list of books to hedge on | - |
| `--sports` | No | Comma-separated list of sports to check | `nba,ncaab` |
| `--stake` | No | Bonus bet amount in dollars | `250` |
| `--min-eff` | No | Minimum efficiency threshold (0.0 to 1.0) | `0.0` |

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

### Supported Sports

- `nba` - NBA Basketball
- `ncaab` - NCAA Basketball
- `nfl` - NFL Football
- `mlb` - MLB Baseball
- `nhl` - NHL Hockey
- `atp` - ATP Tennis
- `wta` - WTA Tennis

## Example Input
```
 python .\main.py --api-key YOUR_API_KEY --stake 10 --bonus-book ballybet --sports nba,ncaab,ncaaf,nhl --books fanduel,draftkings,betmgm,betrivers,ballybet,espnbet
```
## Example Output

```
Event: Milwaukee Bucks @ Oklahoma City Thunder
Bonus: ballybet | Milwaukee Bucks @ +525
Hedge: fanduel | Oklahoma City Thunder @ -600
Hedge stake: $45.00
Locked profit: $7.50
Efficiency: 75.00%
```

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

⚠️ **Disclaimer**: This tool is for educational purposes. Always verify odds manually before placing bets. Odds can change between when the tool fetches them and when you place your bets.

⚠️ **Responsible Gaming**: Only use bonus bets you've legitimately earned. Follow all terms and conditions of your sportsbooks. Bet responsibly.

⚠️ **API Costs**: The Odds API has a free tier with limited requests. Each run of this tool uses API calls based on the number of sports and regions queried.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter issues or have questions:
1. Check the `debug.log` file for detailed information
2. Open an issue on GitHub
3. Make sure you're using the latest version

## Acknowledgments

- Powered by [The Odds API](https://the-odds-api.com/)
- Inspired by the sports betting arbitrage community

---

**Happy hedging! 🎯**