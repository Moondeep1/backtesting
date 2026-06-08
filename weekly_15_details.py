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

    contracts = pd.read_sql("""
        SELECT *
        FROM weekly_strategy_contracts
        WHERE otm_level = ?
        ORDER BY entry_date
    """, conn, params=(OTM_LEVEL,))

    stock = pd.read_sql("SELECT * FROM stock_prices", conn)

    stock["date"] = pd.to_datetime(stock["date"])
    contracts["entry_date"] = pd.to_datetime(contracts["entry_date"])
    contracts["expiration"] = pd.to_datetime(contracts["expiration"])

    rows = []

    for _, trade in contracts.iterrows():
        entry_date = trade["entry_date"]
        expiration = trade["expiration"]
        stock_entry = trade["stock_entry_price"]
        strike = trade["strike"]
        ticker = trade["ticker"]

        exp_stock_row = get_stock_on_or_before(stock, expiration)

        if exp_stock_row is None:
            continue

        stock_close_at_exp = exp_stock_row["close"]
        stock_close_date = exp_stock_row["date"]

        assigned = stock_close_at_exp < strike

        # TEMP approximate premium until we download real option premium
        premium = (stock_entry - strike) * 0.3 * 100

        if assigned:
            loss = (strike - stock_close_at_exp) * 100
            profit = premium - loss
        else:
            profit = premium

        rows.append({
            "entry_date": entry_date.date(),
            "expiration": expiration.date(),
            "stock_entry_price": round(stock_entry, 2),
            "strike": strike,
            "stock_close_date": stock_close_date.date(),
            "stock_close_at_expiration": round(stock_close_at_exp, 2),
            "assigned": assigned,
            "estimated_premium": round(premium, 2),
            "estimated_profit": round(profit, 2),
            "ticker": ticker
        })

    df = pd.DataFrame(rows)

    print("\n--- 15% OTM Weekly Trade Details ---")
    print(df.to_string(index=False))

    print("\n--- Summary ---")
    print("Trades:", len(df))
    print("Assigned:", int(df["assigned"].sum()))
    print("Expired Worthless:", len(df) - int(df["assigned"].sum()))
    print("Estimated Total Profit:", round(df["estimated_profit"].sum(), 2))

    df.to_csv("weekly_15_details.csv", index=False)
    print("\nSaved: weekly_15_details.csv")

    conn.close()


if __name__ == "__main__":
    run()