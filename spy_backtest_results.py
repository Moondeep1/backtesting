import requests
import pandas as pd

API_KEY = "kFOG0Gl6TUrhzWX1NKMekuNeKfXJ0KBL"

url = "https://api.polygon.io/v2/aggs/ticker/SPY/range/1/day/2025-06-01/2026-06-01"

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

rows = []

for r in data.get("results", []):
    rows.append({
        "date": pd.to_datetime(r["t"], unit="ms").date(),
        "open": r["o"],
        "high": r["h"],
        "low": r["l"],
        "close": r["c"],
        "volume": r["v"]
    })

df = pd.DataFrame(rows)

print(df.head(20))
print(f"\nTrading Days: {len(df)}")

df.to_csv("spy_daily_1year.csv", index=False)

print("Saved: spy_daily_1year.csv")
