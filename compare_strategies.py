import sqlite3
import pandas as pd

DB_NAME = "backtest_cache.db"

OTM_LEVELS = [0.10, 0.15, 0.20]


def run():
    conn = sqlite3.connect(DB_NAME)

    trades = pd.read_sql("SELECT * FROM trades", conn)
    stock = pd.read_sql("SELECT * FROM stock_prices", conn)
    options = pd.read_sql("SELECT * FROM option_prices", conn)

    for otm in OTM_LEVELS:
        print("\n==============================")
        print(f"Testing {int(otm*100)}% OTM Strategy")
        print("==============================")

        total_profit = 0
        assigned_count = 0
        total_trades = 0

        for _, t in trades.iterrows():
            entry_date = t["entry_date"]
            expiration = t["expiration"]
            stock_entry = t["stock_entry_price"]

            target_strike = stock_entry * (1 - otm)

            # Find closest strike from your existing contracts
            same_day_trades = trades[trades["entry_date"] == entry_date]

            if same_day_trades.empty:
                continue

            # pick closest strike to new OTM level
            selected = min(
                same_day_trades.to_dict("records"),
                key=lambda x: abs(x["strike"] - target_strike)
            )

            ticker = selected["ticker"]
            strike = selected["strike"]

            opt = options[options["ticker"] == ticker].sort_values("date")

            if opt.empty:
                continue

            entry_price = opt.iloc[0]["open"]
            premium = entry_price * 100

            stock_exp = stock[stock["date"] == expiration]

            if stock_exp.empty:
                continue

            stock_exp_price = stock_exp.iloc[0]["close"]

            if stock_exp_price < strike:
                assigned = True
                assigned_count += 1

                loss = (strike - stock_exp_price) * 100
                profit = premium - loss
            else:
                assigned = False
                profit = premium

            total_profit += profit
            total_trades += 1

        if total_trades == 0:
            print("No trades found")
            continue

        print(f"Total Trades: {total_trades}")
        print(f"Assigned: {assigned_count}")
        print(f"Expired Worthless: {total_trades - assigned_count}")
        print(f"Total Profit: {round(total_profit, 2)}")
        print(f"Average Profit: {round(total_profit / total_trades, 2)}")

    conn.close()


if __name__ == "__main__":
    run()