import sqlite3
import pandas as pd
import os

db_path = r"c:\Users\黃喻琦\Downloads\weater\data.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT DISTINCT regionName FROM TemperatureForecasts", conn)
    print(df['regionName'].tolist())
    conn.close()
else:
    print("Database not found")
