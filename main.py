import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# Sayfa yapılandırması
st.set_page_config(page_title="ŞAHİN | İl İzleme Merkezi", layout="wide")

# Tüm ilçelerin eksiksiz veritabanı
ILCELER = {
    "Karaköprü": {"lat": 37.1950, "lon": 38.8150}, "Haliliye": {"lat": 37.1650, "lon": 38.8300},
    "Eyyübiye": {"lat": 37.1400, "lon": 38.8000}, "Akçakale": {"lat": 36.7111, "lon": 38.9469},
    "Birecik": {"lat": 37.0315, "lon": 37.9782}, "Bozova": {"lat": 37.3622, "lon": 38.4839},
    "Ceylanpınar": {"lat": 36.8411, "lon": 40.0428}, "Halfeti": {"lat": 37.2475, "lon": 37.8697},
    "Harran": {"lat": 36.8617, "lon": 39.0306}, "Hilvan": {"lat": 37.5856, "lon": 38.9592},
    "Siverek": {"lat": 37.7500, "lon": 39.3167}, "Suruç": {"lat": 36.9764, "lon": 38.4244},
    "Viranşehir": {"lat": 37.2353, "lon": 39.7619}
}

# CSS ile Şov Zamanı (Endüstriyel Temiz Görünüm)
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    /* Kartlar ve Yazı Renkleri */
    .metric-card { background: white; padding: 20px; border-radius: 10px; border-left: 5px solid #28A745; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #2D3436 !important; }
    .stMarkdown p { color: #2D3436 !important; font-weight: 500; }
    /* Gönüllü Butonları */
    .stButton>button { width: 100%; border-radius: 5px; background-color: #28A745; color: white !important; font-weight: bold; }
    .stButton>button:hover { background-color: #218838; }
    </style>
""", unsafe_allow_html=True)

# Sidebar
ilce_adi = st.sidebar.selectbox("📍 Bölge Seçimi", list(ILCELER.keys()))
st.sidebar.markdown("---")
st.sidebar.info("ŞAHİN v4.0 - Gerçek Zamanlı İzleme Aktif.")

# Ana Gövde
st.title(f"🦅 ŞAHİN: {ilce_adi} Bölgesi Çevre Analiz Paneli")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.subheader("Anlık Veri Akışı")
    st.metric("Sıcaklık", "36.2 °C", "+0.2")
    st.metric("Nem", "%12", "-1")
    st.markdown("</div>")

with col2:
    m = folium.Map(location=[ILCELER[ilce_adi]["lat"], ILCELER[ilce_adi]["lon"]], zoom_start=12)
    folium.Marker([ILCELER[ilce_adi]["lat"], ILCELER[ilce_adi]["lon"]], popup=ilce_adi).add_to(m)
    st_folium(m, width=700, height=300)

# Gönüllülük Kısmı (Göz alıcı hale getirildi)
st.markdown("---")
st.subheader("🤝 Toplumsal Dayanışma ve Gönüllülük")
g_col1, g_col2 = st.columns(2)

with g_col1:
    st.markdown("### 🌲 Yeşil Şanlıurfa")
    st.write("Fidan bağışlayarak şehrimizin nefes almasına yardımcı olun.")
    if st.button("Fidan Bağışı Yap"):
        st.success("Bağışınız alındı, teşekkürler!")

with g_col2:
    st.markdown("### 🛡️ Sahada Gönüllü Ol")
    st.write("Acil durumlarda ekiplerimize lojistik destek sağlayın.")
    if st.button("Gönüllü Kaydını Başlat"):
        st.success("Talebiniz kaydedildi, size döneceğiz!")
