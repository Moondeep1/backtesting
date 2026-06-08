import requests
import pandas as pd
from datetime import datetime, timedelta

API_KEY = "kFOG0Gl6TUrhzWX1NKMekuNeKfXJ0KBL"

SYMBOL = "PLTR"

# Last 1 year from today-ish; adjust as needed
START_DATE = "2025-06-01"
END_DATE = "2026-06-01"

DTE_TARGET = 30
OTM_PERCENT = 0.10  # 10% below stock price, not true delta


def get_json(url, params):
    params["apiKey"] = API_KEY
    response = requests.get(url, params=params)
    data = response.json()

    if "error" in data:
        raise Exception(data["error"])

    return data


def get_stock_prices(symbol, start, end):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start}/{end}"

    data = get_json(url, {
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000
    })

    df = pd.DataFrame(data.get("results", []))

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["t"], unit="ms").dt.date
    return df[["date", "o", "c", "h", "l", "v"]]


def get_put_contracts(symbol):
    url = "https://api.polygon.io/v3/reference/options/contracts"

    all_results = []
    params = {
        "underlying_ticker": symbol,
        "contract_type": "put",
        "expired": "true",
        "limit": 1000
    }

    while True:
        data = get_json(url, params)
        all_results.extend(data.get("results", []))

        next_url = data.get("next_url")
        if not next_url:
            break

        url = next_url
        params = {}

    return all_results


def get_option_prices(option_ticker, start, end):
    url = f"https://api.polygon.io/v2/aggs/ticker/{option_ticker}/range/1/day/{start}/{end}"

    data = get_json(url, {
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000
    })

    df = pd.DataFrame(data.get("results", []))

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["t"], unit="ms").dt.date
    return df[["date", "o", "c", "h", "l", "v"]]


def get_next_trading_day_price(stock_df, target_date):
    rows = stock_df[stock_df["date"] >= target_date]

    if rows.empty:
        return None

    row = rows.iloc[0]
    return {
        "date": row["date"],
        "open": row["o"],
        "close": row["c"]
    }


def pick_contract(contracts, trade_date, stock_price):
    target_expiration = trade_date + timedelta(days=DTE_TARGET)
    target_strike = stock_price * (1 - OTM_PERCENT)

    candidates = []

    for c in contracts:
        exp = datetime.strptime(c["expiration_date"], "%Y-%m-%d").date()
        strike = c["strike_price"]

        if exp <= trade_date:
            continue

        if strike >= stock_price:
            continue

        dte_distance = abs((exp - target_expiration).days)
        strike_distance = abs(strike - target_strike)

        candidates.append({
            "contract": c,
            "dte_distance": dte_distance,
            "strike_distance": strike_distance
        })

    if not candidates:
        return None

    candidates = sorted(
        candidates,
        key=lambda x: (x["dte_distance"], x["strike_distance"])
    )

    return candidates[0]["contract"]


def run_backtest():
    print("Downloading stock prices...")
    stock_df = get_stock_prices(SYMBOL, START_DATE, END_DATE)

    if stock_df.empty:
        print("No stock data found.")
        return

    print("Downloading option contracts...")
    contracts = get_put_contracts(SYMBOL)
    print("Total contracts found:", len(contracts))

    trades = []

    for _, stock_row in stock_df.iterrows():
        trade_date = stock_row["date"]

        # Every Monday
        if trade_date.weekday() != 0:
            continue

        stock_entry_price = stock_row["o"]

        contract = pick_contract(contracts, trade_date, stock_entry_price)

        if contract is None:
            print("No contract found for", trade_date)
            continue

        option_ticker = contract["ticker"]
        strike = contract["strike_price"]
        expiration_date = datetime.strptime(
            contract["expiration_date"],
            "%Y-%m-%d"
        ).date()

        trade_date_str = trade_date.strftime("%Y-%m-%d")
        expiration_str = expiration_date.strftime("%Y-%m-%d")

        option_df = get_option_prices(option_ticker, trade_date_str, expiration_str)

        if option_df.empty:
            print("No option price data for", option_ticker)
            continue

        # Premium received when selling put
        entry_option_price = option_df.iloc[0]["o"]
        premium_received = entry_option_price * 100

        # Stock price near expiration
        expiration_stock = get_next_trading_day_price(stock_df, expiration_date)

        if expiration_stock is None:
            print("No stock expiration price for", expiration_date)
            continue

        stock_expiration_price = expiration_stock["close"]
        stock_expiration_date = expiration_stock["date"]

        # If stock closes above strike, put expires worthless
        expired_worthless = stock_expiration_price >= strike

        if expired_worthless:
            assigned = False
            profit = premium_received
            expiration_value = 0
        else:
            assigned = True
            # intrinsic value at expiration
            expiration_value = (strike - stock_expiration_price) * 100
            profit = premium_received - expiration_value

        trades.append({
            "entry_date": trade_date,
            "stock_price_when_sold": round(stock_entry_price, 2),
            "option_ticker": option_ticker,
            "expiration_date": expiration_date,
            "stock_price_at_expiration_date": stock_expiration_date,
            "stock_price_at_expiration": round(stock_expiration_price, 2),
            "strike": strike,
            "entry_option_price": round(entry_option_price, 2),
            "premium_received": round(premium_received, 2),
            "expired_worthless": expired_worthless,
            "assigned": assigned,
            "expiration_value": round(expiration_value, 2),
            "profit": round(profit, 2)
        })

    result_df = pd.DataFrame(trades)

    if result_df.empty:
        print("No trades generated.")
        return

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 250)

    print("\n--- Full Trade List ---")
    print(result_df)

    print("\n--- Summary ---")
    print("Total trades:", len(result_df))
    print("Expired worthless:", int(result_df["expired_worthless"].sum()))
    print("Assigned:", int(result_df["assigned"].sum()))
    print("Total premium received:", round(result_df["premium_received"].sum(), 2))
    print("Total profit/loss:", round(result_df["profit"].sum(), 2))
    print("Average profit per trade:", round(result_df["profit"].mean(), 2))
    print("Win rate:", round((result_df["profit"] > 0).mean() * 100, 2), "%")

    result_df.to_csv("pltr_put_backtest_results.csv", index=False)
    print("\nSaved file: pltr_put_backtest_results.csv")


run_backtest()