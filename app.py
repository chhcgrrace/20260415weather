import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import datetime
import os
import base64
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
def get_data():
    if not os.path.exists('data.db'):
        return pd.DataFrame()
    
    conn = sqlite3.connect('data.db')
    df = pd.read_sql_query("SELECT * FROM TemperatureForecasts", conn)
    conn.close()
    
    # Convert dataDate to datetime
    df['dataDate'] = pd.to_datetime(df['dataDate'])
    return df

def refresh_data():
    with st.spinner("正在更新天氣資料..."):
        try:
            # 直接呼叫函式，不再使用 subprocess 以避免環境路徑問題
            fetch_and_store_weather()
            st.success("資料已更新！")
            st.rerun()
        except Exception as e:
            st.error(f"更新失敗: {e}")

# --- Sidebar ---
st.sidebar.image("https://www.cwa.gov.tw/V8/assets/img/logo_CWA.png", width=200)
st.sidebar.title("控制面板")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 同步最新資料"):
    refresh_data()

# --- Main App ---
st.markdown('<h1 class="title-text">臺灣氣象預報中心</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">即時氣溫預報監測系統 (CWA API 官方資料庫)</p>', unsafe_allow_html=True)

df = get_data()

if df.empty:
    st.warning("⚠️ 尚未偵測到天氣資料。請點擊側邊欄的「同步最新資料」以獲取資料。")
else:
    # Get available regions and times
    regions = sorted(df['regionName'].unique())
    
    # Map coordinates mapping
    region_coords = {
        "北部地區": [25.04, 121.51],
        "中部地區": [24.14, 120.67],
        "南部地區": [22.62, 120.30],
        "東北部地區": [24.75, 121.75],
        "東部地區": [23.97, 121.61],
        "東南部地區": [22.75, 121.14],
        "臺北市": [25.03, 121.56], # Optional supplement
    }

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
        st.markdown("### 🗺️ 臺灣地區分布")
        
        # Calibrated positions for the provided taiwan.png
        marker_positions = {
            "北部地區": {"top": "25%", "left": "68%"},
            "中部地區": {"top": "48%", "left": "55%"},
            "南部地區": {"top": "75%", "left": "50%"},
            "東北部地區": {"top": "28%", "left": "73%"},
            "東部地區": {"top": "52%", "left": "68%"},
            "東南部地區": {"top": "80%", "left": "62%"},
            "臺北市": {"top": "22%", "left": "70%"},
        }
        
        pos = marker_positions.get(selected_region, {"top": "50%", "left": "50%"})
        
        # Display the user's map image with CSS-positioned marker
        import base64
        def get_image_base64(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()

        try:
            # Using the taiwan.png provided by the user
            img_b64 = get_image_base64("taiwan.png")
            st.markdown(f"""
                <div style="position: relative; width: 100%; max-width: 500px; margin: 20px auto;">
                    <img src="data:image/png;base64,{img_b64}" style="width: 100%; border-radius: 5px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
                </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error("無法開啟資料夾中的 taiwan.png。請確認該檔案是否存在。")

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
