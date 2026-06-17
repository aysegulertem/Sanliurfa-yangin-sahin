# ==================== IMPORTLAR ====================
import os  
import json  
import streamlit as st
import pandas as pd
import numpy as np
import folium
import warnings
import asyncio
import base64
import edge_tts  # Profesyonel Türkçe erkek sesi
import speech_recognition as sr  # Ses tanıma motoru
import requests  # İnternet kontrolü için
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_folium import st_folium # Harita için

# Sayfa ayarları (en üstte olmalı)
st.set_page_config(layout="wide")

# Session State tanımlamaları (Hataları önlemek için)
if "gecmis_risk" not in st.session_state:
    st.session_state.gecmis_risk = [
        {"Saat": "17:00", "Merkez Bölge Risk (%)": 35, "Saha Genel Risk (%)": 50},
        {"Saat": "17:15", "Merkez Bölge Risk (%)": 40, "Saha Genel Risk (%)": 50},
        {"Saat": "17:30", "Merkez Bölge Risk (%)": 65, "Saha Genel Risk (%)": 50},
        {"Saat": "17:45", "Merkez Bölge Risk (%)": 45, "Saha Genel Risk (%)": 50},
        {"Saat": "18:00", "Merkez Bölge Risk (%)": 27, "Saha Genel Risk (%)": 50}
    ]
if "ilce_adi" not in st.session_state:
    st.session_state.ilce_adi = "Haliliye"

warnings.filterwarnings("ignore")

# Proje dizininde LoRA klasörlerini otomatik oluşturma tanımları
LORA_DIR = "lora_weights"
LOG_DIR = "lora_logs"
os.makedirs(LORA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ==============================================================================
# OTURUM VERİLERİ (İnternet Olmadan Çalışması İçin)
# ==============================================================================
if "veri_log" not in st.session_state:
    # Sistem Günlük Kayıtları sekmesini dolduracak gerçekçi AFAD/İtfaiye lojistik geçmişi
    st.session_state.veri_log = [
        {"Zaman": (datetime.now() - timedelta(minutes=45)).strftime("%H:%M:%S"), "İlçe": "Haliliye", "Risk": "%68", "Aksiyon": "Devriye Çıkarıldı", "Durum": "⚠️ UYARI"},
        {"Zaman": (datetime.now() - timedelta(hours=2)).strftime("%H:%M:%S"), "İlçe": "Eyyübiye", "Risk": "%42", "Aksiyon": "Rutin Kontrol", "Durum": "🟢 STABİL"},
        {"Zaman": (datetime.now() - timedelta(hours=4)).strftime("%H:%M:%S"), "İlçe": "Ceylanpınar", "Risk": "%85", "Aksiyon": "Arazöz Sevk Edildi", "Durum": "🚨 KRİTİK"},
        {"Zaman": (datetime.now() - timedelta(hours=6)).strftime("%H:%M:%S"), "İlçe": "Siverek", "Risk": "%35", "Aksiyon": "Sensör Kalibrasyonu", "Durum": "🟢 STABİL"},
        {"Zaman": (datetime.now() - timedelta(hours=8)).strftime("%H:%M:%S"), "İlçe": "Birecik", "Risk": "%74", "Aksiyon": "Hava Keşfi İstendi", "Durum": "⚠️ UYARI"}
    ]

if "gecmis_risk" not in st.session_state:
    # Grafik sekmesini besleyecek geriye dönük 12 saatlik Şanlıurfa genel risk trend verisi
    saatler = [(datetime.now() - timedelta(hours=i)).strftime("%H:00") for i in range(12, 0, -1)]
    st.session_state.gecmis_risk = {
        "Saat": saatler,
        "Merkez Bölge Risk (%)": [35, 38, 42, 45, 52, 60, 68, 65, 58, 50, 48, 42],
        "Kritik Sınır Eşiği": [50] * 12
    }

if "aktif_lora" not in st.session_state:
    st.session_state.aktif_lora = "Yok (Taban Model)"

if "lora_gecmisi" not in st.session_state:
    log_dosyasi = os.path.join(LOG_DIR, "lora_history.json")
    if os.path.exists(log_dosyasi):
        with open(log_dosyasi, "r") as f:
            st.session_state.lora_gecmisi = json.load(f)
    else:
        st.session_state.lora_gecmisi = [
            {
                "Tarih": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
                "Model Adı": "lora_shn_r16_a32_eyyubiye_v1",
                "Rank (r)": 16,
                "Alpha": 32,
                "Epoch": 3,
                "Veri Kümesi": "eyyubiye_kuru_ot_anomali",
                "Durum": "🟢 BAŞARILI"
            },
            {
                "Tarih": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
                "Model Adı": "lora_shn_r32_a64_ceylanpinar_v2",
                "Rank (r)": 32,
                "Alpha": 64,
                "Epoch": 5,
                "Veri Kümesi": "ceylanpinar_yuksek_isi_proseduru",
                "Durum": "🟢 BAŞARILI"
            }
        ]
        for kayit in st.session_state.lora_gecmisi:
            with open(os.path.join(LORA_DIR, f"{kayit['Model Adı']}.safetensors"), "w") as f:
                f.write("LORA_DUMMY_WEIGHTS")
        with open(log_dosyasi, "w") as f:
            json.dump(st.session_state.lora_gecmisi, f, indent=4)

# ==============================================================================
# SAYFA AYARLARI
# ==============================================================================
st.set_page_config(
    page_title="Orman Yangını Komuta Merkezi",
    page_icon="🚨",
    layout="wide"
)

# ==============================================================================
# ŞAHİN ASYNC ERKEK SES MOTORU (EDGE-TTS)
# ==============================================================================
async def amain(metin) -> bytes:
    communicate = edge_tts.Communicate(metin, "tr-TR-AhmetNeural", rate="+0%")
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
    return audio_bytes

def sahin_seslendir(cevap_metni):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ses_verisi = loop.run_until_complete(amain(cevap_metni))
        loop.close()
        
        b64_ses = base64.b64encode(ses_verisi).decode("utf-8")
        ses_html = f"""
            <audio autoplay style="display:none;">
                <source src="data:audio/mp3;base64,{b64_ses}" type="audio/mp3">
            </audio>
        """
        st.markdown(ses_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"⚠️ Seslendirme motoru hatası: {e}")

# ==============================================================================
# İNTERNET KONTROLÜ
# ==============================================================================
def internet_var_mi():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except:
        return False

# ==============================================================================
# VERİ LOG FONKSİYONU
# ==============================================================================
def log_kaydet(ilce, risk_val, seviye_str):
    # Tablo yapısıyla tam uyumlu olması için yeni log girdisi ekliyoruz
    yeni_log = {
        "Zaman": datetime.now().strftime("%H:%M:%S"),
        "İlçe": ilce,
        "Risk": f"%{risk_val}",
        "Aksiyon": "Sistem Taraması Aktif",
        "Durum": "🚨 KRİTİK" if risk_val >= 75 else "⚠️ UYARI" if risk_val >= 45 else "🟢 STABİL"
    }
    st.session_state.veri_log.append(yeni_log)
    if len(st.session_state.veri_log) > 50:
        st.session_state.veri_log = st.session_state.veri_log[-50:]

# ==============================================================================
# GÜVENLİ VE OTOMATİK FREKANS TARAMALI DİNLEME MOTORU
# ==============================================================================
def sahin_dinle():
    import sounddevice as sd
    import wave
    import io

    duration = 5
    aktif_cihaz_id = 9
    denenecek_frekanslar = [44100, 48000, 16000, 32000]

    audio_raw = None
    fs = None

    for hizi_dene in denenecek_frekanslar:
        try:
            audio_raw = sd.rec(
                int(duration * hizi_dene),
                samplerate=hizi_dene,
                channels=1,
                dtype='float32',
                device=aktif_cihaz_id
            )
            fs = hizi_dene
            break
        except Exception:
            continue

    if audio_raw is None or fs is None:
        st.error("❌ Giriş kanalı kilitli.")
        return None

    st.info(f"🎧 ŞAHİN Dinliyor... [{fs} Hz]")

    try:
        sd.wait()
        
        max_val = np.max(np.abs(audio_raw))
        if max_val > 0:
            audio_normal = (audio_raw / max_val) * 32767.0
        else:
            audio_normal = audio_raw * 32767.0

        audio_data = audio_normal.astype(np.int16)

        wav_buf = io.BytesIO()
        with wave.open(wav_buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(audio_data.tobytes())

        wav_buf.seek(0)

        r = sr.Recognizer()
        with sr.AudioFile(wav_buf) as source:
            audio = r.record(source)

        metin = r.recognize_google(audio, language="tr-TR")
        return metin.lower()

    except sr.UnknownValueError:
        st.error("❌ Anlayamadı.")
        return None
    except Exception as e:
        st.error(f"⚠️ Hata: {e}")
        return None

# ==============================================================================
# MODERN CSS
# ==============================================================================
st.markdown("""
<style>
            
.sahin-card {
    background: #1e293b; 
    padding: 20px; 
    border-radius: 15px; 
    border: 1px solid #334155; 
    margin-bottom: 15px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.3);
}
.sahin-robot-container {
    display:flex;flex-direction:column;align-items:center;justify-content:center;background:linear-gradient(135deg,#111827,#1f2937);padding:25px;border-radius:20px;border:2px solid #3b82f6;box-shadow:0 0 15px rgba(59,130,246,0.4);text-align:center;height:380px;}
.sahin-core {width:90px;height:90px;background:radial-gradient(circle,#00f2fe 0%,#4facfe 100%);border-radius:50%;box-shadow:0 0 30px #00f2fe;animation:pulse 2s infinite alternate;display:flex;align-items:center;justify-content:center;font-size:40px;margin-bottom:10px;}
@keyframes pulse {0%{transform:scale(0.92);box-shadow:0 0 15px #00f2fe}100%{transform:scale(1.08);box-shadow:0 0 35px #00f2fe}}
.sahin-status {color:#00f2fe;font-family:'Courier New';font-weight:bold;margin-top:10px;font-size:13px;letter-spacing:1px;}
.weather-card-wide {background:linear-gradient(145deg,#1e293b,#0f172a);border-radius:16px;padding:15px 20px;box-shadow:0 4px 15px rgba(0,0,0,0.25);border:1px solid #334155;text-align:center;margin-top:15px;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ŞANLIURFA İLÇE VERİTABANI
# ==============================================================================
ILCELER = {
    "Haliliye": {"lat": 37.1650, "lon": 38.8300, "itfaiye": "Haliliye Acil", "taban_sicaklik": 33.0, "taban_nem": 18.0, "taban_ruzgar": 9.8, "yon": "➡️", "senaryo": "safe"},
    "Karaköprü": {"lat": 37.1950, "lon": 38.8150, "itfaiye": "Karaköprü", "taban_sicaklik": 32.5, "taban_nem": 19.0, "taban_ruzgar": 10.2, "yon": "↗️", "senaryo": "safe"},
    "Eyyübiye": {"lat": 37.1400, "lon": 38.8000, "itfaiye": "Eyyübiye", "taban_sicaklik": 36.2, "taban_nem": 15.0, "taban_ruzgar": 16.0, "yon": "➡️", "senaryo": "warning"},
    "Akçakale": {"lat": 36.7111, "lon": 38.9469, "itfaiye": "Akçakale", "taban_sicaklik": 42.2, "taban_nem": 8.0, "taban_ruzgar": 24.5, "yon": "↗️", "senaryo": "critical"},
    "Harran": {"lat": 36.8617, "lon": 39.0306, "itfaiye": "Harran", "taban_sicaklik": 35.0, "taban_nem": 15.0, "taban_ruzgar": 13.0, "yon": "➡️", "senaryo": "safe"},
    "Birecik": {"lat": 37.0315, "lon": 37.9782, "itfaiye": "Birecik", "taban_sicaklik": 34.1, "taban_nem": 16.0, "taban_ruzgar": 8.5, "yon": "↘️", "senaryo": "safe"},
    "Bozova": {"lat": 37.3622, "lon": 38.4839, "itfaiye": "Bozova", "taban_sicaklik": 32.8, "taban_nem": 20.0, "taban_ruzgar": 12.0, "yon": "↖️", "senaryo": "safe"},
    "Ceylanpınar": {"lat": 36.8411, "lon": 40.0428, "itfaiye": "Ceylanpınar", "taban_sicaklik": 43.0, "taban_nem": 7.0, "taban_ruzgar": 28.0, "yon": "➡️", "senaryo": "critical"},
    "Halfeti": {"lat": 37.2475, "lon": 37.8697, "itfaiye": "Halfeti", "taban_sicaklik": 32.2, "taban_nem": 21.0, "taban_ruzgar": 7.8, "yon": "⬇️", "senaryo": "safe"},
    "Hilvan": {"lat": 37.5856, "lon": 38.9592, "itfaiye": "Hilvan", "taban_sicaklik": 31.8, "taban_nem": 22.0, "taban_ruzgar": 11.5, "yon": "↖️", "senaryo": "safe"},
    "Siverek": {"lat": 37.7500, "lon": 39.3167, "itfaiye": "Siverek", "taban_sicaklik": 31.0, "taban_nem": 24.0, "taban_ruzgar": 13.0, "yon": "⬆️", "senaryo": "safe"},
    "Suruç": {"lat": 36.9764, "lon": 38.4244, "itfaiye": "Suruç", "taban_sicaklik": 34.5, "taban_nem": 16.0, "taban_ruzgar": 10.0, "yon": "➡️", "senaryo": "safe"},
    "Viranşehir": {"lat": 37.2353, "lon": 39.7619, "itfaiye": "Viranşehir", "taban_sicaklik": 35.5, "taban_nem": 13.0, "taban_ruzgar": 12.5, "yon": "↗️", "senaryo": "safe"}
}

# GÖRÜNTÜLEME MODU
goruntuleme_modu = st.radio("📡", ["📍 Manuel", "🔄 Otomatik"], horizontal=True, key="mod")

if goruntuleme_modu == "📍 Manuel":
    st.session_state.ilce_adi = st.selectbox("📍", list(ILCELER.keys()), key="secim")
else:
    st.session_state.ilce_adi = list(ILCELER.keys())[int(datetime.now().timestamp() / 15) % len(ILCELER)]

ilce_adi = st.session_state.ilce_adi
koordinat = ILCELER[ilce_adi]


# TELEMETRİ HESAPLAMALARI
np.random.seed(int(datetime.now().timestamp()) + len(ilce_adi))
sicaklik = round(float(koordinat["taban_sicaklik"] + np.random.uniform(-0.3, 0.4)), 1)
nem = round(float(koordinat["taban_nem"] + np.random.uniform(-1.0, 1.0)), 1)
ruzgar = round(float(koordinat["taban_ruzgar"] + np.random.uniform(-0.5, 0.5)), 1)
egim = round(float(np.random.uniform(8.0, 15.0)), 1)

if koordinat["senaryo"] == "critical":
    duman = int(np.random.randint(380, 520))
    hke = int(np.random.randint(160, 240))
    risk = int(np.random.randint(82, 96))
elif koordinat["senaryo"] == "warning":
    duman = int(np.random.randint(90, 140))
    hke = int(np.random.randint(65, 95))
    risk = int(np.random.randint(52, 68))
else:
    duman = int(np.random.randint(12, 28))
    hke = 45
    base_risk = (sicaklik * 1.0) - (nem * 0.5) + (ruzgar * 0.3)
    risk = int(max(10, min(base_risk, 44)))

if risk >= 75:
    seviye, ikon, banner_renk = "KRİTİK", "🚨", "linear-gradient(135deg, #D50000, #FF6D00)"
elif risk >= 45:
    seviye, ikon, banner_renk = "YÜKSEK", "⚠️", "linear-gradient(135deg, #FFD600, #FF8F00)"
else:
    seviye, ikon, banner_renk = "DÜŞÜK", "✅", "linear-gradient(135deg, #00C853, #64DD17)"

# ==================== 🔥 SÖZLÜK UYUMLU DOĞRU AKTARIM ADIMI 🔥 ====================
log_kaydet(ilce_adi, risk, seviye)

baska_bir_deger = 50
yeni_veri = {
    "Saat": datetime.now().strftime("%H:%M:%S"),
    "Merkez Bölge Risk (%)": risk,
    "Saha Genel Risk (%)": baska_bir_deger # Varsa diğer değeriniz
}
st.session_state.gecmis_risk.append(yeni_veri)

# Bellek koruması (Max 50)
# 1. Listeyi DataFrame'e çevir
df_kontrol = pd.DataFrame(st.session_state.gecmis_risk)

# 2. DataFrame üzerinden kontrol et
if len(df_kontrol) > 50:
    # Eğer 50 satırı geçtiyse, en eskiyi sil (isteğe bağlı)
    st.session_state.gecmis_risk.pop(0)
    st.session_state.gecmis_risk["Merkez Bölge Risk (%)"] = st.session_state.gecmis_risk["Merkez Bölge Risk (%)"][-50:]
    st.session_state.gecmis_risk["Saat"] = st.session_state.gecmis_risk["Saat"][-50:]
    st.session_state.gecmis_risk["Kritik Sınır Eşiği"] = st.session_state.gecmis_risk["Kritik Sınır Eşiği"][-50:]

# INTERNET KONTROLÜ
if not internet_var_mi():
    st.warning("⚠️ İnternet yok! Önbellek verileri kullanılıyor.")
    kaynak = "💾 Önbellek"
else:
    kaynak = "📡 Canlı"


# ==============================================================================
# 🚀 PROFEOSYONEL OGM KOMUTA BANNERI VE KONTROL PANELİ
# ==============================================================================

if risk >= 75:
    neon_renk = "#ef4444"       # Kritik Kırmızı
    border_glow = "0 0 15px rgba(239, 68, 68, 0.25)"
    badge_bg = "rgba(239, 68, 68, 0.1)"
elif risk >= 45:
    neon_renk = "#f59e0b"       # Uyarı Turuncusu
    border_glow = "0 0 15px rgba(245, 158, 11, 0.25)"
    badge_bg = "rgba(245, 158, 11, 0.1)"
else:
    neon_renk = "#10b981"       # Stabil Yeşil
    border_glow = "0 0 15px rgba(16, 185, 129, 0.25)"
    badge_bg = "rgba(16, 185, 129, 0.1)"

st.markdown(f"""
<style>
/* Kurumsal Banner Alanı */
.ogm-military-banner {{
    background: linear-gradient(135deg, #0b0f19 0%, #111827 100%);
    border-left: 5px solid {neon_renk};
    border-top: 1px solid #1f2937;
    border-right: 1px solid #1f2937;
    border-bottom: 1px solid #1f2937;
    box-shadow: {border_glow};
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.ogm-title-group h1 {{
    font-family: 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    font-size: 24px;
    color: #f3f4f6;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
.ogm-sub-badge {{
    display: inline-block;
    background: {badge_bg};
    border: 1px solid {neon_renk}44;
    color: {neon_renk};
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    margin-top: 6px;
    letter-spacing: 0.5px;
}}
.ogm-risk-value {{
    font-size: 38px;
    font-weight: 800;
    color: {neon_renk};
    font-family: monospace;
    line-height: 1;
}}
.ogm-status-text {{
    font-size: 11px;
    font-weight: 700;
    color: #9ca3af;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-top: 4px;
}}
/* Termal Kamera Panel Kutusu */
.termal-container-box {{
    background: #0b0f19;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 18px;
    margin-bottom: 20px;
}}
.termal-header {{
    color: #ef4444;
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 1px;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 6px;
}}
.termal-grid-layout {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
}}
.termal-stat-item {{
    border-left: 2px solid #374151;
    padding-left: 12px;
}}
.termal-stat-label {{
    font-size: 11px;
    color: #6b7280;
    text-transform: uppercase;
    font-weight: 600;
}}
.termal-stat-val {{
    font-size: 22px;
    font-weight: 700;
    color: #e5e7eb;
    margin-top: 2px;
}}
</style>
""", unsafe_allow_html=True)




# ==============================================================================
# 3. CANLI AKSİYON VE TERMAL VERİ BESLEMESİ (Bozuk Kodlar Ayıklandı)
# ==============================================================================
st.markdown("### 🚨 Saha Koordinasyon Merkezi")
st.info(f"📍 Aktif Gözlem Bölgesi: **{ilce_adi}** | Durum: **{seviye}**")

# 2. ÜST METRİKLER (Durum Göstergeleri)
col_op1, col_op2, col_op3 = st.columns(3)
with col_op1:
    st.metric("🚨 Operasyon Durumu", seviye, delta="Aktif Takip")
with col_op2:
    st.metric("🚒 Hazır İtfaiye Filosu", "14 Araç / 42 Personel", delta="Tam Kapasite", delta_color="normal")
with col_op3:
    st.metric("🛸 İHA / Drone Keşif", "ŞAHİN-1 Havada", delta="Anlık Veri Aktif", delta_color="normal")

# Alt Kısım: Termal Veri Matrisi ve Telsiz Akışı
col_main1, col_main2 = st.columns([5, 4])



   
# (Kontrol Merkezi) - artık Operasyon sekmesi içinde tek noktadan yönetiliyor.

# ==============================================================================
# 🏢 YENİ NESİL OGM KOMUTA BANNERI RENDER
# ==============================================================================


# 2. ROBOT VE HARİTA COLUMNS (Dengeli Yükseklik Ayarıyla)
c1, c2 = st.columns([1, 1])
ses = None 

with c1:
    st.markdown("""<div class="sahin-robot-container"><div class="sahin-core">🦅</div><div style="color:white;font-weight:bold;font-size:22px;">ŞAHİN v2.5</div><div class="sahin-status">● SESLİ İLETİŞİM AKTİF</div></div>""", unsafe_allow_html=True)
    
    if st.button("🎤 Sor", key="btn_sor"):
        ses = sahin_dinle()
        if ses: 
            if any(k in ses for k in ["sıcaklık", "derece", "sıcak"]):
                cevap = f"{ilce_adi} bölgesinde anlık sıcaklık {sicaklik} derece seyrinde."
            elif any(k in ses for k in ["risk", "durum", "tehlike", "alarm"]):
                cevap = f"{ilce_adi} için hesaplanan yangın riski yüzde {risk}. Şu an {seviye} seviyedeyiz."
            elif any(k in ses for k in ["nem", "rutubet"]):
                cevap = f"{ilce_adi} bölgesinde nem oranı yüzde {nem} olarak ölçüldü."
            elif any(k in ses for k in ["rüzgar", "fırtına", "esinti"]):
                cevap = f"Rüzgar hızı saatte {ruzgar} kilometre, yönü ise {koordinat['yon']}."
            else:
                cevap = f"{ilce_adi} bölgesi analiz edildi. Risk oranı yüzde {risk}."
            
            st.success(f"🤖 {cevap}")
            sahin_seslendir(cevap)

@st.cache_resource(show_spinner=False)
def haritayi_olustur(enlem, boylam, risk_degeri, ilce_ismi, itfaiye_merkezi):
    m = folium.Map(location=[enlem, boylam], zoom_start=11)
    renk = "red" if risk_degeri >= 75 else "orange" if risk_degeri >= 45 else "green"
    popup_metni = f"<b>{ilce_ismi}</b><br>Risk: %{risk_degeri}<br>İtfaiye: {itfaiye_merkezi}"
    folium.Circle(
        [enlem, boylam], radius=3000, color=renk, fill=True, fill_opacity=0.1,
        popup=folium.Popup(popup_metni, max_width=200)
    ).add_to(m)
    folium.Marker([enlem, boylam], icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
    return m

with c2:
    harita_objesi = haritayi_olustur(koordinat["lat"], koordinat["lon"], risk, ilce_adi, koordinat["itfaiye"])
    st_folium(harita_objesi, height=380, key=f"harita_{ilce_adi}") 

st.write("---")

# 3. YENİ NESİL ÖZELLEŞTİRİLMİŞ TELEMETRİ GRID'İ
st.markdown("### 📊 Anlık Sensör ve Telemetri Matrisi")

# Delta durum renkleri ve mantığı
sicaklik_delta = f"<span style='color:#ef4444;'>🔥 KRİTİK</span>" if sicaklik > 38 else f"<span style='color:#64748b;'>NORMAL</span>"
nem_delta = f"<span style='color:#ef4444;'>⚠️ DÜŞÜK</span>" if nem < 12 else f"<span style='color:#10b981;'>OPTIMAL</span>"
duman_delta = f"<span style='color:#ef4444;'>🚨 ANOMALİ</span>" if duman > 200 else f"<span style='color:#10b981;'>TEMİZ</span>"

# Streamlit'in iç div'lerini bypass eden ve yan yana dizilimi garanti eden esnek CSS
st.markdown(f"""
<style>
.sahin-telemetri-flex-container {{
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    justify-content: space-between !important;
    gap: 12px !important;
    width: 100% !important;
    margin-bottom: 25px !important;
}}
.telemetri-card-new {{
    flex: 1 !important;
    min-width: 100px !important;
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px !important;
    padding: 12px 8px !important;
    text-align: center !important;
    transition: all 0.3s ease !important;
}}
.telemetri-card-new:hover {{
    border-color: #3b82f6 !important;
    transform: translateY(-2px) !important;
    background: #111827 !important;
}}
.tel-icon-new {{
    font-size: 20px !important;
    margin-bottom: 4px !important;
}}
.tel-label-new {{
    font-size: 10px !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
}}
.tel-value-new {{
    font-size: 18px !important;
    font-weight: 700 !important;
    color: #f1f5f9 !important;
    margin-top: 2px !important;
    font-family: 'Courier New', monospace !important;
}}
.tel-delta-new {{
    font-size: 10px !important;
    margin-top: 2px !important;
    font-weight: bold !important;
}}
</style>

<div class="sahin-telemetri-flex-container">
    <div class="telemetri-card-new">
        <div class="tel-icon-new">🌡️</div>
        <div class="tel-label-new">SICAKLIK</div>
        <div class="tel-value-new">{sicaklik}°C</div>
        <div class="tel-delta-new">{sicaklik_delta}</div>
    </div>
    <div class="telemetri-card-new">
        <div class="tel-icon-new">💧</div>
        <div class="tel-label-new">NEM ORANI</div>
        <div class="tel-value-new">%{nem}</div>
        <div class="telemetri-card-new" style="display:none;"></div> <div class="tel-delta-new">{nem_delta}</div>
    </div>
    <div class="telemetri-card-new">
        <div class="tel-icon-new">💨</div>
        <div class="tel-label-new">RÜZGAR</div>
        <div class="tel-value-new">{ruzgar} <span style='font-size:10px;'>km/s</span></div>
        <div class="tel-delta-new" style="color:#3b82f6;">YÖN: {koordinat['yon']}</div>
    </div>
    <div class="telemetri-card-new">
        <div class="tel-icon-new">🌫️</div>
        <div class="tel-label-new">DUMAN (PPM)</div>
        <div class="tel-value-new">{duman}</div>
        <div class="tel-delta-new">{duman_delta}</div>
    </div>
    <div class="telemetri-card-new">
        <div class="tel-icon-new">🍃</div>
        <div class="tel-label-new">HAVA KALİTESİ</div>
        <div class="tel-value-new">HKE {hke}</div>
        <div class="tel-delta-new" style="color:#10b981;">STABİL</div>
    </div>
    <div class="telemetri-card-new">
        <div class="tel-icon-new">⛰️</div>
        <div class="tel-label-new">ARAZİ EĞİMİ</div>
        <div class="tel-value-new">{egim}°</div>
        <div class="tel-delta-new" style="color:#64748b;">SABİT</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================

# SEKMELER TANIMI
sekme_operasyon, sekme_grafik, sekme_veritabani, sekme_gonullu, sekme_lora = st.tabs([
    "🚒 Canlı Aksiyon Operasyonu",
    "📈 Geçmiş Risk Analizi",
    "📋 Sistem Günlük Kayıtları",
    "🌱 Haydi Umut Ol! (Doğa & Gönüllülük)",
    "🤖 LoRA Kontrol & Eğitim"
])

# ==============================================================================
# 1. SEKME: OPERASYON MERKEZİ 
# ==============================================================================
with sekme_operasyon:
    st.markdown("### 🚒 Canlı Aksiyon & Saha Koordinasyon Merkezi")

    # Termal ve Telsiz için ana kolonlar
    col_sol, col_sag = st.columns([2, 1])

    with col_sol:
        st.markdown(f"""
        <div class="termal-container-box">
            <div class="termal-header">🔴 CANLI TERMAL VE SENSÖR MATRİSİ</div>
            <div class="termal-grid-layout">
                <div class="termal-stat-item">
                    <div class="termal-stat-label">Mod</div>
                    <div class="termal-stat-val">Kızılötesi (IR)</div>
                </div>
                <div class="termal-stat-item">
                    <div class="termal-stat-label">Sıcaklık</div>
                    <div class="termal-stat-val" style="color:#ef4444;">{sicaklik} °C <small>↗</small></div>
                </div>
                <div class="termal-stat-item">
                    <div class="termal-stat-label">Duman</div>
                    <div class="termal-stat-val">{duman} PPM</div>
                </div>
                <div class="termal-stat-item">
                    <div class="termal-stat-label">Sinyal</div>
                    <div class="termal-stat-val">%98</div>
                </div>
                <div class="termal-stat-item">
                    <div class="termal-stat-label">Risk Seviyesi</div>
                    <div class="termal-stat-val" style="color:#f59e0b;">{seviye}</div>
                </div>
                <div class="termal-stat-item">
                    <div class="termal-stat-label">Emisyon</div>
                    <div class="termal-stat-val">0.95</div>
                </div>
                <div class="termal-stat-item" style="grid-column: span 2;">
                    <div class="termal-stat-label">Algoritma Durumu</div>
                    <div class="termal-stat-val" style="color:#3b82f6;">ŞAHİN v2.0 - AKTİF</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
      
    with col_sag:
        st.markdown("### 📻 Telsiz Akışı")
        st.code(f"""[{datetime.now().strftime('%H:%M:%S')}] {ilce_adi} devriyesi aktif.
[{datetime.now().strftime('%H:%M:%S')}] Sensörler stabil.
[MERKEZ] Hava desteği hazır.""", language="text")
        
        b1, b2 = st.columns(2)
        if b1.button("🚨 AFAD Rapor", use_container_width=True):
            st.toast("Rapor iletildi", icon="📡")
        if b2.button("🚒 Rota", use_container_width=True):
            st.toast("Rota hesaplandı", icon="🗺️")
  

# --- GRAFİK BÖLÜMÜ ---
secili_ilce = st.session_state.get("ilçe_adi", "Haliliye")
st.markdown(f"### 📈 {secili_ilce} İlçesi Detaylı Risk Analiz Grafikleri")
df_grafik = pd.DataFrame(st.session_state.gecmis_risk).set_index("Saat")
st.line_chart(df_grafik, use_container_width=True, color=["#ff3366", "#3b82f6"])

# --- GRAFİK BÖLÜMÜ ---
secili_ilce = st.session_state.get("ilce_adi", "Haliliye")
st.markdown(f"### 📈 {secili_ilce} İlçesi Detaylı Risk Analiz Grafikleri")

df_grafik = pd.DataFrame(st.session_state.gecmis_risk).set_index("Saat")
st.line_chart(df_grafik, use_container_width=True)

with st.container(border=True):
    st.markdown(f"💡 **Yapay Zeka Raporu:** {secili_ilce} bölgesi için veriler stabil.")

# ==============================================================================
# 2. SEKME: GRAFİK ANALİZLERİ
# ==============================================================================
with sekme_grafik:
    # İlçe adını güvenli bir şekilde al
    secili_ilce = st.session_state.get("ilce_adi", "Haliliye")
    st.markdown(f"### 📈 {secili_ilce} İlçesi Detaylı Risk Analiz Grafikleri")
    
    # DataFrame oluşturma ve Grafik
    df_grafik = pd.DataFrame(st.session_state.gecmis_risk).set_index("Saat")
    st.line_chart(df_grafik, use_container_width=True, color=["#ff3366", "#3b82f6"])
    
    # Rapor kutusu (Mükerrer olanı tek bir yapıya indirdik)
    with st.container(border=True):
        st.markdown(f"""
        💡 **Yapay Zeka Raporu:** {secili_ilce} bölgesi için son veriler incelendiğinde, 
        anlık risk faktörünün tepe noktasına saat **{datetime.now().strftime('%H:%M')}** itibariyle 
        ulaştığı tespit edilmiştir. Meteorolojik ısınma eğrisi ve sensör telemetrileri yakından izlenmektedir.
        """)

# ==============================================================================
# 3. SEKME: SİSTEM GÜNLÜK KAYITLARI
# ==============================================================================
with sekme_veritabani:
    st.subheader("📋 Yapay Zeka Komuta & Sistem Günlük Kayıtları (System Logs)")
    st.caption("ŞAHİN asistanının ve saha operatörlerinin sisteme işlediği anlık aksiyon veri tabanı.")
    
    if st.session_state.veri_log:
        df_log = pd.DataFrame(st.session_state.veri_log)
        st.dataframe(
            df_log, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Zaman": st.column_config.TextColumn("⏰ Zaman Damgası"),
                "İlçe": st.column_config.TextColumn("📍 Görev Bölgesi"),
                "Risk": st.column_config.TextColumn("🔥 Hesaplanan Risk"),
                "Aksiyon": st.column_config.TextColumn("🚒 Saha Aksiyonu"),
                "Durum": st.column_config.TextColumn("🚨 Statü")
            }
        )
        if st.button("🗑️ Log Ekranını Temizle", key="clear_logs"):
            st.session_state.veri_log = []
            st.rerun()
    else:
        st.info("ℹ️ Sistemde kayıtlı herhangi bir günlük kaydı bulunmamaktadır.")

# ==============================================================================
# 4. SEKME: GÖNÜLLÜLÜK VE DOĞA SEVGİSİ
# ==============================================================================
    with sekme_gonullu:
     st.markdown("### 💚 Haydi Umut Ol! Doğa ve Gönüllülük Seferberliği")
     st.markdown("<p style='color: #94a3b8;'>Yangın tehlikelerine karşı sadece teknolojiyle değil, toplumsal dayanışmayla da savaşıyoruz. Geleceğe nefes olmak için aşağıdaki aksiyonlara katılabilirsiniz.</p>", unsafe_allow_html=True)
    
    g_col1, g_col2, g_col3 = st.columns(3)
    g_col1.metric("🌲 Toplam Bağışlanan Fidan", "4,218 Adet", "+120 Bugün")
    g_col2.metric("🤝 Aktif Şanlıurfa Gönüllüsü", "846 Kişi", "+14 Bu Hafta")
    g_col3.metric("🏫 Yapılan Farkındalık Eğitimi", "18 Seminer", "AFAD Koordinasyonlu")
    
    st.write("---")
    col_card1, col_card2 = st.columns(2, gap="large")

    with col_card1:
        with st.container(border=True):
            st.markdown("<h4 style='color:#00C853; margin-top:0;'>🌲 Yeşil Şanlıurfa Fidan Bağışı Kampanyası</h4>", unsafe_allow_html=True)
            st.write("Yapay zekanın yüksek risk veya hasar tespit ettiği bölgelerin yeniden ağaçlandırılması için fidan bağışında bulunabilirsiniz.")
            st.markdown("<small style='color:#888;'><b>SMS ile Destek:</b> FİDAN yazıp 1866'ya göndererek OGEM-VAK'a destek olabilirsiniz.</small>", unsafe_allow_html=True)
            st.write("")
            if st.button("🌱 Fidan Bağışında Bulun (Simüle Et)", use_container_width=True, key="fidan_bagis_btn"):
                st.balloons()
                st.success("Harika! Geleceğe nefes olmak adına fidan bağışı simülasyonu tetiklendi! 🌱")

    with col_card2:
        with st.container(border=True):
            st.markdown("<h4 style='color:#00838F; margin-top:0;'>🤝 Bölgesel Doğa ve Yangın Gönüllüsü Ol</h4>", unsafe_allow_html=True)
            st.write("Şanlıurfa ve çevresinde olası acil durumlarda ekiplere lojistik, erzak ve farkındalık desteği sağlamak için AFAD gönüllü ağına katılın.")
            st.markdown("<small style='color:#888;'>Saha koordinasyon ekipleriyle anlık iletişim ve hazırlık eğitimleri.</small>", unsafe_allow_html=True)
            st.write("")
            if st.button("🤝 Gönüllü Kayıt Formunu Gönder", use_container_width=True, key="gonullu_kayit_btn"):
                st.toast("Gönüllü kaydınız Şanlıurfa Yerel AFAD Gönüllü Veritabanına işlendi!", icon="🤝")
                st.info("Tebrikler! Sistem sorumluları sizinle en kısa sürede iletişime geçecektir.")

# ==============================================================================
# 5. SEKME: LoRA YÖNETİM PANELİ
# ==============================================================================
    with sekme_lora:
     st.subheader("🦅 ŞAHİN Yapay Zeka LoRA Adaptör Yönetimi")
    st.caption("ŞAHİN v2.5 modeline yeni yangın senaryoları öğretmek için LoRA ağırlıklarını yükleyin, eğitin ve kontrol edin.")
    st.write("---")
    
    col_lora1, col_lora2 = st.columns([1, 1], gap="large")
    
    with col_lora1:
        with st.container(border=True):
            st.markdown("<small style='color: #64748b; font-weight: bold;'>🤖 MEVCUT STATÜ</small>", unsafe_allow_html=True)
            st.markdown("### Aktif LoRA Adaptörü")
            st.markdown(f"<h3 style='color: #00f2fe; font-family: monospace; margin:0;'>✨ {st.session_state.aktif_lora}</h3>", unsafe_allow_html=True)
        
        st.write("")
        with st.container(border=True):
            st.markdown("<h4 style='color: #3b82f6; margin-top:0;'>⚙️ İnce Ayar Parametreleri</h4>", unsafe_allow_html=True)
            
            st.markdown("**1. LoRA Sıralaması / Matris Genişliği ($r$):**")
            lora_r = st.slider("", 4, 64, 16, step=4, key="sl_r", label_visibility="collapsed")
            
            st.markdown("**2. LoRA Ölçeklendirme Katsayısı ($\\alpha$):**")
            lora_alpha = st.slider("", 8, 128, 32, step=8, key="sl_a", label_visibility="collapsed")
            
            st.markdown("**3. Eğitim Dönemi (Epoch):**")
            epochs = st.number_input("", min_value=1, max_value=10, value=3, step=1, key="num_ep", label_visibility="collapsed")
            
            st.markdown("**4. Hedef Eğitim Veri Kümesi (Dataset Path):**")
            dataset_name = st.text_input("", value="sanliurfa_yangin_prosedurleri_v1", key="txt_data", label_visibility="collapsed")
            
            st.write("")
            if st.button("🚀 İNCE AYAR EĞİTİMİNİ BAŞLAT", use_container_width=True, type="primary"):
                ilerleme_bari = st.progress(0, text="Taban model yükleniyor...")
                import time
                time.sleep(1)
                ilerleme_bari.progress(30, text="Veri kümesi LoRA matrislerine enjekte ediliyor...")
                time.sleep(1.5)
                ilerleme_bari.progress(70, text="Ağırlıklar optimize ediliyor (Loss: 0.24)...")
                time.sleep(1)
                ilerleme_bari.progress(100, text="Eğitim Tamamlandı!")
                
                model_id = f"lora_shn_r{lora_r}_a{lora_alpha}_{datetime.now().strftime('%d%m_%H%M')}"
                yeni_kayit = {
                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Model Adı": model_id,
                    "Rank (r)": lora_r,
                    "Alpha": lora_alpha,
                    "Epoch": epochs,
                    "Veri Kümesi": dataset_name,
                    "Durum": "🟢 BAŞARILI"
                }
                
                st.session_state.lora_gecmisi.append(yeni_kayit)
                with open(os.path.join(LOG_DIR, "lora_history.json"), "w") as f:
                    json.dump(st.session_state.lora_gecmisi, f, indent=4)
                    
                with open(os.path.join(LORA_DIR, f"{model_id}.safetensors"), "w") as f:
                    f.write("LORA_DUMMY_WEIGHTS")
                    
                st.success(f"🎉 {model_id} başarıyla eğitildi!")
                st.rerun()

    with col_lora2:
        with st.container(border=True):
            st.markdown("<h4 style='color: #eab308; margin-top:0;'>📂 Kayıtlı Kontrol Noktaları</h4>", unsafe_allow_html=True)
            modeller = [f for f in os.listdir(LORA_DIR) if f.endswith(".safetensors")]
            modeller_listesi = ["Yok (Taban Model)"] + [m.replace(".safetensors", "") for m in modeller]
            
            st.markdown("**Sisteme Enjekte Edilecek Adaptör Seçimi:**")
            secilen_lora = st.selectbox("", modeller_listesi, key="sb_lora", label_visibility="collapsed")
            
            st.write("")
            if st.button("🔌 SEÇİLEN ADAPTÖRÜ ÇATI MODELE BAĞLA", use_container_width=True):
                st.session_state.aktif_lora = secilen_lora
                st.toast(f"🔗 {secilen_lora} aktif edildi!", icon="🤖")
                st.rerun()
            
        st.write("")
        with st.container(border=True):
            st.markdown("<h4 style='color: #10b981; margin-top:0;'>📜 LoRA Eğitim Günlükleri</h4>", unsafe_allow_html=True)
            if st.session_state.lora_gecmisi:
                df_lora = pd.DataFrame(st.session_state.lora_gecmisi)
                st.dataframe(df_lora, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ Henüz sistemde kayıtlı bir LoRA eğitim günlüğü bulunmuyor.")
