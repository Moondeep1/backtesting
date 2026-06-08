import requests
import sqlite3
from datetime import datetime

print("SPY TEST V2 RUNNING")

API_KEY = "kFOG0Gl6TUrhzWX1NKMekuNeKfXJ0KBL"
DB_NAME = "backtest_cache.db"

START_DATE = "2024-06-01"
END_DATE = "2026-06-01"

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

print("STATUS:", response.status_code)

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

conn.close()

print("DONE")
