import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import datetime
import os
from fetch_data import fetch_and_store_weather

# --- Page Configuration ---
st.set_page_config(
    page_title="臺灣一週氣溫預報 Dashbaord",
    page_icon="⛅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stApp {
        background: radial-gradient(circle at top right, #1a1c23, #0e1117);
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
    }
    .title-text {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        margin-bottom: 0px;
    }
    .subtitle-text {
        color: #888;
        font-size: 1.1rem;
        margin-bottom: 30px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Database Integration ---
def get_db_path():
    return os.path.join(os.path.dirname(__file__), 'data.db')

def get_data():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return pd.DataFrame()
    
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM TemperatureForecasts", conn)
        conn.close()
        
        if df.empty:
            return df
            
        # Convert dataDate to datetime
        df['dataDate'] = pd.to_datetime(df['dataDate'])
        return df
    except Exception as e:
        print(f"Database error: {e}")
        return pd.DataFrame()


# --- Sidebar ---
st.sidebar.image("https://www.cwa.gov.tw/V8/assets/img/logo_CWA.png", width=200)
st.sidebar.title("天氣預報資訊")
st.sidebar.markdown("---")

# --- Main App ---
st.markdown('<h1 class="title-text">臺灣氣象預報中心</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">即時氣溫預報監測系統 (CWA API 官方資料庫)</p>', unsafe_allow_html=True)

# --- Data Loading ---
df = get_data()

# 如果資料庫是空的
if df.empty:
    st.warning("⚠️ 尚未偵測到天氣資料庫。請確認倉庫中包含最新的 `data.db` 檔案。")
    st.stop()
else:
    # Get available regions and times
    regions = sorted(df['regionName'].unique())
    

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        selected_region = st.selectbox("📍 選擇顯示地區", regions)
        
        region_df = df[df['regionName'] == selected_region].sort_values('dataDate')
        
        # Time selector for map highlight / card display
        times = region_df['dataDate'].dt.strftime('%m/%d %H:%M').tolist()
        selected_time_str = st.selectbox("⏰ 選擇預報時間", times)
        selected_time = pd.to_datetime(region_df.iloc[times.index(selected_time_str)]['dataDate'])
        
        current_data = region_df[region_df['dataDate'] == selected_time].iloc[0]
        
        st.markdown(f"### {selected_region} - {selected_time_str}")
        m1, m2 = st.columns(2)
        m1.metric("最低氣溫", f"{current_data['mint']}°C", delta_color="inverse")
        m2.metric("最高氣溫", f"{current_data['maxt']}°C")
        st.markdown(f"**天氣現象**: {current_data['weather']}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Map Visualization (Custom Image Version)
        # --- Dynamic Map Visualization ---
        st.markdown("### 🗺️ 臺灣氣溫分佈地圖")
        
        # Define coordinates for all major counties in Taiwan
        city_coords = {
            "基隆市": [25.13, 121.74], "臺北市": [25.04, 121.57], "新北市": [24.91, 121.55],
            "桃園市": [24.94, 121.22], "新竹市": [24.81, 120.97], "新竹縣": [24.70, 121.16],
            "苗栗縣": [24.56, 120.94], "臺中市": [24.23, 120.84], "彰化縣": [24.03, 120.52],
            "南投縣": [23.83, 120.98], "雲林縣": [23.71, 120.43], "嘉義市": [23.47, 120.45],
            "嘉義縣": [23.45, 120.58], "臺南市": [23.15, 120.25], "高雄市": [22.84, 120.52],
            "屏東縣": [22.42, 120.65], "宜蘭縣": [24.60, 121.60], "花蓮縣": [23.76, 121.36],
            "臺東縣": [22.89, 120.98], "澎湖縣": [23.57, 119.61], "金門縣": [24.45, 118.38],
            "連江縣": [26.16, 119.95]
        }

        # Prepare map data for the selected time across ALL regions
        map_data = []
        all_regions_at_time = df[df['dataDate'] == selected_time]
        
        for _, row in all_regions_at_time.iterrows():
            r_name = row['regionName']
            if r_name in city_coords:
                map_data.append({
                    "City": r_name,
                    "Lat": city_coords[r_name][0],
                    "Lon": city_coords[r_name][1],
                    "Temp": row['maxt'],
                    "Weather": row['weather'],
                    "Size": 15 if r_name == selected_region else 8
                })
        
        if map_data:
            map_df = pd.DataFrame(map_data)
            
            # Create a sophisticated Mapbox scatter plot
            import plotly.express as px
            
            # Determine color scale based on temperature range (Autonomous judgment)
            avg_temp = map_df['Temp'].mean()
            if avg_temp > 28:
                color_scale = px.colors.sequential.YlOrRd # Hot
            elif avg_temp < 18:
                color_scale = px.colors.sequential.Blues # Cold
            else:
                color_scale = px.colors.sequential.Viridis # Moderate
                
            fig_map = px.scatter_mapbox(
                map_df, lat="Lat", lon="Lon", 
                color="Temp", size="Size",
                hover_name="City", 
                hover_data={"Temp": True, "Weather": True, "Lat": False, "Lon": False, "Size": False},
                color_continuous_scale=color_scale,
                size_max=15, zoom=6.5,
                center={"lat": 23.7, "lon": 121.0},
                mapbox_style="carto-darkmatter"
            )
            
            fig_map.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0},
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                coloraxis_colorbar=dict(
                    title="Temp °C",
                    thicknessmode="pixels", thickness=10,
                    lenmode="fraction", len=0.5,
                    yanchor="top", y=0.9,
                    ticks="outside",
                    tickfont=dict(color="white")
                )
            )
            
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("💡 目前選擇的時間點暫無地圖分佈資料。")

    with col2:
        # Temperature Trend Chart
        st.markdown("### 📈 本週氣溫趨勢圖")
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=region_df['dataDate'], y=region_df['maxt'],
            mode='lines+markers',
            name='最高氣溫',
            line=dict(color='#FF4B4B', width=4),
            marker=dict(size=10, symbol='circle'),
            hovertemplate='%{y}°C'
        ))

        fig.add_trace(go.Scatter(
            x=region_df['dataDate'], y=region_df['mint'],
            mode='lines+markers',
            name='最低氣溫',
            line=dict(color='#00C9FF', width=4),
            marker=dict(size=10, symbol='circle'),
            hovertemplate='%{y}°C',
            fill='tonexty',
            fillcolor='rgba(0, 201, 255, 0.1)'
        ))

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, tickfont=dict(color='white')),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)', tickfont=dict(color='white')),
            legend=dict(font=dict(color='white')),
            height=450,
            margin=dict(l=0, r=0, t=20, b=0),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Forecast Table
        st.markdown("### 📅 七天天氣明細")
        table_df = region_df[['dataDate', 'weather', 'mint', 'maxt']].copy()
        table_df['dataDate'] = table_df['dataDate'].dt.strftime('%Y-%m-%d %H:%M')
        table_df.columns = ['時間', '天氣現象', '最低溫 (°C)', '最高溫 (°C)']
        
        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True
        )

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #666; font-size: 0.8rem;">'
    '本應用程式使用的資料來源為「中央氣象署開放資料平臺」 (CWA Open Data). '
    '最後更新時間: ' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + 
    '</div>',
    unsafe_allow_html=True
)
