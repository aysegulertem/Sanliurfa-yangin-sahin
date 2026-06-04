import streamlit as st
import pandas as pd
import numpy as np
import folium

from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

import warnings
import os
import asyncio
import edge_tts
import base64

from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# SAYFA AYARLARI
# ==============================================================================
st.set_page_config(
    page_title="AFAD Orman Yangını Komuta Merkezi",
    page_icon="🚨",
    layout="wide"
)

# ==============================================================================
# CSS TASARIM VE HAREKETLİ ROBOT ÇEKİRDEĞİ (UI GLOW)
# ==============================================================================
st.markdown("""
<style>
.sahin-card{
    background: white;
    color: black;
    padding: 20px;
    border-radius: 20px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}
.sahin-card p{
    color: black !important;
}
.sahin-card h3{
    color: #d50000 !important;
}

/* ŞAHİN Yapay Zeka Robot Animasyonu */
.sahin-robot-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #111827, #1f2937);
    padding: 25px;
    border-radius: 20px;
    border: 2px solid #3b82f6;
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.5);
    margin-bottom: 20px;
    text-align: center;
}
.sahin-core {
    width: 80px;
    height: 80px;
    background: radial-gradient(circle, #00f2fe 0%, #4facfe 100%);
    border-radius: 50%;
    box-shadow: 0 0 30px #00f2fe;
    animation: pulse 2s infinite alternate;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40px;
}
@keyframes pulse {
    0% { transform: scale(0.9); box-shadow: 0 0 15px #00f2fe; }
    100% { transform: scale(1.1); box-shadow: 0 0 40px #00f2fe; }
}
.sahin-status {
    color: #00f2fe;
    font-family: 'Courier New', Courier, monospace;
    font-weight: bold;
    margin-top: 10px;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# BULUT UYUMLU ŞAHİN ASİSTAN SES MOTORU
# ==============================================================================
def sahin_seslendir(metin):
    try:
        ses_yolu = os.path.join(BASE_DIR, "sahin_asistan.mp3")
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        communicator = edge_tts.Communicate(metin, "tr-TR-AhmetNeural", rate="+25%")
        loop.run_until_complete(communicator.save(ses_yolu))
        with open(ses_yolu, "rb") as f: 
            ses_bytes = f.read()
        b64_ses = base64.b64encode(ses_bytes).decode()
        st.markdown(f'<audio autoplay><source src="data:audio/mp3;base64,{b64_ses}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    except:
        pass

# ==============================================================================
# İLÇE VERİTABANI
# ==============================================================================
ILCELER = {
    "Karaköprü":{"lat":37.1950, "lon":38.8150, "itfaiye":"Karaköprü Merkez İtfaiye Amirliği", "orman_mud":"Şanlıurfa Orman İşletme Müdürlüğü"},
    "Haliliye":{"lat":37.1650, "lon":38.8300, "itfaiye":"Haliliye Acil Müdahale İstasyonu", "orman_mud":"Şanlıurfa Orman İşletme Müdürlüğü"},
    "Eyyübiye":{"lat":37.1400, "lon":38.8000, "itfaiye":"Eyyübiye Sanayi Bölgesi İtfaiyesi", "orman_mud":"Şanlıurfa Orman İşletme Müdürlüğü"},
    "Akçakale":{"lat":36.7111, "lon":38.9469, "itfaiye":"Akçakale Sınır İtfaiye Amirliği", "orman_mud":"Harran Orman Şefliği"},
    "Birecik":{"lat":37.0315, "lon":37.9782, "itfaiye":"Birecik Sahil İtfaiye Grubu", "orman_mud":"Birecik Ağaçlandırma Şefliği"},
    "Bozova":{"lat":37.3622, "lon":38.4839, "itfaiye":"Bozova Merkez Müdahale Ekibi", "orman_mud":"Baraj Havzası Orman Koruma Şefliği"},
    "Ceylanpınar":{"lat":36.8411, "lon":40.0428, "itfaiye":"Ceylanpınar TİGEM İtfaiye Merkezi", "orman_mud":"Ceylanpınar Orman Koruma Ekibi"},
    "Halfeti":{"lat":37.2475, "lon":37.8697, "itfaiye":"Halfeti İtfaiye Müfrezesi", "orman_mud":"Halfeti Bölge Orman Şefliği"},
    "Harran":{"lat":36.8617, "lon":39.0306, "itfaiye":"Harran İtfaiyesi", "orman_mud":"Harran Ovası Şefliği"},
    "Hilvan":{"lat":37.5856, "lon":38.9592, "itfaiye":"Hilvan Müdahale İstasyonu", "orman_mud":"Hilvan Orman Ekibi"},
    "Siverek":{"lat":37.7500, "lon":39.3167, "itfaiye":"Siverek Bölge İtfaiye Amirliği", "orman_mud":"Siverek Orman İşletme Şefliği"},
    "Suruç":{"lat":36.9764, "lon":38.4244, "itfaiye":"Suruç İtfaiye Grubu", "orman_mud":"Şanlıurfa Orman Koruma Müfrezesi"},
    "Viranşehir":{"lat":37.2353, "lon":39.7619, "itfaiye":"Viranşehir Organize Sanayi İtfaiyesi", "orman_mud":"Viranşehir Orman Koruma Şefliği"}
}

# ==============================================================================
# GÖRÜNTÜLEME MODU
# ==============================================================================
goruntuleme_modu = st.radio(
    "📡 İzleme Modu",
    ["📍 Manuel İlçe", "🔄 Otomatik Döngü"],
    horizontal=True
)

# ==============================================================================
# İLÇE SEÇİMİ
# ==============================================================================
if goruntuleme_modu == "📍 Manuel İlçe":
    ilce_adi = st.selectbox("📍 İlçe Seç", list(ILCELER.keys()))
else:
    st_autorefresh(interval=10000, key="otomatik_dongu")
    ilce_adi = list(ILCELER.keys())[int(datetime.now().timestamp()/10) % len(ILCELER)]

koordinat = ILCELER[ilce_adi]

# ==============================================================================
# TELEMETRİ VERİLERİ (Rastgele Simülasyon)
# ==============================================================================
np.random.seed(int(datetime.now().timestamp()))
sicaklik = round(np.random.uniform(34, 46), 1)
nem = round(np.random.uniform(5, 25), 1)
ruzgar = round(np.random.uniform(10, 45), 1)
egim = round(np.random.uniform(0, 60), 1)

# Yangın Risk Hesabı
risk = int((sicaklik * 1.8) + (ruzgar * 0.8) + (egim * 0.4) - (nem * 1.2))
risk = max(0, min(risk, 100))

yonler = ["⬆️ Kuzey", "⬇️ Güney", "➡️ Doğu", "⬅️ Batı", "↗️ Kuzeydoğu", "↖️ Kuzeybatı", "↘️ Güneydoğu", "↙️ Güneybatı"]
yayilma_yonu = np.random.choice(yonler)

# ==============================================================================
# ÜST BANNER
# ==============================================================================
if goruntuleme_modu == "📍 Manuel İlçe":
    durum_etiketi = "🎯 OPERATÖR SEÇİMİ"
else:
    durum_etiketi = "📡 OTOMATİK TARAMA"

if risk >= 80:
    ikon, seviye, banner_renk = "🚨", "KRİTİK", "linear-gradient(135deg, #D50000, #FF6D00)"
elif risk >= 50:
    ikon, seviye, banner_renk = "⚠️", "YÜKSEK", "linear-gradient(135deg, #FFD600, #FF8F00)"
else:
    ikon, seviye, banner_renk = "✅", "DÜŞÜK", "linear-gradient(135deg, #00C853, #64DD17)"

st.markdown(f"""
<div style="background:{banner_renk}; padding:25px; border-radius:20px; color:white; box-shadow:0 8px 25px rgba(0,0,0,0.25); margin-bottom:20px;">
    <h1>🚨 AFAD ORMAN YANGINI KOMUTA MERKEZİ</h1>
    <h4>{durum_etiketi}</h4>
    <h3>📍 Aktif Bölge: {ilce_adi}</h3>
    <h2>{ikon} Risk Seviyesi: %{risk}</h2>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# ANA EKRAN SÜTUNLARI
# ==============================================================================
col_left, col_right = st.columns([1, 1.5])

# --- SOL SÜTUN: 🤖 ŞAHİN YAPAY ZEKA ROBOTU VE TELEMETRİ ---
with col_left:
    # Canlı Gözüken Yapay Zeka Robotu Paneli
    st.markdown(f"""
    <div class="sahin-robot-container">
        <div class="sahin-core">🦅</div>
        <div style="color: white; font-weight: bold; margin-top: 10px; font-size: 18px;">ŞAHİN v2.5 AI CORE</div>
        <div class="sahin-status">● SİSTEM AKTİF - VERİ AKIŞI ANALİZ EDİLİYOR</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ŞAHİN'e Hızlı Rapor Okutma Butonu (Anında Ses Tetikler)
    if st.button("🎙️ ŞAHİN'e Sesli Raporu Sor", use_container_width=True):
        rapor = f"{ilce_adi} bölgesi telemetri verileri işlendi. Yangın riski yüzde {risk}. "
        if risk >= 80:
            rapor += "Kritik eşik aşıldı, lojistik birimler otomatik sevk ediliyor!"
        else:
            rapor += "Durum stabil, bölge otonom drone ile izleniyor."
        sahin_seslendir(rapor)
        st.caption(f"🤖 **ŞAHİN Konuşuyor:** {rapor}")

    st.markdown("### 📍 Bölgesel Telemetri")
    st.info(f"📍 Aktif Tarama Bölgesi: Şanlıurfa / {ilce_adi}")
    st.write(f"🌡️ Sıcaklık: **{sicaklik} °C**")
    st.write(f"💧 Nem: **%{nem}**")
    st.write(f"💨 Rüzgar: **{ruzgar} km/s**")
    st.write(f"⛰️ Eğim: **{egim}°**")
    st.write(f"🔥 Tahmini Yayılma: **{yayilma_yonu}**")
    st.caption(f"Enlem: {koordinat['lat']} | Boylam: {koordinat['lon']}")
    st.warning(f"🔥 Yangının {yayilma_yonu} yönünde ilerleme ihtimali yüksek.")

# --- SAĞ SÜTUN: HARİTA ---
with col_right:
    # Uydu Katmanı Entegrasyonu (Projeyi çok daha profesyonel gösterir)
    uydu_katmani = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    m = folium.Map(location=[koordinat["lat"], koordinat["lon"]], zoom_start=11, tiles=uydu_katmani, attr="Esri Satellite")

    yangin_lat = koordinat["lat"] + np.random.uniform(-0.02, 0.02)
    yangin_lon = koordinat["lon"] + np.random.uniform(-0.02, 0.02)
    folium.Marker([yangin_lat, yangin_lon], popup="🔥 Aktif Yangın Noktası", tooltip="Yangın Merkezi", icon=folium.Icon(color="red")).add_to(m)
    folium.Marker([koordinat["lat"], koordinat["lon"]], popup=ilce_adi, tooltip=ilce_adi).add_to(m)

    drone_lat, drone_lon = yangin_lat + 0.01, yangin_lon + 0.01
    folium.Marker([drone_lat, drone_lon], popup="🚁 ŞAHİN Drone", tooltip="Drone Görevde", icon=folium.Icon(color="blue")).add_to(m)

    itfaiye_lat, itfaiye_lon = koordinat["lat"] - 0.015, koordinat["lon"] - 0.015
    folium.Marker([itfaiye_lat, itfaiye_lon], popup=koordinat["itfaiye"], tooltip="🚒 İtfaiye", icon=folium.Icon(color="green")).add_to(m)

    orman_lat, orman_lon = koordinat["lat"] + 0.015, koordinat["lon"] - 0.015
    folium.Marker([orman_lat, orman_lon], popup=koordinat["orman_mud"], tooltip="🌲 Orman Ekibi", icon=folium.Icon(color="darkgreen")).add_to(m)

    folium.PolyLine([[itfaiye_lat, itfaiye_lon], [yangin_lat, yangin_lon]], color="red", weight=5, tooltip="Müdahale Rotası").add_to(m)
    folium.PolyLine([[drone_lat, drone_lon], [yangin_lat, yangin_lon]], color="blue", weight=3, dash_array="10").add_to(m)

    yon_koordinat = {
        "⬆️ Kuzey": (0.03, 0), "⬇️ Güney": (-0.03, 0), "➡️ Doğu": (0, 0.03), "⬅️ Batı": (0, -0.03),
        "↗️ Kuzeydoğu": (0.03, 0.03), "↖️ Kuzeybatı": (0.03, -0.03), "↘️ Güneydoğu": (-0.03, 0.03), "↙️ Güneybatı": (-0.03, -0.03)
    }
    delta_lat, delta_lon = yon_koordinat[yayilma_yonu]
    folium.PolyLine([[yangin_lat, yangin_lon], [yangin_lat + delta_lat, yangin_lon + delta_lon]], color="orange", weight=8, tooltip="Tahmini Yayılma Yönü").add_to(m)

    renk = "red" if risk > 75 else "orange" if risk > 50 else "green"
    for yaricap in [1000, 2000, 3000]:
        folium.Circle(location=[koordinat["lat"], koordinat["lon"]], radius=yaricap, color=renk, weight=2, fill=False).add_to(m)

    st_folium(m, width=900, height=520)

# ==============================================================================
# SEKMELER
# ==============================================================================
st.write("---")
sekme1, sekme2, sekme3 = st.tabs(["🚒 Operasyon", "📈 Risk Analizi", "📋 Kayıtlar"])

# --- SEKME 1: OPERASYON ---
with sekme1:
    st.subheader("🚒 Acil Müdahale Merkezi")
    st.info(f"{ilce_adi} bölgesinde risk seviyesi %{risk}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚨 AFAD Çağır", use_container_width=True):
            st.success("AFAD ekipleri olay yerine yönlendirildi.")
    with col2:
        if st.button("🚒 İtfaiye Gönder", use_container_width=True):
            st.success(f"{koordinat['itfaiye']} görevlendirildi.")
    with col3:
        if st.button("🚁 Drone Kaldır", use_container_width=True):
            st.success("ŞAHİN Drone göreve başladı.")

    st.write("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Yangın Riski", f"%{risk}")
    c2.metric("Aktif İlçe", ilce_adi)
    c3.metric("Yayılma Yönü", yayilma_yonu)

# --- SEKME 2: RİSK ANALİZİ (Yapay Zeka Ağırlık Grafiği Eklendi) ---
with sekme2:
    st.subheader(f"📈 {ilce_adi} Risk Analizi")
    saatler = pd.date_range(end=datetime.now(), periods=24, freq="h")
    risk_grafik = pd.DataFrame({
        "Saat": saatler,
        "Risk": np.random.randint(max(10, risk - 30), min(100, risk + 20), size=24)
    })
    st.line_chart(risk_grafik.set_index("Saat"))
    
    st.write("---")
    st.subheader("🧠 ŞAHİN YZ Karar Faktörleri Analizi")
    faktorler = pd.DataFrame({
        "Sensör / Parametre": ["Sıcaklık Kontrolü", "Rüzgar Şiddeti", "Arazi Eğimi", "Atmosferik Nem (Ters Etki)"],
        "Ağırlık Skoru": [sicaklik * 1.8, ruzgar * 0.8, egim * 0.4, nem * 1.2]
    })
    st.bar_chart(faktorler.set_index("Sensör / Parametre"), color="#4facfe")

# --- SEKME 3: KAYITLAR ---
with sekme3:
    st.subheader("📋 Sistem Günlük Kayıtları")
    kayitlar = pd.DataFrame({
        "Tarih/Saat": [(datetime.now() - timedelta(minutes=i * 15)).strftime("%d.%m.%Y %H:%M") for i in range(10)],
        "İlçe": [ilce_adi] * 10,
        "Risk": [f"%{np.random.randint(20, 100)}" for _ in range(10)],
        "Durum": ["AKTİF", "AKTİF", "İNCELENDİ", "ARŞİVLENDİ", "ARŞİVLENDİ", "ARŞİVLENDİ", "ARŞİVLENDİ", "ARŞİVLENDİ", "ARŞİVLENDİ", "ARŞİVLENDİ"]
    })
    st.dataframe(kayitlar, use_container_width=True)
