import requests
import pandas as pd
import streamlit as st
import os
import json
import asyncio
import numpy as np
import folium
import warnings
from datetime import datetime, timedelta
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh
import edge_tts
import base64


warnings.filterwarnings("ignore")


# ================= SESSION STATE =================

if 'sahin_konustu_mu' not in st.session_state:
    st.session_state.sahin_konustu_mu = False

if "son_ses" not in st.session_state:
    st.session_state.son_ses = ""

if "son_veri_zamani" not in st.session_state:
    st.session_state.son_veri_zamani = datetime.now() - timedelta(seconds=10)


if "gecmis_risk" not in st.session_state:
    st.session_state.gecmis_risk = [
        {"Saat": "17:00", "Merkez Bölge Risk (%)": 35, "Saha Genel Risk (%)": 50},
        {"Saat": "17:15", "Merkez Bölge Risk (%)": 40, "Saha Genel Risk (%)": 50},
        {"Saat": "17:30", "Merkez Bölge Risk (%)": 65, "Saha Genel Risk (%)": 50},
        {"Saat": "17:45", "Merkez Bölge Risk (%)": 45, "Saha Genel Risk (%)": 50},
        {"Saat": "18:00", "Merkez Bölge Risk (%)": 27, "Saha Genel Risk (%)": 50}
    ]

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
# ŞAHİN ASYNC SES MOTORU (EDGE-TTS)
# ==============================================================================
def sahin_analiz_et(soru, sicaklik, risk, ilce):
    
    if risk >= 75:
        durum = "KRİTİK"
    elif risk >= 50:
        durum = "ORTA"
    else:
        durum = "DÜŞÜK"
        
    return f"{ilce} bölgesinde risk seviyesi: %{risk}. Durum: {durum}."
async def amain(metin) -> bytes:
    communicate = edge_tts.Communicate(metin, "tr-TR-AhmetNeural", rate="+0%")
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
    return audio_bytes
    
def sahin_uyar():
    # Kritik bir durumda tetiklenecek alarm sesi
    if os.path.exists("alarm.mp3"):
        st.audio("alarm.mp3", format='audio/mp3', autoplay=True)
def sahin_seslendir(cevap_metni):

    if st.session_state.get("son_ses","") == cevap_metni:
        return

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        ses_verisi = loop.run_until_complete(
            amain(cevap_metni)
        )

        loop.close()

        b64_ses = base64.b64encode(ses_verisi).decode("utf-8")

        ses_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64_ses}">
        </audio>
        """

        st.markdown(
            ses_html,
            unsafe_allow_html=True
        )

        st.session_state.son_ses = cevap_metni


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
def log_kaydet(ilce, risk_val, seviye_str, aksiyon): 
    yeni_log = {
        "Zaman": datetime.now().strftime("%H:%M:%S"),
        "İlçe": ilce,
        "Risk": f"%{risk_val}",
        "Aksiyon": aksiyon,
        "Durum": seviye_str  # 'durum_str' yerine 'seviye_str' 
    }
    st.session_state.veri_log.append(yeni_log)
    if len(st.session_state.veri_log) > 50:
        st.session_state.veri_log = st.session_state.veri_log[-50:]


# ==============================================================================
# ŞAHİN RAPORLAMA FONKSİYONU 
# ==============================================================================

def sahin_raporla(ilce_adi, risk, sicaklik, seviye):
    rapor_metni = (
        f"Şahin durum raporu. {ilce_adi} bölgesinde anlık sensör verileri; "
        f"sıcaklık {sicaklik} derece, risk seviyesi yüzde {risk}. "
        f"Saha durumu şu an {seviye} olarak değerlendirilmiştir."
    )
    st.success(f"🤖 {rapor_metni}")
    sahin_seslendir(rapor_metni)

# ==============================================================================
# POPOVER KISMI 
# ==============================================================================

if "risk" not in st.session_state:
    st.session_state.risk = 0
    st.session_state.sicaklik = 0
    st.session_state.seviye = "Bilinmiyor"
    st.session_state.ilce_adi = "Belirsiz"

with st.popover(" "):
    st.subheader("📡 ŞAHİN Kontrol Merkezi")
    
    if st.button("📢 Güncel Durumu Seslendir"):
        # Hata almamak için session_state'den çekim
        metin = (f"Şahin durum raporu. {st.session_state.ilce_adi} bölgesinde anlık veriler; "
                 f"sıcaklık {st.session_state.sicaklik} derece, risk seviyesi yüzde {st.session_state.risk}. "
                 f"Durum: {st.session_state.seviye}.")
        
        st.success(f"🤖 {metin}")
        sahin_seslendir(metin)
        
    if st.button("📄 Detaylı Rapor"):
        rapor = f"--- ŞAHİN RAPORU ---\nBölge: {st.session_state.ilce_adi}\nRisk: %{st.session_state.risk}\nSıcaklık: {st.session_state.sicaklik}C\nDurum: {st.session_state.seviye}"
        st.text_area("Rapor:", value=rapor, height=150)
        st.download_button("💾 İndir", rapor, "rapor.txt")
# ==============================================================================
# CSS stil tanımları
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


if 'ilce_adi' not in st.session_state:
    st.session_state.ilce_adi = "Haliliye"
if 'gecmis_risk' not in st.session_state:
    st.session_state.gecmis_risk = []
if 'veri_log' not in st.session_state:
    st.session_state.veri_log = []

# İlçe seçimini yap
goruntuleme_modu = st.radio("📡", ["📍 Manuel", "🔄 Otomatik"], horizontal=True, key="mod")
if goruntuleme_modu == "📍 Manuel":
    ilce_adi = st.selectbox("📍", list(ILCELER.keys()), key="secim")
else:
    ilce_adi = list(ILCELER.keys())[int(datetime.now().timestamp() / 15) % len(ILCELER)]
    st.info(f"🔄 Otomatik Takip Modu: {ilce_adi}")

# Değişkenleri global hale getir
st.session_state.ilce_adi = ilce_adi
koordinat = ILCELER[ilce_adi]

# ==============================================================================
# 1. HESAPLAMA BLOĞU 
# ==============================================================================
np.random.seed(int(datetime.now().timestamp()) + len(ilce_adi))

sicaklik = round(float(koordinat["taban_sicaklik"] + np.random.uniform(-0.3, 0.4)), 1)
nem = round(float(koordinat["taban_nem"] + np.random.uniform(-1.0, 1.0)), 1)
ruzgar = round(float(koordinat["taban_ruzgar"] + np.random.uniform(-0.5, 0.5)), 1)

if koordinat.get("senaryo") == "critical":
    risk = int(np.random.randint(82, 96))
    seviye, ikon = "KRİTİK", "🚨"
elif koordinat.get("senaryo") == "warning":
    risk = int(np.random.randint(52, 68))
    seviye, ikon = "YÜKSEK", "⚠️"
else:
    risk = int(max(10, min((sicaklik * 1.0) - (nem * 0.5) + (ruzgar * 0.3), 44)))
    seviye, ikon = "DÜŞÜK", "✅"

# 3. TEK BİR BANNER BLOĞU 
st.markdown("""
<style>
.main-banner { background: #0f172a; padding: 20px; border-radius: 12px; display: flex; justify-content: space-between; margin-bottom: 20px; color: white; border: 1px solid #334155; }
.data-box { display: flex; align-items: center; gap: 10px; }
.value { font-weight: bold; font-size: 18px; color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="main-banner">
    <div class="data-box"><div>📍</div><div>Bölge<br><span class="value">{ilce_adi}</span></div></div>
    <div class="data-box"><div>{ikon}</div><div>Risk<br><span class="value">%{risk}</span></div></div>
    <div class="data-box"><div>⚙️</div><div>Durum<br><span class="value">{seviye}</span></div></div>
   <div class="data-box"><div>🚒</div><div>Müdahale Birimi<br><span class="value">{koordinat.get('itfaiye', 'Saha Ekibi')}</span>
</div></div></div>
""", unsafe_allow_html=True)



# ==============================================================================

simdi = datetime.now().strftime("%H:%M:%S")
if st.session_state.son_veri_zamani != simdi:

    log_kaydet(ilce_adi, risk, seviye, "Sistem Taraması")

    yeni_veri = {
        "Saat": simdi,
        "Merkez Bölge Risk (%)": risk,
        "Saha Genel Risk (%)": 50
    }

    st.session_state.gecmis_risk.append(yeni_veri)

    # Maksimum 50 kayıt tut
    if len(st.session_state.gecmis_risk) > 50:
        st.session_state.gecmis_risk.pop(0)

    st.session_state.son_veri_zamani = simdi

# INTERNET KONTROLÜ
if not internet_var_mi():
    st.warning("⚠️ İnternet yok! Önbellek verileri kullanılıyor.")
    kaynak = "💾 Önbellek"
else:
    kaynak = "📡 Canlı"


# ==============================================================================
# 🚀 PROFEOSYONEL OGM KOMUTA BANNERI VE KONTROL PANELİ
# ==============================================================================

# İnternet kontrolü var  sadece durumu belirltmek için
kaynak = "📡 Canlı" if internet_var_mi() else "💾 Önbellek"


# Renk tanımları 
if risk >= 75:
    neon_renk = "#ef4444"
elif risk >= 45:
    neon_renk = "#f59e0b"
else:
    neon_renk = "#3b82f6"

st.sidebar.success(f"Bağlantı: {kaynak}")

#==============================================================================
#ŞAHİN ROBOT STİLİ VE GÖRSELİ

st.markdown("""
<style>
@keyframes spin { 100% { transform: rotate(360deg); } }
.sahin-gorsel {
    position: fixed; bottom: 30px; right: 30px; z-index: 999;
    width: 110px; height: 110px; border-radius: 50%;
    background: #0f172a; border: 3px solid #3b82f6;
    display: flex; align-items: center; justify-content: center;
    font-size: 30px; animation: spin 10s linear infinite;
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.6);
}

/* 2. Görünmez Buton (Üstüne Binen Katman) */
.sahin-buton {
    position: fixed; bottom: 30px; right: 30px; z-index: 1000;
    width: 70px; height: 70px; opacity: 0; cursor: pointer;
}
</style>

<div class="sahin-gorsel">🦅</div>
""", unsafe_allow_html=True)

# 1. HESAPLAMA BLOĞUNUNDAN SONRA GELEMLİ 
st.session_state.ilce_adi = ilce_adi
st.session_state.risk = risk
st.session_state.sicaklik = sicaklik
st.session_state.seviye = seviye

# 2. ŞAHİN BUTON VE MENÜ BLOĞU
st.markdown("""
<style>
/* 1. Kendi logon zaten dönüyor, biz popover'ı onun üzerine çiviliyoruz */
[data-testid="stPopover"] {
    position: fixed; bottom: 30px; right: 30px; 
    z-index: 1002; width: 110px; height: 110px; opacity: 0;
}
</style>
""", unsafe_allow_html=True)

with st.popover(" "): 
    st.subheader("📡 ŞAHİN Kontrol Merkezi")
    
    # 📢 Sesli Rapor
    if st.button("📢 Güncel Durumu Seslendir", key="btn_sahin_ses"):
        rapor = (f"Şahin durum raporu. {st.session_state.ilce_adi} bölgesinde anlık veriler; "
                 f"sıcaklık {st.session_state.sicaklik} derece, risk seviyesi yüzde {st.session_state.risk}. "
                 f"Durum: {st.session_state.seviye}.")
        st.success(f"🤖 {rapor}")
        sahin_seslendir(rapor)

    st.write("---")

    # 📄 Rapor İndirme
    if st.button("📄 Detaylı Rapor", key="btn_sahin_rapor"):
        rapor_txt = f"--- ŞAHİN RAPORU ---\nBölge: {st.session_state.ilce_adi}\nRisk: %{st.session_state.risk}\nSıcaklık: {st.session_state.sicaklik}C\nDurum: {st.session_state.seviye}"
        st.text_area("Rapor:", value=rapor_txt, height=150)
        st.download_button("💾 İndir", rapor_txt, "rapor.txt")
# ==============================================================================
# CANLI AKSİYON VE TERMAL VERİ AKIŞ PANELİ
# ==============================================================================
st.markdown("### 🚨 Saha Koordinasyon Merkezi")
st.info(f"📍 Aktif Gözlem Bölgesi: **{ilce_adi}** | Durum: **{seviye}**")

# DURUM GÖSTERGELERİ
col_op1, col_op2, col_op3 = st.columns(3)
with col_op1:
    st.metric("🚨 Operasyon Durumu", seviye, delta="Aktif Takip")
with col_op2:
    st.metric("🚒 Hazır İtfaiye Filosu", "14 Araç / 42 Personel", delta="Tam Kapasite", delta_color="normal")
with col_op3:
    st.metric("🛸 İHA / Drone Keşif", "ŞAHİN-1 Havada", delta="Anlık Veri Aktif", delta_color="normal")

# Alt Kısım: Termal Veri Matrisi ve Telsiz Akışı
col_main1, col_main2 = st.columns([5, 4])


# ==============================================================================
# 🏢 YENİ NESİL OGM KOMUTA BANNERI 
# ==============================================================================


# ROBOT VE HARİTA COLUMNS
c1, c2 = st.columns([1, 1])
ses = None 

with c1:
    st.markdown("""
<style>
.sahin-assistant {
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 70px;
    height: 70px;
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 2px solid #3b82f6;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #3b82f6;
    font-size: 28px;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
    cursor: pointer;
    z-index: 9999;
    transition: transform 0.3s ease;
}
.sahin-assistant:hover {
    transform: scale(1.1);
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
.akis-paneli {
    height: 440px;
    background-color: #0c1220;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #1e3a8a;
    color: #e2e8f0;
    font-family: 'Roboto Mono', monospace;
    font-size: 15px; /* Yazıları biraz büyüttük */
    overflow-y: auto;
}
.telsiz-mesaj {
    text-align: left;
    margin-bottom: 12px;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 8px;
    line-height: 1.4;
}
/* Renk Kodları */
.merkez { color: #f59e0b; font-weight: bold; } /* Turuncu: Merkez */
.sistem { color: #3b82f6; font-weight: bold; } /* Mavi: Sistem */
.uyari { color: #ef4444; font-weight: bold; }  /* Kırmızı: Uyarı */
.bilgi { color: #10b981; font-weight: bold; }  /* Yeşil: Bilgi */
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# OPERASYON SEKME (Gövde)
# ==============================================================================

    
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

# ==============================================================================
# 🚒 HARİTA VE TELSİZ KOMUTA PANELİ 
# ==============================================================================

# Harita ve Telsiz için kolon yapısı 
col_harita, col_telsiz = st.columns([2, 1])
def haritayi_olustur_sanliurfa(ilceler_dict):
    m = folium.Map(location=[37.1674, 38.7952], zoom_start=10)
    for isim, veri in ilceler_dict.items():
        renk = "red" if veri["senaryo"] == "critical" else "orange" if veri["senaryo"] == "warning" else "green"
        folium.Marker(
            [veri["lat"], veri["lon"]],
            popup=f"<b>{isim}</b>",
            icon=folium.Icon(color=renk, icon="info-sign")
        ).add_to(m)
    return m

# Her değişkeni locals() işle alıyoruz böylece hata oluşmaz
sicaklik = locals().get('sicaklik', 0)
nem = locals().get('nem', 0)
duman = locals().get('duman', 0)


sicaklik_delta = f"<span style='color:#ef4444;'>🔥 KRİTİK</span>" if sicaklik > 38 else f"<span style='color:#64748b;'>NORMAL</span>"
nem_delta = f"<span style='color:#ef4444;'>⚠️ DÜŞÜK</span>" if nem < 12 else f"<span style='color:#10b981;'>OPTIMAL</span>"
duman_delta = f"<span style='color:#ef4444;'>🚨 ANOMALİ</span>" if duman > 200 else f"<span style='color:#10b981;'>TEMİZ</span>"

# HARİTA VE TELSİZ YERLEŞİMİ

col_harita, col_telsiz = st.columns([1, 1])

with col_harita:
    st.markdown("### 🗺️ Saha Operasyon Haritası")
    m = haritayi_olustur_sanliurfa(ILCELER)
    st_folium(m, height=500, use_container_width=True, key="sanliurfa_map")


with col_telsiz:
    st.markdown("### 📻 Telsiz Akışı")
    
    # Listeyi tanımlama
    telsiz_mesajlari = [
        f"[{datetime.now().strftime('%H:%M:%S')}] {ilce_adi} devriyesi aktif.",
        f"[{datetime.now().strftime('%H:%M:%S')}] Sensörler stabil.",
        "[MERKEZ] Hava desteği hazır.",
        "[SİSTEM] Akçakale taraması başladı.",
        "[BİLGİ] Meteorolojik veri güncellendi.",
        "[UYARI] Ceylanpınar sinyal zayıf.",
        "[MERKEZ] Raporları iletin.",
        "[SİSTEM] Senkronizasyon tamam."
    ]
    
    # Mesajları döngü ile işleyip HTML içine ekleme
    mesajlar_html = ""
    for msg in telsiz_mesajlari:
        # Renkleme ve stil ekleme
        renkli_msg = msg
        if "[MERKEZ]" in renkli_msg: renkli_msg = renkli_msg.replace("[MERKEZ]", "<span class='merkez'>[MERKEZ]</span>")
        if "[SİSTEM]" in renkli_msg: renkli_msg = renkli_msg.replace("[SİSTEM]", "<span class='sistem'>[SİSTEM]</span>")
        if "[UYARI]" in renkli_msg: renkli_msg = renkli_msg.replace("[UYARI]", "<span class='uyari'>[UYARI]</span>")
        if "[BİLGİ]" in renkli_msg: renkli_msg = renkli_msg.replace("[BİLGİ]", "<span class='bilgi'>[BİLGİ]</span>")
        
        # İşlenmiş mesajı HTML bloğuna ekleme
        mesajlar_html += f"<div class='telsiz-mesaj' style='margin-bottom: 8px;'>{renkli_msg}</div>"
    
    # Paneli render etme
    st.markdown(f"""
        <div class="akis-paneli">
            <div style='display: flex; flex-direction: column; align-items: flex-start; justify-content: flex-start; padding: 10px;'>
                {mesajlar_html}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
 


# ==============================================================================
# OPERASYON SEKME DÜZENİ
# ==============================================================================
sekme_operasyon, sekme_grafik, sekme_veritabani, sekme_lora, sekme_gonullu = st.tabs([
    "🚒 Canlı Aksiyon & Saha Koordinasyon Merkezi",
    "📈 Geçmiş Risk Analizi",
    "📋 Sistem Günlük Kayıtları",
    "🤖 LoRA Kontrol & Eğitim",
    "🌱 Haydi Umut Ol! (Doğa & Gönüllülük)"
])
with sekme_operasyon:
         col_sol, col_sag = st.columns([2, 1], gap="medium")
with sekme_operasyon:
    st.markdown("### 🚒 Canlı Aksiyon & Saha Koordinasyon Merkezi")
    
    col_sol, col_sag = st.columns([2, 1], gap="medium")
    
    with col_sol:   
             
        # SESLİ UYARI MANTIĞI 
        if seviye == "KRİTİK": 
         st.error("🚨 KRİTİK RİSK ALGILANDI!")
    sahin_uyar()
    st.markdown(f"""
        <div style="width: 100%; border: 2px solid #333; padding: 20px; border-radius: 15px; background-color: #0e1117;">
            <h4 style="color: #ff4b4b;">🔴 CANLI TERMAL VE SENSÖR MATRİSİ</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div><small>Sıcaklık</small><br><strong>{sicaklik} °C</strong></div>
                <div><small>Duman</small><br><strong>{duman} PPM</strong></div>
                <div><small>Risk Seviyesi</small><br><strong style="color: #ff4b4b;">{seviye}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
          
        
# ==============================================================================
# 2. SEKME: GRAFİK ANALİZLERİ
# ==============================================================================
with sekme_grafik:

    secili_ilce = st.session_state.get("ilce_adi", "Haliliye")

    st.markdown(f"### 📈 {secili_ilce} İlçesi Detaylı Risk Analiz Grafikleri")

    if st.session_state.gecmis_risk:

        df_grafik = pd.DataFrame(st.session_state.gecmis_risk)

        if "Saat" in df_grafik.columns:
            df_grafik = df_grafik.set_index("Saat")

        # Sadece sayısal sütunları al
        df_grafik = df_grafik.select_dtypes(include=["number"])

        st.line_chart(df_grafik, use_container_width=True)

    else:
        st.warning("Henüz grafik için yeterli veri yok.")

    with st.container(border=True):
        st.markdown(f"""
💡 **Yapay Zeka Raporu:** {secili_ilce} bölgesi için son veriler incelendiğinde,
anlık risk faktörünün tepe noktasına saat **{datetime.now().strftime('%H:%M')}**
itibariyle ulaştığı tespit edilmiştir.
Meteorolojik ısınma eğrisi ve sensör telemetrileri ŞAHİN tarafından yakından izlenmektedir.
""")
# ==============================================================================
# 3. SEKME: SİSTEM GÜNLÜK KAYITLARI
# ==============================================================================
with sekme_veritabani:
    st.subheader("📋 Yapay Zeka Komuta & Sistem Günlük Kayıtları (System Logs)")
    st.caption("ŞAHİN asistanının ve saha operatörlerinin sisteme işlediği anlık aksiyon veri tabanı.")
    
    # 'veri_log' session_state içinde yoksa hata vermemesi için güvenli kontrol
    logs = st.session_state.get("veri_log", [])
    
    if logs:
        df_log = pd.DataFrame(logs)
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
# 4. SEKME: LoRA YÖNETİM PANELİ
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
            if st.session_state.get("lora_gecmisi"):
                df_lora = pd.DataFrame(st.session_state.lora_gecmisi)
                st.dataframe(df_lora, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ Henüz sistemde kayıtlı bir LoRA eğitim günlüğü bulunmuyor.")        
# ==============================================================================
# 5. SEKME: GÖNÜLLÜLÜK 
# ==============================================================================
with sekme_gonullu:
    st.markdown("### 💚 Haydi Umut Ol! Doğa ve Gönüllülük Seferberliği")
    st.markdown("<p style='color: #94a3b8;'>Yangın tehlikelerine karşı sadece teknolojiyle değil, toplumsal dayanışmayla da savaşıyoruz. Geleceğe nefes olmak için aşağıdaki aksiyonlara katılabilirsiniz.</p>", unsafe_allow_html=True)
    
    # Tüm elemanlar 'with sekme_gonullu' bloğunun içine al
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
            if st.button("🌱 Fidan Bağışında Bulun", use_container_width=True, key="fidan_bagis_btn"):
                st.balloons()
                st.success("Harika! Geleceğe nefes olmak adına fidan bağışı gerçekleşti! 🌱")

    with col_card2:
        with st.container(border=True):
            st.markdown("<h4 style='color:#00838F; margin-top:0;'>🤝 Bölgesel Doğa ve Yangın Gönüllüsü Ol</h4>", unsafe_allow_html=True)
            st.write("Şanlıurfa ve çevresinde olası acil durumlarda ekiplere lojistik, erzak ve farkındalık desteği sağlamak için AFAD gönüllü ağına katılın.")
            st.markdown("<small style='color:#888;'>Saha koordinasyon ekipleriyle anlık iletişim ve hazırlık eğitimleri.</small>", unsafe_allow_html=True)
            st.write("")
            if st.button("🤝 Gönüllü Kayıt Formunu Gönder", use_container_width=True, key="gonullu_kayit_btn"):
                st.toast("Gönüllü kaydınız Şanlıurfa Yerel AFAD Gönüllü Veritabanına işlendi!", icon="🤝")
                st.info("Tebrikler! Sistem sorumluları sizinle en kısa sürede iletişime geçecektir.")


