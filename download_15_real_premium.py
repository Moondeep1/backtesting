import sqlite3
import requests
import time
import logging
from datetime import datetime

API_KEY = "kFOG0Gl6TUrhzWX1NKMekuNeKfXJ0KBL"
DB_NAME = "backtest_cache.db"
MAX_CALLS_PER_MINUTE = 5
OTM_LEVEL = 0.15

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class Client:
    def __init__(self):
        self.calls = 0

    def get(self, url, params=None):
        if params is None:
            params = {}

        if self.calls > 0 and self.calls % MAX_CALLS_PER_MINUTE == 0:
            logging.info("Waiting 60 seconds due to rate limit...")
            time.sleep(60)

        params["apiKey"] = API_KEY
        self.calls += 1
        logging.info(f"API call #{self.calls}")

        r = requests.get(url, params=params)
        data = r.json()

        if "error" in data:
            raise Exception(data["error"])

        return data


def create_table(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS weekly_real_premiums (
        entry_date TEXT,
        otm_level REAL,
        ticker TEXT,
        entry_option_price REAL,
        premium_received REAL,
        PRIMARY KEY(entry_date, otm_level)
    )
    """)
    conn.commit()


def save_premium(conn, entry_date, otm, ticker, entry_option_price):
    premium_received = entry_option_price * 100

    conn.execute("""
    INSERT OR REPLACE INTO weekly_real_premiums
    VALUES (?, ?, ?, ?, ?)
    """, (
        entry_date,
        otm,
        ticker,
        entry_option_price,
        premium_received
    ))

    conn.commit()


def run():
    conn = sqlite3.connect(DB_NAME)
    create_table(conn)

    client = Client()

    trades = conn.execute("""
        SELECT entry_date, otm_level, ticker, expiration
        FROM weekly_strategy_contracts
        WHERE otm_level = ?
        ORDER BY entry_date
    """, (OTM_LEVEL,)).fetchall()

    logging.info(f"Found {len(trades)} 15% OTM weekly trades")

    for i, (entry_date, otm, ticker, expiration) in enumerate(trades, start=1):
        logging.info(f"{i}/{len(trades)} Downloading premium for {ticker} on {entry_date}")

        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{entry_date}/{entry_date}"

        data = client.get(url, {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000
        })

        rows = data.get("results", [])

        if not rows:
            logging.warning(f"No premium found for {ticker} on {entry_date}")
            continue

        entry_option_price = rows[0]["o"]

        save_premium(conn, entry_date, otm, ticker, entry_option_price)

        logging.info(
            f"Saved premium: option_price={entry_option_price}, premium=${entry_option_price * 100:.2f}"
        )

    conn.close()
    logging.info("DONE downloading real premiums for 15%")


if __name__ == "__main__":
    run()