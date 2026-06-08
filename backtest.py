import sqlite3
import pandas as pd

DB_NAME = "backtest_cache.db"

def run_backtest():
    print("Starting backtest...")

    conn = sqlite3.connect(DB_NAME)

    trades = pd.read_sql("SELECT * FROM trades", conn)
    stock = pd.read_sql("SELECT * FROM stock_prices", conn)
    options = pd.read_sql("SELECT * FROM option_prices", conn)

    print(f"Trades loaded: {len(trades)}")
    print(f"Stock rows loaded: {len(stock)}")
    print(f"Option rows loaded: {len(options)}")

    results = []
    assigned_count = 0

    for i, t in trades.iterrows():
        print("\n-----------------------------")
        print(f"Processing trade #{i+1}")

        ticker = t["ticker"]
        strike = t["strike"]
        expiration = t["expiration"]
        entry_date = t["entry_date"]

        print(f"Ticker: {ticker}")
        print(f"Strike: {strike}")
        print(f"Expiration: {expiration}")

        opt = options[options["ticker"] == ticker].sort_values("date")

        if opt.empty:
            print("❌ No option data found")
            continue

        entry_price = opt.iloc[0]["open"]
        premium = entry_price * 100

        print(f"Entry option price: {entry_price}")
        print(f"Premium received: {premium}")

        stock_exp = stock[stock["date"] == expiration]

        if stock_exp.empty:
            print("❌ No stock price found for expiration")
            continue

        stock_exp_price = stock_exp.iloc[0]["close"]

        print(f"Stock at expiration: {stock_exp_price}")

        if stock_exp_price < strike:
            print("➡️ Assigned")
            assigned = True
            assigned_count += 1

            loss = (strike - stock_exp_price) * 100
            profit = premium - loss
        else:
            print("➡️ Expired worthless")
            assigned = False
            profit = premium

        print(f"Profit: {profit}")

        results.append(profit)

    print("\n==============================")
    print(f"Processed trades: {len(results)}")

    if not results:
        print("❌ No results generated — something is wrong")
        return

    print("\n--- SUMMARY ---")
    print("Total Trades:", len(results))
    print("Assigned:", assigned_count)
    print("Expired Worthless:", len(results) - assigned_count)
    print("Total Profit:", round(sum(results), 2))
    print("Average Profit:", round(sum(results) / len(results), 2))

    conn.close()


if __name__ == "__main__":
    run_backtest()