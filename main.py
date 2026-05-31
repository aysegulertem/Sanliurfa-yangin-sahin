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
# 📱 TEMA VE SIRA DIŞI MOBİL ESTETİK AYARLARI (CSS DÖNÜŞÜMÜ)
# ==============================================================================
st.set_page_config(page_title="ŞAHİN Komuta Merkezi v2.5", layout="wide", initial_sidebar_state="expanded")

# Sol menü yapılandırması
st.sidebar.markdown("## 🎨 Arayüz Özelleştirme")
tema = st.sidebar.selectbox("Görünüm Modu Seçin", ["🌃 Siber Koyu (Gece)", "🌅 Canlı Açık (Gündüz)"])

st.sidebar.markdown("---")
st.sidebar.markdown("## 🕹️ Harita Akış Denetimi")
akis_modu = st.sidebar.radio("Çalışma Modu", ["🔄 Otomatik Canlı Simülasyon", "📍 Manuel İlçe Seçimi (Sabitle)"])

# 13 İlçeli Tam Coğrafi Veri Bankası
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

if akis_modu == "📍 Manuel İlçe Seçimi (Sabitle)":
    ilce_adi = st.sidebar.selectbox("Hedef İlçe Seçin", list(ILCELER.keys()))
else:
    st_autorefresh(interval=25000, key="sahin_global_refresh")
    ilce_adi = list(ILCELER.keys())[int(datetime.now().timestamp()) % len(ILCELER)]

koordinat = ILCELER[ilce_adi]

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
    .sahin-avatar-container {{ text-align: center; padding: 10px; }}
    .sahin-icon {{
        font-size: 65px;
        background: {accent_gradient};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
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
    except Exception as e: pass

# Telemetri Hesaplama Verileri
np.random.seed(int(datetime.now().timestamp()) + list(ILCELER.keys()).index(ilce_adi))
sicaklik = round(float(np.random.uniform(34.0, 46.0)), 1)
nem = round(float(np.random.uniform(5.0, 20.0)), 1)
rüzgar = round(float(np.random.uniform(15.0, 45.0)), 1)
risk = max(0, min(100, int((sicaklik * 1.8) - nem + (rüzgar * 0.7))))

if risk > 75:
    st.toast(f"🚨 KRİTİK ALARM: {ilce_adi} bölgesinde risk seviyesi %{risk}! AFAD bilgilendirildi.", icon="🔥")

# ==============================================================================
# 📊 ANA MOBİL ARAYÜZ ÜST KATMANI
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
    
    st.metric(label="📊 Hesaplanan Yapay Zeka Risk İndeksi", value=f"%{risk}", delta="KRİTİK EŞİK" if risk > 75 else "GÜVENLİ SINIR")

with col_right:
    st.markdown('<div class="sahin-card" style="padding:10px;">', unsafe_allow_html=True)
    
    # 🌍 image_98f599.png STİLİ: Esri World Imagery Uydu Katmanı Entegrasyonu
    uydu_katmani = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    m = folium.Map(location=[koordinat['lat'], koordinat['lon']], zoom_start=11, tiles=uydu_katmani, attr="Esri Satellite")
    
    renk = "red" if risk > 75 else "orange" if risk > 50 else "green"
    
    # Odak noktasına AFAD benzeri dairesel risk dalgası (Yarıçap) ekleme
    folium.Circle(
        location=[koordinat['lat'], koordinat['lon']],
        radius=2500,
        color=renk,
        fill=True,
        fill_color=renk,
        fill_opacity=0.3
    ).add_to(m)
    
    folium.Marker(location=[koordinat['lat'], koordinat['lon']], popup=f"{ilce_adi} Odak Noktası", icon=folium.Icon(color=renk, icon="fire", prefix="fa")).add_to(m)
    st_folium(m, width="stretch", height=275)
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 🎮 SEKME YAPISI (TABS) - AFAD SOSYAL SORUMLULUK DAHİL
# ==============================================================================
st.write("---")
sekme_operasyon, sekme_grafik, sekme_veritabani, sekme_gonullu = st.tabs([
    "🚒 Canlı Aksiyon Operasyonu", 
    "📈 Geçmiş Risk Analizi", 
    "📋 Sistem Günlük Kayıtları",
    "🌱 Haydi Umut Ol! (Doğa & Gönüllülük)"
])

# 1. SEKME: CANLI OPERASYON
with sekme_operasyon:
    if risk > 75:
        seviye = "3. DERECE (KRİTİK ACİL DURUM)"
        afad_durum = "🚨 AFAD KRİZ MASASI OTOMATİK TETİKLENDİ. HAVA DESTEĞİ PROTOKOLÜ AKTİF."
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
    <div class="sahin-card" style="border-left: 8px solid {renk_kod}; margin-top:10px;">
        <h4 style="color:{renk_kod}; margin-top:0;">🔥 Yangın Seviyesi: {seviye}</h4>
        <p><b>🌲 Orman Bölge Müdürlüğü Bildirimi:</b> {koordinat['orman_mud']} merkezine konum aktarıldı.</p>
        <p><b>🚒 En Yakın İstasyon Sevk Raporu:</b> <b>{koordinat['itfaiye']}</b> birimleri çıkış yaptı.</p>
        <p><b>🛡️ AFAD Entegrasyon Durumu:</b> {afad_durum}</p>
    </div>
    """, unsafe_allow_html=True)

    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("🚨 AFAD Kriz Merkezini Çağır", use_container_width=True): st.success("AFAD hattına veri paketi başarıyla gönderildi!")
    with col_btn2:
        if st.button("🚒 İtfaiye Rotalarını Çiz", use_container_width=True): st.info(f"{koordinat['itfaiye']} için en hızlı rota oluşturuldu.")
    with col_btn3:
        if st.button("🎙️ ŞAHİN Asistanı Sesli Dinle", use_container_width=True):
            konusma = f"{ilce_adi} bölgesinde yangın riski yüzde {risk} olarak ölçüldü."
            sahin_seslendir(konusma)

# 2. SEKME: GEÇMİŞ RİSK GRAFİĞİ
with sekme_grafik:
    st.markdown(f"#### 📈 {ilce_adi} İlçesi Son 24 Saatlik Risk Değişim Grafiği")
    saatler = [(datetime.now() - timedelta(hours=i)).strftime("%H:00") for i in range(24, 0, -1)]
    np.random.seed(list(ILCELER.keys()).index(ilce_adi))
    grafik_verisi = pd.DataFrame({
        "Saat": saatler,
        "Yapay Zeka Risk İndeksi (%)": np.random.randint(max(10, risk-30), min(100, risk+20), size=24)
    }).set_index("Saat")
    st.line_chart(grafik_verisi, color="#FF3366")

# 3. SEKME: VERİ TABANI TABLOSU
with sekme_veritabani:
    st.markdown("#### 📋 Sistem Yangın Günlük Kayıtları (Veri Tabanı)")
    df_dummy = pd.DataFrame({
        "Tarih/Saat": [(datetime.now() - timedelta(minutes=i*15)).strftime("%Y-%m-%d %H:%M") for i in range(5)],
        "Bölge / İlçe": [ilce_adi] * 5,
        "Sıcaklık (°C)": [round(sicaklik + np.random.uniform(-2, 2), 1) for _ in range(5)],
        "Risk Seviyesi": [f"%{max(10, min(100, int(risk + np.random.randint(-15, 15))))}" for _ in range(5)],
        "Durum Sinyali": ["AKTİF LOG", "ARŞİVLENDİ", "ARŞİVLENDİ", "ARŞİVLENDİ", "ARŞİVLENDİ"]
    })
    st.dataframe(df_dummy, width="stretch")

# 4. SEKME: 🌱 image_98f5c0.png ESİNTİLİ SOSYAL SORUMLULUK VE GÖNÜLLÜLÜK PANELİ
with sekme_gonullu:
    st.markdown("### 💚 Haydi Umut Ol! Doğa ve Gönüllülük Seferberliği")
    st.write("Yangın tehlikelerine karşı sadece teknolojiyle değil, dayanışmayla da savaşıyoruz. Geleceğe nefes olmak için aşağıdaki kampanyalara katılabilirsiniz.")
    
    col_card1, col_card2 = st.columns(2)
    
    with col_card1:
        st.markdown(f"""
        <div class="sahin-card" style="border-top: 5px solid #00C853; min-height: 220px;">
            <h4 style="color:#00C853; margin-top:0;">🌲 Yeşil Şanlıurfa Fidan Bağışı Kampanyası</h4>
            <p>Yapay zekanın yüksek risk veya hasar tespit ettiği bölgelerin yeniden ağaçlandırılması için fidan bağışında bulunabilirsiniz.</p>
            <p style="font-size:13px; color:#888;"><b>SMS ile Destek:</b> FİDAN yazıp 1866'ya göndererek destek olabilirsiniz.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🌱 Fidan Bağışı Simülasyonunu Başlat", use_container_width=True):
            st.balloons()
            st.success("Tebrikler! Geleceğe nefes olmak adına 1 adet fidan bağışı simüle edildi. 🌱")
            
    with col_card2:
        st.markdown(f"""
        <div class="sahin-card" style="border-top: 5px solid #00838F; min-height: 220px;">
            <h4 style="color:#00838F; margin-top:0;">🤝 Bölgesel Doğa ve Yangın Gönüllüsü Ol</h4>
            <p>Şanlıurfa ve çevresinde olası acil durumlarda ekiplere lojistik ve farkındalık desteği sağlamak için TEMA ve AFAD gönüllü ağına katılın.</p>
            <p style="font-size:13px; color:#888;">Gönüllü koordinasyon ekipleriyle anlık iletişim kurun.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🤝 Gönüllü Kayıt Formunu Aç", use_container_width=True):
            st.info("Harika! Şanlıurfa Yerel Gönüllü Kayıt Simülasyonu Aktif Edildi. Bilgileriniz başarıyla işlendi.")
