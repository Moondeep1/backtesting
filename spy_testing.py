import requests
import sqlite3
from datetime import datetime
import argparse
import json

class SPYBacktestTool:
    def __init__(self, api_key, capital=50000, target_gain=2.0, start_date="2024-06-01", end_date="2026-06-01", db_name="backtest_cache.db"):
        self.api_key = api_key
        self.capital = capital
        self.target_gain = target_gain
        self.start_date = start_date
        self.end_date = end_date
        self.db_name = db_name
        self.conn = None
        
    def setup_database(self):
        """Initialize database."""
        self.conn = sqlite3.connect(self.db_name)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS spy_daily_prices (
        date TEXT PRIMARY KEY,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL
        )
        """)
        self.conn.commit()
    
    def fetch_data(self):
        """Fetch SPY data from Polygon.io API."""
        print("Downloading SPY data...")
        url = f"https://api.polygon.io/v2/aggs/ticker/SPY/range/1/day/{self.start_date}/{self.end_date}"
        response = requests.get(url, params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": self.api_key})
        
        print(f"HTTP Status: {response.status_code}")
        
        data = response.json()
        rows = data.get("results", [])
        print(f"Rows returned: {len(rows)}")
        
        for row in rows:
            date = datetime.fromtimestamp(row["t"] / 1000).date()
            self.conn.execute(
                "INSERT OR REPLACE INTO spy_daily_prices VALUES (?, ?, ?, ?, ?, ?)",
                (date.isoformat(), row["o"], row["h"], row["l"], row["c"], row["v"])
            )
        self.conn.commit()
    
    def run_backtest(self):
        """Run the backtesting simulation."""
        cursor = self.conn.execute("SELECT date, open, high FROM spy_daily_prices ORDER BY date")
        rows = cursor.fetchall()
        
        # Convert dates to datetime objects
        rows = [(datetime.fromisoformat(date), open_price, high_price) for date, open_price, high_price in rows]
        
        holding = False
        buy_price = 0
        buy_date = None
        shares = 0
        total_profit = 0
        completed_trades = 0
        trade_profits = []
        holding_days = []
        trades = []
        no_trade_days = 0
        
        for date, open_price, high_price in rows:
            if not holding:
                shares = int(self.capital / open_price)
                buy_price = open_price
                buy_date = date
                cost = shares * buy_price
                holding = True
                trades.append({
                    'buy_date': date,
                    'buy_price': buy_price,
                    'shares': shares,
                    'cost': cost
                })
            
            if holding:
                sell_price = buy_price + self.target_gain
                if high_price >= sell_price:
                    revenue = shares * sell_price
                    profit = revenue - (shares * buy_price)
                    total_profit += profit
                    trade_profits.append(profit)
                    
                    days_held = (date - buy_date).days + 1
                    holding_days.append(days_held)
                    completed_trades += 1
                    
                    trades[-1]['sell_date'] = date
                    trades[-1]['sell_price'] = sell_price
                    trades[-1]['revenue'] = revenue
                    trades[-1]['profit'] = profit
                    trades[-1]['days_held'] = days_held
                    
                    holding = False
                else:
                    no_trade_days += 1
        
        return {
            'completed_trades': completed_trades,
            'total_profit': total_profit,
            'avg_profit': total_profit / completed_trades if completed_trades > 0 else 0,
            'avg_holding_days': sum(holding_days) / len(holding_days) if holding_days else 0,
            'winning_trades': len([p for p in trade_profits if p > 0]),
            'losing_trades': len([p for p in trade_profits if p <= 0]),
            'win_rate': (len([p for p in trade_profits if p > 0]) / completed_trades * 100) if completed_trades > 0 else 0,
            'no_trade_days': no_trade_days,
            'trades': trades
        }
    
    def print_results(self, results):
        """Print backtesting results."""
        print("\n" + "="*60)
        print("SPY DAY TRADING BACKTEST RESULTS")
        print("="*60)
        print(f"Capital Per Trade: ${self.capital:,.2f}")
        print(f"Target Gain: ${self.target_gain:.2f}")
        print(f"Date Range: {self.start_date} to {self.end_date}")
        print("="*60)
        print(f"Completed Trades: {results['completed_trades']}")
        print(f"Total Profit: ${results['total_profit']:,.2f}")
        print(f"Average Profit Per Trade: ${results['avg_profit']:.2f}")
        print(f"Average Holding Period: {results['avg_holding_days']:.1f} days")
        print(f"Winning Trades: {results['winning_trades']}")
        print(f"Losing Trades: {results['losing_trades']}")
        print(f"Win Rate: {results['win_rate']:.2f}%")
        print(f"Days Holding Without Profit: {results['no_trade_days']}")
        print("="*60)
        
        print("\n--- FIRST 10 TRADES ---")
        for i, trade in enumerate(results['trades'][:10], 1):
            if 'sell_date' in trade:
                print(f"Trade {i}: BUY {trade['shares']} @ ${trade['buy_price']:.2f} ({trade['buy_date']}) → SELL @ ${trade['sell_price']:.2f} ({trade['sell_date']}) | Profit: ${trade['profit']:.2f} | Days: {trade['days_held']}")
            else:
                print(f"Trade {i}: BUY {trade['shares']} @ ${trade['buy_price']:.2f} ({trade['buy_date']}) | HOLDING")
    
    def export_results(self, results, filename="backtest_results.json"):
        """Export results to JSON."""
        export_data = {
            'capital': self.capital,
            'target_gain': self.target_gain,
            'date_range': f"{self.start_date} to {self.end_date}",
            'completed_trades': results['completed_trades'],
            'total_profit': results['total_profit'],
            'avg_profit': results['avg_profit'],
            'win_rate': results['win_rate'],
        }
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        print(f"\nResults exported to {filename}")
    
    def run(self, export=False):
        """Run full backtest workflow."""
        self.setup_database()
        self.fetch_data()
        results = self.run_backtest()
        self.print_results(results)
        if export:
            self.export_results(results)
        self.conn.close()
        return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPY Day Trading Backtest Tool")
    parser.add_argument("--api-key", required=True, help="Polygon.io API key")
    parser.add_argument("--capital", type=float, default=50000, help="Capital per trade (default: 50000)")
    parser.add_argument("--target-gain", type=float, default=2.0, help="Target gain in dollars (default: 2.0)")
    parser.add_argument("--start-date", default="2024-06-01", help="Start date YYYY-MM-DD (default: 2024-06-01)")
    parser.add_argument("--end-date", default="2026-06-01", help="End date YYYY-MM-DD (default: 2026-06-01)")
    parser.add_argument("--export", action="store_true", help="Export results to JSON")
    
    args = parser.parse_args()
    
    tool = SPYBacktestTool(
        api_key=args.api_key,
        capital=args.capital,
        target_gain=args.target_gain,
        start_date=args.start_date,
        end_date=args.end_date
    )
    tool.run(export=args.export)