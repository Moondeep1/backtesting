import sqlite3
import pandas as pd

DB_NAME = "backtest_cache.db"

def inspect():
    conn = sqlite3.connect(DB_NAME)

    try:
        trades = pd.read_sql("SELECT * FROM trades", conn)
    except:
        trades = pd.DataFrame()

    try:
        stock = pd.read_sql("SELECT * FROM stock_prices", conn)
    except:
        stock = pd.DataFrame()

    try:
        options = pd.read_sql("SELECT * FROM option_prices", conn)
    except:
        options = pd.DataFrame()

    print("\n==============================")
    print("TRADES TABLE")
    print("==============================")
    print("Rows:", len(trades))
    print(trades.head(10))

    print("\n==============================")
    print("STOCK PRICES TABLE")
    print("==============================")
    print("Rows:", len(stock))
    print(stock.head(10))

    print("\n==============================")
    print("OPTION PRICES TABLE")
    print("==============================")
    print("Rows:", len(options))
    print(options.head(10))

    conn.close()


if __name__ == "__main__":
    inspect()