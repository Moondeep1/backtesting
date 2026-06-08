import sqlite3
import requests
import time
import logging
from datetime import datetime, timedelta

API_KEY = "kFOG0Gl6TUrhzWX1NKMekuNeKfXJ0KBL"

DB_NAME = "backtest_cache.db"
SYMBOL = "PLTR"

START_DATE = "2025-06-01"
END_DATE = "2026-06-01"

OTM_PERCENT = 0.10
DTE_TARGET = 30
MAX_CALLS_PER_MINUTE = 5

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class RateLimitedPolygonClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.call_count = 0

    def get(self, url, params=None):
        if params is None:
            params = {}

        if self.call_count > 0 and self.call_count % MAX_CALLS_PER_MINUTE == 0:
            logging.info("Reached 5 API calls. Waiting 60 seconds...")
            time.sleep(60)

        params["apiKey"] = self.api_key
        self.call_count += 1

        logging.info(f"API call #{self.call_count}: {url}")
        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            raise Exception(data["error"])

        return data


class DatabaseManager:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_prices (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY(symbol, date)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS option_contracts (
            ticker TEXT PRIMARY KEY,
            underlying TEXT,
            expiration_date TEXT,
            strike REAL,
            contract_type TEXT,
            shares_per_contract INTEGER
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS option_prices (
            option_ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY(option_ticker, date)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS selected_trades (
            entry_date TEXT PRIMARY KEY,
            stock_entry_price REAL,
            option_ticker TEXT,
            expiration_date TEXT,
            strike REAL
        )
        """)

        self.conn.commit()
        logging.info("Database ready")

    def save_stock_row(self, symbol, row):
        date = datetime.fromtimestamp(row["t"] / 1000).date().isoformat()
        self.conn.execute("""
        INSERT OR REPLACE INTO stock_prices VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (symbol, date, row["o"], row["h"], row["l"], row["c"], row["v"]))
        self.conn.commit()

    def save_contract(self, contract):
        self.conn.execute("""
        INSERT OR REPLACE INTO option_contracts VALUES (?, ?, ?, ?, ?, ?)
        """, (
            contract["ticker"],
            contract["underlying_ticker"],
            contract["expiration_date"],
            contract["strike_price"],
            contract["contract_type"],
            contract.get("shares_per_contract", 100)
        ))
        self.conn.commit()

    def save_option_price(self, ticker, row):
        date = datetime.fromtimestamp(row["t"] / 1000).date().isoformat()
        self.conn.execute("""
        INSERT OR REPLACE INTO option_prices VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticker, date, row["o"], row["h"], row["l"], row["c"], row["v"]))
        self.conn.commit()

    def save_selected_trade(self, entry_date, stock_price, contract):
        self.conn.execute("""
        INSERT OR REPLACE INTO selected_trades VALUES (?, ?, ?, ?, ?)
        """, (
            entry_date,
            stock_price,
            contract["ticker"],
            contract["expiration_date"],
            contract["strike_price"]
        ))
        self.conn.commit()

    def close(self):
        self.conn.close()


class NeededDataDownloader:
    def __init__(self, db, client):
        self.db = db
        self.client = client

    def download_stock_prices(self):
        logging.info("Downloading PLTR stock prices...")

        url = f"https://api.polygon.io/v2/aggs/ticker/{SYMBOL}/range/1/day/{START_DATE}/{END_DATE}"

        data = self.client.get(url, {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000
        })

        rows = data.get("results", [])

        for row in rows:
            self.db.save_stock_row(SYMBOL, row)

        logging.info(f"Saved {len(rows)} stock rows")

        return [
            {
                "date": datetime.fromtimestamp(row["t"] / 1000).date(),
                "open": row["o"]
            }
            for row in rows
        ]

    def get_contracts_for_expiration(self, expiration_date):
        url = "https://api.polygon.io/v3/reference/options/contracts"

        data = self.client.get(url, {
            "underlying_ticker": SYMBOL,
            "contract_type": "put",
            "expiration_date": expiration_date,
            "limit": 1000
        })

        return data.get("results", [])

    def pick_contract(self, contracts, stock_price):
        target_strike = stock_price * (1 - OTM_PERCENT)

        candidates = [
            c for c in contracts
            if c["strike_price"] < stock_price
        ]

        if not candidates:
            return None

        return min(candidates, key=lambda c: abs(c["strike_price"] - target_strike))

    def download_option_prices(self, ticker, start_date, expiration_date):
        logging.info(f"Downloading option prices for {ticker}")

        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{expiration_date}"

        data = self.client.get(url, {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000
        })

        rows = data.get("results", [])

        for row in rows:
            self.db.save_option_price(ticker, row)

        logging.info(f"Saved {len(rows)} option price rows for {ticker}")

    def run(self):
        stock_rows = self.download_stock_prices()

        monday_rows = [r for r in stock_rows if r["date"].weekday() == 0]

        logging.info(f"Found {len(monday_rows)} Mondays")

        for index, row in enumerate(monday_rows, start=1):
            entry_date = row["date"]
            stock_price = row["open"]

            target_expiration = entry_date + timedelta(days=DTE_TARGET)

            # Try nearby Friday expirations around 30 DTE
            possible_expirations = []
            for offset in range(-7, 8):
                d = target_expiration + timedelta(days=offset)
                if d.weekday() == 4:
                    possible_expirations.append(d)

            selected_contract = None

            logging.info(f"Processing Monday {index}/{len(monday_rows)}: {entry_date}, stock={stock_price}")

            for exp in possible_expirations:
                exp_str = exp.isoformat()
                contracts = self.get_contracts_for_expiration(exp_str)

                if not contracts:
                    continue

                contract = self.pick_contract(contracts, stock_price)

                if contract:
                    selected_contract = contract
                    break

            if selected_contract is None:
                logging.warning(f"No contract found for {entry_date}")
                continue

            self.db.save_contract(selected_contract)
            self.db.save_selected_trade(entry_date.isoformat(), stock_price, selected_contract)

            self.download_option_prices(
                selected_contract["ticker"],
                entry_date.isoformat(),
                selected_contract["expiration_date"]
            )

            logging.info(
                f"Selected {selected_contract['ticker']} | "
                f"strike={selected_contract['strike_price']} | "
                f"exp={selected_contract['expiration_date']}"
            )

        logging.info("Finished downloading only needed strategy data")


if __name__ == "__main__":
    db = DatabaseManager(DB_NAME)
    client = RateLimitedPolygonClient(API_KEY)
    downloader = NeededDataDownloader(db, client)

    try:
        downloader.run()
    finally:
        db.close()