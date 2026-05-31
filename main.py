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
from datetime import datetime

warnings.filterwarnings("ignore")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# 📱 TEMA VE SIRA DIŞI MOBİL ESTETİK AYARLARI (CSS DÖNÜŞÜMÜ)
# ==============================================================================
st.set_page_config(page_title="ŞAHİN Mobil Komuta", layout="wide", initial_sidebar_state="expanded")

# Sol menüde Tema Seçimi
st.sidebar.markdown("## 🎨 Arayüz Özelleştirme")
tema = st.sidebar.selectbox("Görünüm Modu Seçin", ["🌃 Siber Koyu (Gece)", "🌅 Canlı Açık (Gündüz)"])

if "Siber Koyu" in tema:
    bg_color = "#0B0F19"
    card_bg = "#161B26"
    text_color = "#E2E8F0"
    border_color = "#1E293B"
    accent_gradient = "linear-gradient(135deg, #FF3366, #FF6633)"
else:
    bg_color = "#F8FAFC"
    card_bg = "#FFFFFF"
    text_color = "#0F172A"
    border_color = "#E2E8F0"
    accent_gradient = "linear-gradient(135deg, #00C853, #B2FF59)"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    .sahin-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 20px;
        padding: 22px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }}
    .sahin-avatar-container {{
        text-align: center;
        padding: 15px;
    }}
    .sahin-icon {{
        font-size: 65px;
        background: {accent_gradient};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0px 5px 10px rgba(255,51,102,0.3));
    }}
    .neon-text {{
        font-weight: bold;
        color: #FF3366;
    }}
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 🔉 BULUT UYUMLU ŞAHİN ASİSTAN SES MOTORU
# ==============================================================================
async def ses_vektörü_üret(metin, dosya_yolu):
    VOICE = "tr-TR-AhmetNeural"
    communicator = edge_tts.Communicate(metin, VOICE, rate="+25%")
    await communicator.save(dosya_yolu)

def sahin_seslendir(metin):
    try:
        ses_yolu = os.path.join(BASE_DIR, "sahin_asistan.mp3")
        try: loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(ses_vektörü_üret(metin, ses_yolu))
        with open(ses_yolu, "rb") as f: ses_bytes = f.read()
        b64_ses = base64.b64encode(ses_bytes).decode()
        st.markdown(f'<audio autoplay><source src="data:audio/mp3;base64,{b64_ses}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    except Exception as e:
        pass

# ==============================================================================
# 🗺️ 13 İLÇELİ TAM COĞRAFİ VERİ BANKASI (ŞANLIURFA GLOBAL AĞI)
# ==============================================================================
ILCELER = {
    "Karaköprü": {"lat": 37.1950, "lon": 38.8150, "itfaiye": "Karaköprü Merkez İtfaiye Amirliği", "orman_mud": "Şanlıurfa Orman İşletme Müdürlüğü Merkez Ekibi"},
    "Haliliye": {"lat": 37.1650, "lon": 38.8300, "itfaiye": "Haliliye Acil Müdahale İstasyonu", "orman_mud": "Şanlıurfa Orman İşletme Müdürlüğü Merkez Ekibi"},
    "Eyyübiye": {"lat": 37.1400, "lon": 38.8000, "itfaiye": "Eyyübiye Sanayi Bölgesi İtfaiyesi", "orman_mud": "Şanlıurfa Orman İşletme Müdürlüğü Merkez Ekibi"},
    "Akçakale": {"lat": 36.7111, "lon": 38.9469, "itfaiye": "Akçakale Sınır İtfaiye Amirliği", "orman_mud": "Harran Orman Fidanlık Şefliği"},
    "Birecik": {"lat": 37.0315, "lon": 37.9782, "itfaiye": "Birecik Sahil İtfaiye Grubu", "orman_mud": "Birecik Ağaçlandırma Şefliği Ekibi"},
    "Bozova": {"lat": 37.3622, "lon": 38.4839, "itfaiye": "Bozova Merkez Müdahale Ekibi", "orman_mud": "Atatürk Barajı Havzası Orman Koruma Şefliği"},
    "Ceylanpınar": {"lat": 36.8411, "lon": 40.0428, "itfaiye": "Ceylanpınar TİGEM İtfaiye Merkezi", "orman_mud": "Ceylanpınar Orman Koruma Ekibi"},
    "Halfeti": {"lat": 37.2475, "lon": 37.8697, "itfaiye": "Halfeti Yukarı Kent İtfaiye Müfrezesi", "orman_mud": "Birecik/Halfeti Bölge Orman Şefliği"},
    "Harran": {"lat": 36.8617, "lon": 39.0306, "itfaiye": "Harran Tarihi Kültür Bölgesi İtfaiyesi", "orman_mud": "Harran Ovası Yeşillendirme Şefliği"},
    "Hilvan": {"lat": 37.5856, "lon": 38.9592, "itfaiye": "Hilvan Çıkış İstasyonu Müfrezesi", "orman_mud": "Siverek/Hilvan Bölge Orman Ekipleri"},
    "Siverek": {"lat": 37.7500, "lon": 39.3167, "itfaiye": "Siverek Bölge İtfaiye Amirliği", "orman_mud": "Siverek Orman İşletme Şefliği"},
    "Suruç": {"lat": 36.9764, "lon": 38.4244, "itfaiye": "Suruç Aligor İtfaiye Grubu", "orman_mud": "Şanlıurfa Merkez Orman Koruma Müfrezesi"},
    "Viranşehir": {"lat": 37.2353, "lon": 39.7619, "itfaiye": "Viranşehir Organize Sanayi İtfaiyesi", "orman_mud": "Viranşehir Orman Koruma ve Ağaçlandırma Şefliği"}
}

st_autorefresh(interval=25000, key="sahin_global_refresh")

# Otomatik Rastgele İlçe ve Yangın Telemetrisi Seçimi
ilce_adi = list(ILCELER.keys())[int(datetime.now().timestamp()) % len(ILCELER)]
koordinat = ILCELER[ilce_adi]

np.random.seed(int(datetime.now().timestamp()))
sicaklik = round(float(np.random.uniform(34.0, 46.0)), 1)
nem = round(float(np.random.uniform(5.0, 20.0)), 1)
rüzgar = round(float(np.random.uniform(15.0, 45.0)), 1)
risk = max(0, min(100, int((sicaklik * 1.8) - nem + (rüzgar * 0.7))))

# ==============================================================================
# 📊 ANA MOBİL ARAYÜZ (UX/UI TASARIMI)
# ==============================================================================
col_logo, col_heading = st.columns([1, 4])
with col_logo:
    st.markdown('<div class="sahin-avatar-container"><div class="sahin-icon">🦅</div></div>', unsafe_allow_html=True)
with col_heading:
    st.markdown(f"<h2 style='margin-top:10px;'>ŞAHİN Akıllı Yapay Zeka Asistanı</h2><p style='color:#aaa;'>Şanlıurfa İl Geneli Gerçek Zamanlı Yangın Algılama ve Otomatik Lojistik Yönlendirme Sistemi</p>", unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1.5])

with col_left:
    st.markdown(f"""
    <div class="sahin-card">
        <h3 style="color:#FF3366; margin-top:0;">📍 Bölgesel Telemetri</h3>
        <p><b>Aktif Tarama Bölgesi:</b> Şanlıurfa / {ilce_adi}</p>
        <p><b>Ortam Sıcaklığı:</b> {sicaklik} °C</p>
        <p><b>Atmosferik Nem:</b> %{nem}</p>
        <p><b>Rüzgar Şiddeti:</b> {rüzgar} km/s</p>
        <p style="font-size:12px; color:#777;">Enlem: {koordinat['lat']} | Boylam: {koordinat['lon']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.metric(label="📊 Hesaplanan Yapay Zeka Risk İndeksi", value=f"%{risk}", delta="KRİTİK EŞİK" if risk > 70 else "GÜVENLİ")

with col_right:
    st.markdown('<div class="sahin-card" style="padding:10px;">', unsafe_allow_html=True)
    m = folium.Map(location=[koordinat['lat'], koordinat['lon']], zoom_start=11, tiles="OpenStreetMap")
    renk = "red" if risk > 75 else "orange" if risk > 50 else "green"
    folium.Marker(location=[koordinat['lat'], koordinat['lon']], popup=f"{ilce_adi} Risk Odak Noktası", icon=folium.Icon(color=renk, icon="fire", prefix="fa")).add_to(m)
    st_folium(m, width="stretch", height=275)
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 🚒 OTOMATİK YÖNLENDİRME & STRATEJİK KOMUTA MERKEZİ
# ==============================================================================
st.write("---")
st.markdown("### ⚡ Otomatik Akıllı Yönlendirme ve Lojistik Protokolü")

if risk > 75:
    seviye = "3. DERECE (KRİTİK ACİL DURUM)"
    afad_durum = "🚨 AFAD KRİZ MASASI OTOMATİK TETİKLENDİ. HAVA DESTEĞİ VE KORDİNASYON PROTOKOLÜ AKTİF."
    renk_kod = "#D50000"
elif risk > 50:
    seviye = "2. DERECE (YÜKSEK ALARM)"
    afad_durum = "⚪ AFAD Bekleme Modunda (Bölgesel Afet Ekipleri Teyakkuzda)."
    renk_kod = "#FF6D00"
else:
    seviye = "1. DERECE (GÜVENLİ / İZLEME)"
    afad_durum = "⚪ AFAD Aktivasyonuna Gerek Görülmedi."
    renk_kod = "#00C853"

st.markdown(f"""
<div class="sahin-card" style="border-left: 8px solid {renk_kod};">
    <h4 style="color:{renk_kod}; margin-top:0;">🔥 Yangın Seviyesi: {seviye}</h4>
    <p><b>🌲 Orman Bölge Müdürlüğü Bildirimi:</b> {koordinat['orman_mud']} lojistik merkezine tam konum ve telemetri verileri aktarıldı. Öncü arazözler sevk edildi.</p>
    <p><b>🚒 En Yakın İstasyon Sevk Raporu:</b> Yangın odağına en yakın olan <b>{koordinat['itfaiye']}</b> birimleri koordinat doğrultusunda çıkış yaptı.</p>
    <p><b>🛡️ AFAD Entegrasyon Durumu:</b> {afad_durum}</p>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# 🎙️ ASİSTAN SES PRODÜKSİYONU
# ==============================================================================
if st.button("🎙️ ŞAHİN Asistanı Sesli Dinle"):
    if risk > 50:
        konusma = f"Şahine acil durum sinyali ulaştı. {ilce_adi} bölgesinde yangın riski yüzde {risk} olarak ölçüldü. En yakın {koordinat['itfaiye']} birimleri yönlendirildi. Orman bölge müdürlüğüne veri aktarımı tamamlandı."
        if risk > 75:
            konusma += " Durum kritik. Afad koordinasyon merkezi entegrasyonu sağlandı."
    else:
        konusma = f"Şahine telemetri verisi ulaştı. {ilce_adi} bölgesinde risk yüzde {risk} ile güvenli sınırdadır. İstasyonlar rutine devam ediyor."
        
    st.write(f"💬 *ŞAHİN Konuşuyor:* {konusma}")
    sahin_seslendir(konusma)
