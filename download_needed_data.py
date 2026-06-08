import requests
import sqlite3
import pandas as pd
from datetime import datetime

API_KEY = "YOUR_API_KEY"
DB_NAME = "backtest_cache.db"

START_DATE = "2024-06-01"
END_DATE = "2026-06-01"

TARGET_GAIN = 2.0
SHARES = 100

class DB:
def **init**(self):
self.conn = sqlite3.connect(DB_NAME)

```
    self.conn.execute("""
    CREATE TABLE IF NOT EXISTS spy_daily_prices (
        date TEXT PRIMARY KEY,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL
    )
    """)

    self.conn.commit()

def save_day(self, date, open_price, high_price, low_price, close_price, volume):
    self.conn.execute(
        """
        INSERT OR REPLACE INTO spy_daily_prices
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (date, open_price, high_price, low_price, close_price, volume)
    )

def commit(self):
    self.conn.commit()

def load_data(self):
    return pd.read_sql(
        """
        SELECT *
        FROM spy_daily_prices
        ORDER BY date
        """,
        self.conn
    )
```

def download_data(db):
print("Downloading SPY data...")

```
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

response.raise_for_status()

data = response.json()
rows = data.get("results", [])

print(f"API rows returned: {len(rows)}")

for row in rows:
    date = datetime.fromtimestamp(row["t"] / 1000).date()

    db.save_day(
        date.isoformat(),
        row["o"],
        row["h"],
        row["l"],
        row["c"],
        row["v"]
    )

db.commit()

print(f"Saved {len(rows)} trading days to SQLite")
```

def run_backtest(db):
df = db.load_data()

```
df["target_price"] = df["open"] + TARGET_GAIN
df["hit_target"] = df["high"] >= df["target_price"]

total_days = len(df)
winning_days = int(df["hit_target"].sum())
losing_days = total_days - winning_days

success_rate = (winning_days / total_days) * 100

profit_per_win = TARGET_GAIN * SHARES
total_profit = winning_days * profit_per_win

df["profit"] = df["hit_target"].apply(
    lambda x: profit_per_win if x else 0
)

print("\n==============================")
print("SPY OPEN + $2 BACKTEST")
print("==============================")
print(f"Trading Days: {total_days}")
print(f"Winning Days: {winning_days}")
print(f"Losing Days: {losing_days}")
print(f"Success Rate: {success_rate:.2f}%")
print(f"Profit Per Winning Day: ${profit_per_win:.2f}")
print(f"Total Profit: ${total_profit:.2f}")

df.to_csv("spy_2year_backtest.csv", index=False)

print("\nSaved: spy_2year_backtest.csv")
```

def main():
db = DB()

```
download_data(db)

run_backtest(db)
```

if **name** == "**main**":
main()
