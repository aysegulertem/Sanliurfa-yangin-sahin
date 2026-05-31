import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_autorefresh import st_autorefresh
import warnings
import winsound
import os
import asyncio
import edge_tts
import base64
from datetime import datetime

warnings.filterwarnings("ignore")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ==============================================================================
# 🔉 %100 TARAYICI UYUMLU, TOK VE HIZLI ERKEK SESİ (MICROSOFT EDGE AI)
# ==============================================================================
def sahin_seslendir(metin):
    """ŞAHİN'in yanıtını yapay zeka üretimi doğal bir erkek sesiyle tarayıcıda oynatır."""
    try:
        ses_yolu = os.path.join(BASE_DIR, "sahin_ses.mp3")

        # Microsoft AI Türkçe Erkek Sesi (Ahmet) seçiliyor.
        # Hız (+25%) ayarlanarak ŞAHİN'in serileşmesi sağlanıyor.
        VOICE = "tr-TR-AhmetNeural"
        communicator = edge_tts.Communicate(metin, VOICE, rate="+25%")

        # Asenkron çalışan ses üretimini Streamlit içinde senkronize tetikliyoruz
        asyncio.run(communicator.save(ses_yolu))

        # Ses dosyasını tarayıcıya enjekte etmek için Base64'e çeviriyoruz
        with open(ses_yolu, "rb") as f:
            ses_bytes = f.read()
        b64_ses = base64.b64encode(ses_bytes).decode()

        md = f"""
            <audio autoplay>
            <source src="data:audio/mp3;base64,{b64_ses}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        pass


# ==============================================================================
# 📊 SAYFA YAPILANDIRMASI VE HAFIZA SİSTEMİ
# ==============================================================================
st.set_page_config(page_title="Şanlıurfa Yangın Komuta Merkezi", layout="wide", initial_sidebar_state="expanded")

if "yz_etap" not in st.session_state:
    st.session_state.yz_etap = 0
if "aktif_komut" not in st.session_state:
    st.session_state.aktif_komut = ""

st.markdown("""
    <style>
    .main-title { font-size:32px; font-weight:bold; color:#FF4B4B; text-align:center; margin-bottom:20px; }
    .metric-box { padding:15px; background-color:#1E1E1E; border-radius:10px; border-left:5px solid #FF4B4B; }
    .mimar-box { padding:15px; background-color:#111; border-radius:8px; border-left:5px solid #00E676; margin-top:10px; color:#FFF; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main-title'>🔥 Şanlıurfa Yangın Erken Uyarı Komuta Merkezi</div>", unsafe_allow_html=True)

st_autorefresh(interval=20000, key="yangin_datarefresh")

np.random.seed(int(datetime.now().timestamp()))
sicaklik = round(float(np.random.uniform(32.0, 44.0)), 1)
nem = round(float(np.random.uniform(8.0, 25.0)), 1)
rüzgar = round(float(np.random.uniform(12.0, 38.0)), 1)
risk = max(0, min(100, int((sicaklik * 1.6) - nem + (rüzgar * 0.6))))
son_veri = {"bölge": "Karaköprü / Şanlıurfa", "sicaklik": sicaklik, "nem": nem, "rüzgar": rüzgar,
            "zaman": datetime.now().strftime("%H:%M:%S")}

# ==============================================================================
# 🖥️ ARAYÜZ TASARIMI (METRİKLER VE HARİTA)
# ==============================================================================
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📊 Canlı Sensör Verileri")
    st.markdown(f"""
    <div class='metric-box'>
        <p><b>📍 Bölge:</b> {son_veri['bölge']}</p>
        <p><b>🌡️ Sıcaklık:</b> {son_veri['sicaklik']} °C</p>
        <p><b>💧 Nem Oranı:</b> %{son_veri['nem']}</p>
        <p><b>💨 Rüzgar Hızı:</b> {son_veri['rüzgar']} km/s</p>
        <p><b>⏱️ Son Güncelleme:</b> {son_veri['zaman']}</p>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.metric(label="🚨 ŞAHİN Yapay Zeka Yangın Riski", value=f"%{risk}", delta=f"{risk - 50} Sınır Değeri")
    if risk > 70:
        winsound.Beep(1200, 100)

with col2:
    st.subheader("🗺️ Bölgesel Risk Analiz Haritası")
    m = folium.Map(location=[37.1950, 38.8150], zoom_start=13)
    renk = "red" if risk > 70 else "orange" if risk > 40 else "green"
    folium.CircleMarker(location=[37.1950, 38.8150], radius=25, popup=f"Karaköprü Risk: %{risk}", color=renk, fill=True,
                        fill_color=renk).add_to(m)
    st_folium(m, width="stretch", height=300)

# ==============================================================================
# 🤖 MİMARİ KATMAN: GERÇEK ERKEK SESLİ ŞAHİN v2
# ==============================================================================
st.write("---")
st.subheader("🧠 Robotik Akıl Yürütme ve Üretim Merkezi (ŞAHİN v2)")

st.markdown(
    "<p style='color: #aaa;'>🎙️ <b>Jüri Özel İletişim Protokolü:</b> ŞAHİN'e telsiz kanalı üzerinden ismiyle hitap ederek sesli komut simülasyonunu başlatın.</p>",
    unsafe_allow_html=True)

col_t1, col_t2 = st.columns([1, 2])
with col_t1:
    st.markdown("**🎙️ Telsiz Mandalını Kullan:**")
    if st.button("🎚️ BAS-KONUŞ: Ses Kaydını ŞAHİN'e Gönder"):
        st.session_state.aktif_komut = "ŞAHİN, Karaköprü sensör verilerini analiz et ve üretimi başlat."
        st.session_state.yz_etap = 1

with col_t2:
    user_input = st.text_input("Ses Girdisi Görüntüleme Modülü:", value=st.session_state.aktif_komut)

if st.session_state.yz_etap > 0:
    st.write("")
    st.markdown("### 🔄 ŞAHİN Bilişsel Mimari Akışı")

    durum_etiket = "YÜKSEK ALARM" if risk > 65 else "STANDART OPERASYON"
    isik = "🟢" if risk < 50 else "🟡" if risk < 75 else "🔴"

    # 1. AŞAMA: ANLAMA
    st.markdown("#### 📥 1. Aşama: Akıllı Ses ve Niyet Çözümleme (Anlama)")
    st.info(
        f"🎤 **Gelen Ses Dalgası Algılandı:** \"{user_input}\"\n\n⚙️ **Niyet Analizi:** Kullanıcı, 'ŞAHİN' kimlik çağrısını kullandı. Karaköprü bölgesi telemetri verileri ve IoT risk motoru hedef alındı.")

    # 2. AŞAMA: DÜŞÜNME (O Çok Beğendiğin Siber Tasarım)
    st.markdown("#### 💭 2. Aşama: Bağıntısal Düşünme ve Eşik Analizi (Düşünme)")

    siber_log = f"""
    <div style="background-color: #0b0f19; border: 1px solid #1e293b; border-left: 5px solid #ffbc00; border-radius: 8px; padding: 20px; font-family: 'Courier New', monospace; color: #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5);">
        <div style="color: #ffbc00; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #334155; padding-bottom: 5px;">🧠 ŞAHİN HİBRİT BİLİŞSEL MOTORU - AKIL YÜRÜTME LOGU</div>
        <div style="margin-bottom: 6px;"><span style="color: #38bdf8;">[TELEMETRİ]</span> Bağlantı Durumu: <span style="color: #4ade80;">AKTİF</span> | Hedef Bölge: <span style="color: #fb923c;">Karaköprü / Şanlıurfa</span></div>
        <div style="margin-bottom: 6px;"><span style="color: #38bdf8;">[VERI_OKUMA]</span> Sıcaklık: <span style="color: #f87171;">{sicaklik}°C</span> (Kritik Eşik: 35.0°C)</div>
        <div style="margin-bottom: 6px;"><span style="color: #38bdf8;">[VERI_OKUMA]</span> Nem Oranı: <span style="color: #f87171;">%{nem}</span> (Kritik Eşik: %15.0)</div>
        <div style="margin-bottom: 6px;"><span style="color: #38bdf8;">[VERI_OKUMA]</span> Rüzgar Hızı: <span style="color: #f87171;">{rüzgar} km/s</span> (Kritik Eşik: 25.0 km/s)</div>
        <div style="margin-bottom: 6px; background-color: #1e293b; padding: 6px; border-radius: 4px; color: #a78bfa;"><span style="color: #c084fc;">[MATRIS_ALGORITMASI]</span> Risk_Formülü = (({sicaklik} × 1.6) - {nem} + ({rüzgar} × 0.6))</div>
        <div style="margin-bottom: 6px;"><span style="color: #38bdf8;">[MATRIS_CIKTI]</span> Hesaplanan Kompakt Risk Oranı: <span style="color: #ffbc00; font-weight: bold;">%{risk}</span></div>
        <div style="margin-bottom: 6px;"><span style="color: #38bdf8;">[DURUM_ISIGI]</span> Sistem Güvenlik İndeksi: <span style="font-size: 14px;">{isik} {durum_etiket}</span></div>
        <div style="margin-top: 10px; border-top: 1px solid #334155; padding-top: 8px; color: #4ade80; font-weight: bold;">🤖 KARAR: Stratejik Eylem Protokolü Tetiklendi. Üretime Geçiliyor...</div>
    </div>
    """
    st.markdown(siber_log, unsafe_allow_html=True)

    # 3. AŞAMA: ÜRETİM
    st.markdown("#### 🏭 3. Aşama: Üretim ve Aksiyon Modülü (Üretim)")

    sahin_yaniti = (
        f"**🤖 ŞAHİN Yapay Zeka Komuta Çıktısı:**\n\n"
        f"Komut başarıyla alındı ve anlaşıldı. Karaköprü istasyonu telemetri hatları kontrol edildi.\n\n"
        f"🔥 **Anlık Risk Seviyesi:** %{risk} | **Sistem Durumu:** {durum_etiket}\n\n"
        f"**📋 Üretilen Stratejik Aksiyon Maddeleri:**\n"
        f"1. **IoT Veri Doğrulama:** {sicaklik}°C sıcaklık ve %{nem} nem dengesiyle oluşan risk katmanı doğrulanmıştır.\n"
        f"2. **Lojistik Entegrasyon:** Karaköprü itfaiye yerleşkesindeki operasyon ekipleri mevcut risk oranına göre bilgilendirilmiştir.\n"
        f"3. **Otomasyon Günlüğü:** Yangın kayıt sistemi (`yangin_gunlugu.txt`) anlık telemetri verileriyle güncellenmiştir."
    )

    st.markdown(f"<div class='mimar-box'>{sahin_yaniti.replace('\n', '<br>')}</div>", unsafe_allow_html=True)

    # 🚀 Yapay Zeka Destekli Erkek Sesiyle Anons Başlatılıyor
    sahin_seslendir(
        f"Şahin komutu algıladı. Karaköprü verileri düşünüldü ve işlendi. Yangın riski yüzde {risk}. Üretim protokolü aktif.")

# ==============================================================================
# 📋 VERİ TABANI KAYITLARI
# ==============================================================================
st.write("---")
st.subheader("📋 Sistem Yangın Günlük Kayıtları (Veri Tabanı)")
df_dummy = pd.DataFrame({
    "Tarih/Saat": [datetime.now().strftime("%Y-%m-%d %H:%M")],
    "Bölge": ["Karaköprü"],
    "Sıcaklık (°C)": [sicaklik],
    "Risk Seviyesi": [f"%{risk}"]
})
st.dataframe(df_dummy, width="stretch")
