import requests
import sqlite3
from datetime import datetime

print("SPY DAY TRADING SIMULATION - $50K FIXED CAPITAL")

API_KEY = "kFOG0Gl6TUrhzWX1NKMekuNeKfXJ0KBL"
DB_NAME = "backtest_cache.db"
START_DATE = "2024-06-01"
END_DATE = "2026-06-01"
TARGET_GAIN = 2.0
CAPITAL = 50000

conn = sqlite3.connect(DB_NAME)

conn.execute("""
CREATE TABLE IF NOT EXISTS spy_daily_prices (
date TEXT PRIMARY KEY,
open REAL,
high REAL,
low REAL,
close REAL,
volume REAL
)
""")

conn.commit()

print("Downloading SPY data...")

url = f"https://api.polygon.io/v2/aggs/ticker/SPY/range/1/day/{START_DATE}/{END_DATE}"
response = requests.get(url, params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": API_KEY})

print("HTTP Status:", response.status_code)

data = response.json()
rows = data.get("results", [])

print("Rows returned:", len(rows))

for row in rows:
    date = datetime.fromtimestamp(row["t"] / 1000).date()
    conn.execute(
        "INSERT OR REPLACE INTO spy_daily_prices VALUES (?, ?, ?, ?, ?, ?)",
        (date.isoformat(), row["o"], row["h"], row["l"], row["c"], row["v"])
    )

conn.commit()

cursor = conn.execute("SELECT date, open, high FROM spy_daily_prices ORDER BY date")
rows = cursor.fetchall()

# Convert dates to datetime objects
rows = [(datetime.fromisoformat(date), open_price, high_price) for date, open_price, high_price in rows]

# Day trading simulation with fixed $50,000 capital
holding = False
buy_price = 0
buy_date = None
shares = 0
total_profit = 0
completed_trades = 0
trade_profits = []
holding_days = []
trades = []
no_trade_days = 0

for date, open_price, high_price in rows:
    if not holding:
        # Buy with exactly $50,000
        shares = int(CAPITAL / open_price)  # floor division
        buy_price = open_price
        buy_date = date
        cost = shares * buy_price
        holding = True
        trades.append({
            'buy_date': date,
            'buy_price': buy_price,
            'shares': shares,
            'cost': cost
        })
    
    if holding:
        # Check if we can sell at target
        sell_price = buy_price + TARGET_GAIN
        if high_price >= sell_price:
            # Sell at target price
            revenue = shares * sell_price
            profit = revenue - (shares * buy_price)
            total_profit += profit
            trade_profits.append(profit)
            
            days_held = (date - buy_date).days + 1
            holding_days.append(days_held)
            completed_trades += 1
            
            trades[-1]['sell_date'] = date
            trades[-1]['sell_price'] = sell_price
            trades[-1]['revenue'] = revenue
            trades[-1]['profit'] = profit
            trades[-1]['days_held'] = days_held
            
            holding = False
        else:
            # Stock held but did not reach target - count as no-trade day
            no_trade_days += 1

# Statistics
avg_profit = total_profit / completed_trades if completed_trades > 0 else 0
avg_holding = sum(holding_days) / len(holding_days) if holding_days else 0
winning_trades = len([p for p in trade_profits if p > 0])
losing_trades = len([p for p in trade_profits if p <= 0])

print("\n" + "="*60)
print("SPY DAY TRADING SIMULATION - FIXED $50,000 CAPITAL")
print("="*60)
print(f"Completed Trades: {completed_trades}")
print(f"Days Holding Without Profit (No Trade): {no_trade_days}")
print(f"Total Profit: ${total_profit:.2f}")
print(f"Average Profit Per Trade: ${avg_profit:.2f}")
print(f"Average Holding Period: {avg_holding:.1f} days")
print(f"Winning Trades: {winning_trades}")
print(f"Losing Trades: {losing_trades}")
win_rate = (winning_trades / completed_trades * 100) if completed_trades > 0 else 0
print(f"Win Rate: {win_rate:.2f}%")
print("="*60)

print("\n--- FIRST 10 TRADES ---")
for i, trade in enumerate(trades[:10], 1):
    if 'sell_date' in trade:
        print(f"Trade {i}: BUY {trade['shares']} @ ${trade['buy_price']:.2f} ({trade['buy_date']}) → SELL @ ${trade['sell_price']:.2f} ({trade['sell_date']}) | Profit: ${trade['profit']:.2f} | Days: {trade['days_held']}")
    else:
        print(f"Trade {i}: BUY {trade['shares']} @ ${trade['buy_price']:.2f} ({trade['buy_date']}) | STILL HOLDING")

print("\n--- LAST 10 TRADES ---")
for i, trade in enumerate(trades[-10:], completed_trades - 9):
    if 'sell_date' in trade:
        print(f"Trade {i}: BUY {trade['shares']} @ ${trade['buy_price']:.2f} ({trade['buy_date']}) → SELL @ ${trade['sell_price']:.2f} ({trade['sell_date']}) | Profit: ${trade['profit']:.2f} | Days: {trade['days_held']}")
    else:
        print(f"Trade {i}: BUY {trade['shares']} @ ${trade['buy_price']:.2f} ({trade['buy_date']}) | STILL HOLDING")

conn.close()
print("\nDONE")