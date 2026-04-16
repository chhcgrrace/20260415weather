import requests
import sqlite3
import json
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

def fetch_and_store_weather():
    # 從環境變數讀取 API Key
    api_key = os.getenv("CWA_API_KEY")
    
    if not api_key:
        raise ValueError("未找到 API Key。請確認 .env 檔案中是否已設定 CWA_API_KEY，或在環境變數中設定。")

    # API 端點
    url = f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-C0032-003?Authorization={api_key}&format=JSON"
    
    data = None
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"API 抓取失敗: {e}")
        # 嘗試讀取本地備份 (選擇性)
        local_path = os.path.join(os.path.dirname(__file__), 'F-C0032-003.json')
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            raise RuntimeError(f"無法獲取天氣資料且無本地備份: {e}")

    # 解析資料結構
    locations = []
    if 'cwaopendata' in data:
        dataset = data['cwaopendata'].get('Dataset') or data['cwaopendata'].get('dataset')
        if dataset:
            loc_data = dataset.get('Locations') or dataset.get('locations')
            if loc_data:
                locations = loc_data.get('Location', []) or loc_data.get('location', [])
    elif 'records' in data:
        if 'locations' in data['records']:
            locations = data['records']['locations'][0].get('location', [])
        else:
            locations = data['records'].get('location', [])
    
    if not locations:
        raise RuntimeError("API 回傳資料格式不符或沒有地理位置資料。")

    # 連接資料庫 (使用絕對路徑以確保一致性)
    db_path = os.path.join(os.path.dirname(__file__), 'data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 建立表格
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
    
    inserted_count = 0
    for loc in locations:
        region_name = loc.get('LocationName') or loc.get('locationName')
        elements = loc.get('WeatherElement') or loc.get('weatherElement')
        if not elements:
            continue
            
        weather_data = {} # key: startTime, value: {weather, maxt, mint}
        
        for elem in elements:
            elem_name = (elem.get('ElementName') or elem.get('elementName') or "").strip()
            
            time_list = elem.get('Time') or elem.get('time') or []
            for t in time_list:
                start_time = t.get('StartTime') or t.get('startTime')
                if not start_time:
                    continue
                    
                if start_time not in weather_data:
                    weather_data[start_time] = {'weather': 'N/A', 'maxt': 20, 'mint': 20}
                
                e_val = t.get('ElementValue') or t.get('elementValue')
                
                # 處理不同的資料層級
                val = "N/A"
                if isinstance(e_val, dict):
                    val = e_val.get('Weather') or e_val.get('MaxTemperature') or e_val.get('MinTemperature') or e_val.get('value') or "N/A"
                elif isinstance(e_val, list) and len(e_val) > 0:
                    val = e_val[0].get('value') or "N/A"
                
                # 根據專案需求映射欄位
                if elem_name in ['天氣現象', 'Weather']:
                    weather_data[start_time]['weather'] = val
                elif elem_name in ['最高溫度', 'MaxTemperature', 'MaxT']:
                    try:
                        weather_data[start_time]['maxt'] = int(float(val))
                    except: pass
                elif elem_name in ['最低溫度', 'MinTemperature', 'MinT']:
                    try:
                        weather_data[start_time]['mint'] = int(float(val))
                    except: pass

        for start_time, vals in weather_data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO TemperatureForecasts (regionName, dataDate, mint, maxt, weather)
                VALUES (?, ?, ?, ?, ?)
            ''', (region_name, start_time, vals['mint'], vals['maxt'], vals['weather']))
            inserted_count += 1

    conn.commit()
    conn.close()
    print(f"資料庫更新完成，共更新 {inserted_count} 筆記錄。")
    return inserted_count

if __name__ == "__main__":
    try:
        count = fetch_and_store_weather()
        print(f"成功更新 {count} 筆資料。")
    except Exception as e:
        print(f"錯誤: {e}")

