import requests
import sqlite3
import json
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

def fetch_and_store_weather():
    # 從環境變數讀取 API Key (具備更高的安全性)
    api_key = os.getenv("CWA_API_KEY")
    
    if not api_key:
        print("未找到 API Key。請確認 .env 檔案中是否已設定 CWA_API_KEY。")
        return
    # Try the OpenData API endpoint first
    url = f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-C0032-003?Authorization={api_key}&format=JSON"
    
    data = None
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        print("Fetched data from API.")
    except Exception as e:
        print(f"API fetch failed ({e}), attempting to read local file...")
        try:
            with open('../F-C0032-003.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            print("Loaded data from local file.")
        except Exception as le:
            print(f"Local file read failed: {le}")
            return

    # Parsing the "cwaopendata" structure
    if 'cwaopendata' in data:
        locations = data['cwaopendata']['Dataset']['Locations']['Location']
    elif 'records' in data: # Fallback for API V1 records format
        # If it's V1 records format, the structure is records -> locations or records -> location
        if 'locations' in data['records']:
            locations = data['records']['locations'][0]['location']
        else:
            locations = data['records']['location']
    else:
        print("Unknown data structure")
        return

    # Connect to SQLite
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS TemperatureForecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regionName TEXT,
            dataDate TEXT,
            mint INTEGER,
            maxt INTEGER,
            weather TEXT,
            UNIQUE(regionName, dataDate)
        )
    ''')
    
    # SQLite fix for AUTOINCREMENT (it's implicit for INTEGER PRIMARY KEY, but this is fine)
    # The error in previous run was actually 404, not SQL.

    for loc in locations:
        region_name = loc.get('LocationName') or loc.get('locationName')
        elements = loc.get('WeatherElement') or loc.get('weatherElement')
        
        weather_data = {} # key: startTime, value: {weather, maxt, mint}
        
        for elem in elements:
            elem_name = elem.get('ElementName') or elem.get('elementName')
            for t in elem['Time'] if 'Time' in elem else elem['time']:
                start_time = t.get('StartTime') or t.get('startTime')
                if start_time not in weather_data:
                    weather_data[start_time] = {'weather': 'N/A', 'maxt': 0, 'mint': 0}
                
                # Handle multiple ways element value can be structured
                e_val = t.get('ElementValue') or t.get('elementValue')
                
                if isinstance(e_val, dict):
                    if elem_name in ['天氣現象', 'Weather']:
                        weather_data[start_time]['weather'] = e_val.get('Weather', e_val.get('value', 'N/A'))
                    elif elem_name in ['最高溫度', 'MaxTemperature', 'MaxT']:
                        weather_data[start_time]['maxt'] = int(e_val.get('MaxTemperature', e_val.get('value', 0)))
                    elif elem_name in ['最低溫度', 'MinTemperature', 'MinT']:
                        weather_data[start_time]['mint'] = int(e_val.get('MinTemperature', e_val.get('value', 0)))
                elif isinstance(e_val, list):
                    val_str = e_val[0].get('value')
                    if elem_name in ['天氣現象', 'Weather']:
                        weather_data[start_time]['weather'] = val_str
                    elif elem_name in ['最高溫度', 'MaxTemperature']:
                        weather_data[start_time]['maxt'] = int(float(val_str))
                    elif elem_name in ['最低溫度', 'MinTemperature']:
                        weather_data[start_time]['mint'] = int(float(val_str))

        for start_time, vals in weather_data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO TemperatureForecasts (regionName, dataDate, mint, maxt, weather)
                VALUES (?, ?, ?, ?, ?)
            ''', (region_name, start_time, vals['mint'], vals['maxt'], vals['weather']))

    conn.commit()
    conn.close()
    print("Database updated.")

if __name__ == "__main__":
    fetch_and_store_weather()
