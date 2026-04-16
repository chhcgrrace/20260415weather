import sqlite3
import pandas as pd
import os
import sys

# Set output encoding to UTF-8
if sys.platform == 'win32':
    import _locale
    _locale._getdefaultlocale = (lambda *args: ['zh_TW', 'utf8'])

db_path = r"c:\Users\黃喻琦\Downloads\weater\data.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT DISTINCT regionName FROM TemperatureForecasts", conn)
    regions = df['regionName'].tolist()
    print("--- REGIONS START ---")
    for r in regions:
        print(r)
    print("--- REGIONS END ---")
    conn.close()
else:
    print("Database not found")
