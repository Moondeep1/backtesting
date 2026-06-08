import sqlite3
import pandas as pd

DB_NAME = "backtest_cache.db"


def get_stock_on_or_before(stock_df, target_date):
    df = stock_df[stock_df["date"] <= target_date].sort_values("date")
    if df.empty:
        return None
    return df.iloc[-1]["close"]


def run():
    conn = sqlite3.connect(DB_NAME)

    contracts = pd.read_sql("SELECT * FROM weekly_strategy_contracts", conn)
    stock = pd.read_sql("SELECT * FROM stock_prices", conn)

    stock["date"] = pd.to_datetime(stock["date"])
    contracts["entry_date"] = pd.to_datetime(contracts["entry_date"])
    contracts["expiration"] = pd.to_datetime(contracts["expiration"])

    print("\n==============================")
    print("WEEKLY BACKTEST RESULTS")
    print("==============================")

    for otm in [0.10, 0.15, 0.20]:
        print(f"\n--- Testing {int(otm*100)}% OTM ---")

        df = contracts[contracts["otm_level"] == otm]

        total_profit = 0
        assigned = 0
        trades = 0

        for _, row in df.iterrows():
            strike = row["strike"]
            entry_price = row["stock_entry_price"]
            expiration = row["expiration"]

            stock_exp = get_stock_on_or_before(stock, expiration)

            if stock_exp is None:
                continue

            # approximate premium (simple model)
            premium = (entry_price - strike) * 0.3 * 100

            if stock_exp < strike:
                assigned += 1
                loss = (strike - stock_exp) * 100
                profit = premium - loss
            else:
                profit = premium

            total_profit += profit
            trades += 1

        if trades == 0:
            print("No trades")
            continue

        print(f"Trades: {trades}")
        print(f"Assigned: {assigned}")
        print(f"Expired Worthless: {trades - assigned}")
        print(f"Total Profit: {round(total_profit, 2)}")
        print(f"Average Profit: {round(total_profit/trades, 2)}")

    conn.close()


if __name__ == "__main__":
    run()