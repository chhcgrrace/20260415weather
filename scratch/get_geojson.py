import requests
import json

urls = [
    "https://raw.githubusercontent.com/g0v/twgeojson/master/json/counties.json",
    "https://raw.githubusercontent.com/angel910086/taiwan-geojson/master/taiwan-counties.json"
]

for url in urls:
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"URL: {url}")
            print(f"Keys: {data.keys()}")
            if 'features' in data:
                props = data['features'][0]['properties']
                print(f"Props: {props}")
            break
    except Exception as e:
        print(f"Failed {url}: {e}")
