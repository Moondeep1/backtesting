import sqlite3
import pandas as pd

DB_NAME = "backtest_cache.db"
OTM_LEVEL = 0.15


def get_stock_on_or_before(stock_df, target_date):
    df = stock_df[stock_df["date"] <= target_date].sort_values("date")
    if df.empty:
        return None
    return df.iloc[-1]


def run():
    conn = sqlite3.connect(DB_NAME)

    trades = pd.read_sql("""
        SELECT *
        FROM weekly_strategy_contracts
        WHERE otm_level = ?
        ORDER BY entry_date
    """, conn, params=(OTM_LEVEL,))

    premiums = pd.read_sql("""
        SELECT *
        FROM weekly_real_premiums
        WHERE otm_level = ?
    """, conn, params=(OTM_LEVEL,))

    stock = pd.read_sql("SELECT * FROM stock_prices", conn)

    trades["entry_date"] = pd.to_datetime(trades["entry_date"])
    trades["expiration"] = pd.to_datetime(trades["expiration"])
    stock["date"] = pd.to_datetime(stock["date"])

    results = []

    for _, trade in trades.iterrows():
        entry_date_str = trade["entry_date"].date().isoformat()

        premium_row = premiums[premiums["entry_date"] == entry_date_str]
        if premium_row.empty:
            continue

        exp_stock = get_stock_on_or_before(stock, trade["expiration"])
        if exp_stock is None:
            continue

        premium_received = premium_row.iloc[0]["premium_received"]
        stock_close = exp_stock["close"]
        strike = trade["strike"]

        if stock_close < strike:
            assigned = True
            loss = (strike - stock_close) * 100
            profit = premium_received - loss
        else:
            assigned = False
            profit = premium_received

        results.append({
            "entry_date": entry_date_str,
            "expiration": trade["expiration"].date().isoformat(),
            "stock_entry": round(trade["stock_entry_price"], 2),
            "strike": strike,
            "stock_close_at_exp": round(stock_close, 2),
            "option_price": premium_row.iloc[0]["entry_option_price"],
            "premium_received": round(premium_received, 2),
            "assigned": assigned,
            "profit": round(profit, 2),
            "ticker": trade["ticker"]
        })

    df = pd.DataFrame(results)

    print(df.to_string(index=False))

    print("\n--- REAL 15% WEEKLY SUMMARY ---")
    print("Trades:", len(df))
    print("Assigned:", int(df["assigned"].sum()))
    print("Expired Worthless:", len(df) - int(df["assigned"].sum()))
    print("Total Premium/Profit:", round(df["profit"].sum(), 2))
    print("Average Profit:", round(df["profit"].mean(), 2))

    df.to_csv("weekly_15_real_results.csv", index=False)
    print("\nSaved: weekly_15_real_results.csv")

    conn.close()


if __name__ == "__main__":
    run()