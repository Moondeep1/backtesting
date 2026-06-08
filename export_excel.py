import sqlite3
from openpyxl import Workbook

conn = sqlite3.connect("backtest_cache.db")
cursor = conn.cursor()

wb = Workbook()

def add_sheet(name, query):
    ws = wb.create_sheet(title=name)
    cursor.execute(query)
    cols = [desc[0] for desc in cursor.description]
    ws.append(cols)
    for row in cursor.fetchall():
        ws.append(row)

# remove default sheet
wb.remove(wb.active)

add_sheet("trades", "SELECT * FROM trades")
add_sheet("stock_prices", "SELECT * FROM stock_prices")
add_sheet("option_prices", "SELECT * FROM option_prices")

wb.save("backtest_data.xlsx")

conn.close()

print("✅ Excel file created: backtest_data.xlsx")
