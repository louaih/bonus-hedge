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
| `--bonus-book` | ✅ | Sportsbook where you have the bonus bet | - |
| `--books` | ✅ | Comma-separated list of books to hedge on | - |
| `--sports` | ❌ | Comma-separated list of sports to check | `nba,ncaab` |
| `--stake` | ❌| Bonus bet amount in dollars | `250` |
| `--min-eff` | ❌ | Minimum efficiency threshold (0.0 to 1.0) | `0.0` |

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
- `ncaaf` - NCAA Football
- `nfl` - NFL Football
- `mlb` - MLB Baseball
- `nhl` - NHL Hockey
- `eurobasketball` - Euroleague Basketball

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