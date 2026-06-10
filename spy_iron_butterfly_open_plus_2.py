import requests
from datetime import datetime
import csv

print("SPY IRON BUTTERFLY BACKTEST")
print("="*60)

API_KEY = "kFOG0Gl6TUrhzWX1NKMekuNeKfXJ0KBL"
START_DATE = "2019-06-01"
END_DATE = "2026-06-01"

# Get user input
print("\nEnter backtest parameters:")
center_offset = float(input("Center Strike Offset (e.g., 2 for OPEN + $2): "))
starting_capital = float(input("Starting Capital ($): "))
show_daily_details = input("Show daily gain/loss details? (yes/no): ").strip().lower() == "yes"

print(f"\nBacktest Settings:")
print(f"Center Strike: OPEN + ${center_offset:.2f}")
print(f"Starting Capital: ${starting_capital:,.2f}")
print(f"Date Range: {START_DATE} to {END_DATE} (7 YEARS)")
print("="*60)

# Download SPY data from API (split into chunks to avoid limit)
print("\nDownloading SPY data (7 years in chunks)...")

# Split into multiple date ranges
date_ranges = [
    ("2019-06-01", "2020-12-31"),
    ("2021-01-01", "2022-12-31"),
    ("2023-01-01", "2024-12-31"),
    ("2025-01-01", "2026-06-01")
]

rows = []

for start, end in date_ranges:
    print(f"Downloading {start} to {end}...")
    url = f"https://api.polygon.io/v2/aggs/ticker/SPY/range/1/day/{start}/{end}"
    response = requests.get(url, params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": API_KEY})
    
    print(f"HTTP Status: {response.status_code}")
    
    data = response.json()
    chunk_rows = data.get("results", [])
    print(f"Rows returned: {len(chunk_rows)}")
    
    rows.extend(chunk_rows)

print(f"\nTotal rows downloaded: {len(rows)}")

if len(rows) == 0:
    print("No data returned. Check your date range and API key.")
    exit()

# Data storage
results = []
daily_pnl = []
winning_days = 0
losing_days = 0
total_profit = 0
current_capital = starting_capital
capital_depleted_date = None
capital_depleted = False

# Process each day
for row in rows:
    date = datetime.fromtimestamp(row["t"] / 1000).date()
    open_price = row["o"]
    close_price = row["c"]
    
    center_strike = open_price + center_offset
    distance = abs(close_price - center_strike)
    
    # Calculate profit/loss
    if distance <= 3:
        profit_loss = (3 - distance) * 100
    elif distance == 4:
        profit_loss = -100
    else:  # distance >= 5
        profit_loss = -200
    
    # Update capital
    current_capital += profit_loss
    
    # Track if capital goes to zero or below
    if current_capital <= 0 and not capital_depleted:
        capital_depleted_date = date
        capital_depleted = True
    
    # Track statistics
    if profit_loss > 0:
        winning_days += 1
    elif profit_loss < 0:
        losing_days += 1
    
    total_profit += profit_loss
    daily_pnl.append(profit_loss)
    
    results.append({
        'date': date,
        'open': open_price,
        'close': close_price,
        'center_strike': center_strike,
        'distance': distance,
        'profit_loss': profit_loss,
        'capital': current_capital
    })

# Print daily details if requested (ONLY DATE AND P&L)
if show_daily_details:
    print("\n" + "="*50)
    print("DAILY GAIN/LOSS (ALL DAYS)")
    print("="*50)
    for i, row in enumerate(results, 1):
        status = "WIN" if row['profit_loss'] > 0 else "LOSS" if row['profit_loss'] < 0 else "EVEN"
        print(f"{row['date']} | ${row['profit_loss']:+.2f} | {status}")
    print("="*50)

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
breakeven_days = total_days - winning_days - losing_days
win_rate = (winning_days / total_days * 100) if total_days > 0 else 0
avg_profit = total_profit / total_days if total_days > 0 else 0
best_day = max(daily_pnl) if daily_pnl else 0
worst_day = min(daily_pnl) if daily_pnl else 0
ending_capital = starting_capital + total_profit
percentage_return = (total_profit / starting_capital * 100) if starting_capital > 0 else 0

# Export to CSV
csv_filename = f"spy_iron_butterfly_open_plus_{center_offset}_7year_results.csv"
with open(csv_filename, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['date', 'open', 'close', 'center_strike', 'distance', 'profit_loss', 'capital'])
    for row in results:
        writer.writerow([row['date'], row['open'], row['close'], row['center_strike'], row['distance'], row['profit_loss'], row['capital']])

# Print summary statistics
print("\n" + "="*60)
print("IRON BUTTERFLY BACKTEST RESULTS (7 YEARS)")
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