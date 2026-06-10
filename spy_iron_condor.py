"""
SPY IRON CONDOR BACKTEST TOOL

This script backtests an Iron Condor options strategy on SPY (S&P 500 ETF).

STRATEGY:
- Each trading day, create a synthetic Iron Condor centered at: OPEN + X (user input)
- Short Put: Center Strike - 5
- Long Put: Center Strike - 10
- Short Call: Center Strike + 5
- Long Call: Center Strike + 10
- Credit received per contract: $1.50 ($150)
- Max profit: $150 (collected credit)
- Max loss: $350 (width - credit)

PROFIT/LOSS CALCULATION:
- If SPY closes within $5 of center: +$150 (max profit)
- If SPY closes $6 away: +$50
- If SPY closes $7 away: -$50
- If SPY closes $8 away: -$150
- If SPY closes $9 away: -$250
- If SPY closes $10+ away: -$350 (max loss)

INPUT PARAMETERS:
1. Starting Capital: Your initial trading capital
2. Center Offset: How far from open price to set center strike (default: 2)
3. Show Daily Details: Print all daily trades (yes/no)

OUTPUT:
- Trading statistics (win rate, total profit, best/worst days, streaks)
- Capital analysis (starting, ending, percentage return)
- Capital depletion warning if applicable
- CSV file with all daily trades
- First 20 and last 20 trading days

DATA SOURCE:
- Uses Yahoo Finance (yfinance) - completely free
- Date range: 2019-06-01 to 2026-06-01 (7 years)
"""

import yfinance as yf
from datetime import datetime
import csv

print("SPY IRON CONDOR BACKTEST")
print("="*60)

START_DATE = "2019-06-01"
END_DATE = "2026-06-01"

# Strategy parameters (easily modifiable)
CREDIT = 150  # $1.50 per contract × 100 shares
MAX_PROFIT = 150
MAX_LOSS = 350
SHORT_STRIKE_DISTANCE = 5  # $5 from center
LONG_STRIKE_DISTANCE = 10  # $10 from center

# Get user input
print("\nEnter backtest parameters:")
starting_capital = float(input("Starting Capital ($): "))
center_offset = float(input("Center Strike Offset (default 2): ") or "2")
show_daily_details = input("Show daily gain/loss details? (yes/no): ").strip().lower() == "yes"

print(f"\nBacktest Settings:")
print(f"Center Strike: OPEN + ${center_offset:.2f}")
print(f"Starting Capital: ${starting_capital:,.2f}")
print(f"Credit Received: ${CREDIT:.2f}")
print(f"Max Profit: ${MAX_PROFIT:.2f}")
print(f"Max Loss: ${MAX_LOSS:.2f}")
print(f"Date Range: {START_DATE} to {END_DATE} (7 YEARS)")
print("="*60)

# Download SPY data from Yahoo Finance (FREE!)
print("\nDownloading SPY data from Yahoo Finance...")
spy_data = yf.download("SPY", start=START_DATE, end=END_DATE, progress=False)
print(f"Downloaded {len(spy_data)} trading days")

if len(spy_data) == 0:
    print("No data returned. Check your date range.")
    exit()

# Data storage
results = []
daily_pnl = []
winning_days = 0
losing_days = 0
breakeven_days = 0
total_profit = 0
current_capital = starting_capital
capital_depleted_date = None
capital_depleted = False

# Process each day
# Process each day
spy_data.columns = spy_data.columns.get_level_values(0)

for date, row in spy_data.iterrows():

    date = date.date()

    open_price = float(row["Open"])
    close_price = float(row["Close"])


    center_strike = open_price + center_offset

    distance = abs(close_price - center_strike)

    if distance <= 5:
        profit_loss = 150

    elif distance <= 6:
        profit_loss = 50

    elif distance <= 7:
        profit_loss = -50

    elif distance <= 8:
        profit_loss = -150

    elif distance <= 9:
        profit_loss = -250

    else:
        profit_loss = -350

    current_capital += profit_loss

    if current_capital <= 0 and not capital_depleted:
        capital_depleted_date = date
        capital_depleted = True

    if profit_loss > 0:
        winning_days += 1
    elif profit_loss < 0:
        losing_days += 1
    else:
        breakeven_days += 1

    total_profit += profit_loss
    daily_pnl.append(profit_loss)

    results.append({
        "date": date,
        "open": open_price,
        "close": close_price,
        "center_strike": center_strike,
        "distance": distance,
        "profit_loss": profit_loss,
        "capital": current_capital
    })

# Print daily details if requested
if show_daily_details:
    print("\n" + "="*60)
    print("DAILY GAIN/LOSS (ALL DAYS)")
    print("="*60)
    for row in results:
        status = "WIN" if row['profit_loss'] > 0 else "LOSS" if row['profit_loss'] < 0 else "EVEN"
        print(f"{row['date']} | ${row['profit_loss']:+.2f} | {status}")
    print("="*60)

# Calculate streaks
winning_streak = 0
losing_streak = 0
max_winning_streak = 0
max_losing_streak = 0

for pnl in daily_pnl:
    if pnl > 0:
        winning_streak += 1
        losing_streak = 0
        max_winning_streak = max(max_winning_streak, winning_streak)
    elif pnl < 0:
        losing_streak += 1
        winning_streak = 0
        max_losing_streak = max(max_losing_streak, losing_streak)
    else:
        winning_streak = 0
        losing_streak = 0

# Calculate statistics
total_days = len(results)
win_rate = (winning_days / total_days * 100) if total_days > 0 else 0
avg_profit = total_profit / total_days if total_days > 0 else 0
best_day = max(daily_pnl) if daily_pnl else 0
worst_day = min(daily_pnl) if daily_pnl else 0
ending_capital = starting_capital + total_profit
percentage_return = (total_profit / starting_capital * 100) if starting_capital > 0 else 0

# Export to CSV
csv_filename = f"spy_iron_condor_offset_{center_offset}_results.csv"
with open(csv_filename, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['date', 'open', 'close', 'center_strike', 'distance', 'profit_loss', 'capital'])
    for row in results:
        writer.writerow([row['date'], row['open'], row['close'], row['center_strike'], row['distance'], row['profit_loss'], row['capital']])

# Print summary statistics
print("\n" + "="*60)
print("IRON CONDOR BACKTEST RESULTS (7 YEARS)")
print("="*60)
print(f"Total Trading Days: {total_days}")
print(f"Winning Days: {winning_days}")
print(f"Losing Days: {losing_days}")
print(f"Breakeven Days: {breakeven_days}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Total Profit: ${total_profit:,.2f}")
print(f"Average Profit Per Day: ${avg_profit:.2f}")
print(f"Best Day: ${best_day:.2f}")
print(f"Worst Day: ${worst_day:.2f}")
print(f"Largest Winning Streak: {max_winning_streak} consecutive days of profit")
print(f"Largest Losing Streak: {max_losing_streak} consecutive days of losses")
print("="*60)

print("\n" + "="*60)
print("CAPITAL ANALYSIS")
print("="*60)
print(f"Starting Capital: ${starting_capital:,.2f}")
print(f"Ending Capital: ${ending_capital:,.2f}")
print(f"Percentage Return: {percentage_return:.2f}%")

if capital_depleted:
    print(f"\n⚠️  CAPITAL DEPLETED on: {capital_depleted_date}")
else:
    print(f"\n✅ Capital never depleted")
print("="*60)

# Print first 20 trades
print("\n" + "="*60)
print("FIRST 20 TRADING DAYS")
print("="*60)
for i, row in enumerate(results[:20], 1):
    status = "WIN" if row['profit_loss'] > 0 else "LOSS" if row['profit_loss'] < 0 else "EVEN"
    print(f"{row['date']} | ${row['profit_loss']:+.2f} | {status}")

# Print last 20 trades
print("\n" + "="*60)
print("LAST 20 TRADING DAYS")
print("="*60)
start_idx = max(0, len(results) - 20)
for i, row in enumerate(results[start_idx:], start_idx + 1):
    status = "WIN" if row['profit_loss'] > 0 else "LOSS" if row['profit_loss'] < 0 else "EVEN"
    print(f"{row['date']} | ${row['profit_loss']:+.2f} | {status}")

print("\n" + "="*60)
print(f"Results exported to: {csv_filename}")
print("="*60)
print("\nBACKTEST COMPLETE!")