import requests
import sqlite3
from datetime import datetime

print("SPY DAY TRADING SIMULATION V1")

API_KEY = "kFOG0Gl6TUrhzWX1NKMekuNeKfXJ0KBL"
DB_NAME = "backtest_cache.db"
START_DATE = "2024-06-01"
END_DATE = "2026-06-01"
TARGET_GAIN = 2.0
SHARES = 100

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

# Day trading simulation
holding = False
buy_price = 0
total_bought = 0
total_sold = 0
trades = []
cash = 0

for date, open_price, high_price in rows:
    if not holding:
        # Buy at open
        buy_price = open_price
        total_bought += SHARES * buy_price
        holding = True
        trades.append(f"{date}: BUY 100 @ ${buy_price:.2f} (Total Cost: ${SHARES * buy_price:.2f})")
    
    if holding:
        # Check if we can sell at target
        sell_price = buy_price + TARGET_GAIN
        if high_price >= sell_price:
            # Sell at target price
            total_sold += SHARES * sell_price
            cash += SHARES * TARGET_GAIN
            trades.append(f"{date}: SELL 100 @ ${sell_price:.2f} (Profit: ${SHARES * TARGET_GAIN:.2f})")
            holding = False

profit = total_sold - total_bought

print("\n" + "="*50)
print("SPY DAY TRADING SIMULATION")
print("="*50)
print(f"Total Shares Bought: {len([t for t in trades if 'BUY' in t])} trades")
print(f"Total Shares Sold: {len([t for t in trades if 'SELL' in t])} trades")
print(f"Total Amount Spent (Buys): ${total_bought:.2f}")
print(f"Total Amount Earned (Sells): ${total_sold:.2f}")
print(f"Total Profit: ${profit:.2f}")
print(f"Total Cash Gained: ${cash:.2f}")
print("="*50)

print("\n--- TRADE LOG (First 20 & Last 20) ---")
for trade in trades[:20]:
    print(trade)
if len(trades) > 40:
    print("...")
for trade in trades[-20:]:
    print(trade)

conn.close()
print("\nDONE")