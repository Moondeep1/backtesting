import requests
import sqlite3
from datetime import datetime

print("SPY TEST V3 RUNNING")

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

response = requests.get(
url,
params={
"adjusted": "true",
"sort": "asc",
"limit": 50000,
"apiKey": API_KEY
}
)

print("HTTP Status:", response.status_code)

data = response.json()

rows = data.get("results", [])

print("Rows returned:", len(rows))

for row in rows:
date = datetime.fromtimestamp(row["t"] / 1000).date()

```
conn.execute(
    """
    INSERT OR REPLACE INTO spy_daily_prices
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    (
        date.isoformat(),
        row["o"],
        row["h"],
        row["l"],
        row["c"],
        row["v"]
    )
)
```

conn.commit()

count = conn.execute(
"SELECT COUNT(*) FROM spy_daily_prices"
).fetchone()[0]

print("Rows in DB:", count)

cursor = conn.execute(
"""
SELECT date, open, high
FROM spy_daily_prices
ORDER BY date
"""
)

rows = cursor.fetchall()

total_days = len(rows)
winning_days = 0

for date, open_price, high_price in rows:
if high_price >= open_price + TARGET_GAIN:
winning_days += 1

losing_days = total_days - winning_days

success_rate = 0

if total_days > 0:
success_rate = (winning_days / total_days) * 100

profit_per_win = TARGET_GAIN * SHARES
total_profit = winning_days * profit_per_win

print()
print("==============================")
print("SPY OPEN + $2 BACKTEST")
print("==============================")
print("Trading Days:", total_days)
print("Winning Days:", winning_days)
print("Losing Days:", losing_days)
print("Success Rate:", round(success_rate, 2), "%")
print("Profit Per Win: $", profit_per_win)
print("Total Profit: $", total_profit)

conn.close()

print()
print("DONE")
