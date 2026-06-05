import streamlit as st
import pandas as pd
import numpy as np
import folium
import warnings
import base64  # Ses dosyasını HTML içine gömmek için
from gtts import gTTS  # ŞAHİN'in ses motoru
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# ==============================================================================
# SAYFA AYARLARI
# ==============================================================================
st.set_page_config(
    page_title="AFAD Orman Yangını Komuta Merkezi",
    page_icon="🚨",
    layout="wide"
)

# Haritayı her 15 saniyede bir otomatik yenilemek için
st_autorefresh(interval=15000, key="canli_veri_akis_dongusu")


# ==============================================================================
# ŞAHİN SES MOTORU FONKSİYONU
# ==============================================================================
def sahin_seslendir(metin):
    """ŞAHİN'in ürettiği yapay zeka özetini sese dönüştürür ve otomatik oynatır."""
    try:
        # Metni temizle ve ses dosyasına dönüştür
        tts = gTTS(text=metin, lang='tr', slow=False)
        audio_file = "sahin_ses.mp3"
        tts.save(audio_file)

        # Ses dosyasını oku ve base64 formatına çevir (Streamlit içinde oto-oynatma için en kararlı yol)
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode()

        # HTML5 Audio tag'i ile otomatik oynatılmasını sağla (autoplay)
        audio_html = f"""
            <audio autoplay style="display:none;">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)
    except Exception as e:
        pass  # Ses motorunda oluşabilecek anlık kesintileri sisteme yansıtma


# ==============================================================================
# MODERN CSS TASARIMLARI
# ==============================================================================
st.markdown("""
<style>
.sahin-robot-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #111827, #1f2937);
    padding: 30px;
    border-radius: 20px;
    border: 2px solid #3b82f6;
    box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
    text-align: center;
    height: 480px;
}
.sahin-core {
    width: 100px;
    height: 100px;
    background: radial-gradient(circle, #00f2fe 0%, #4facfe 100%);
    border-radius: 50%;
    box-shadow: 0 0 30px #00f2fe;
    animation: pulse 2s infinite alternate;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 45px;
    margin-bottom: 15px;
}
@keyframes pulse {
    0% { transform: scale(0.92); box-shadow: 0 0 15px #00f2fe; }
    100% { transform: scale(1.08); box-shadow: 0 0 35px #00f2fe; }
}
.sahin-status {
    color: #00f2fe;
    font-family: 'Courier New', Courier, monospace;
    font-weight: bold;
    margin-top: 15px;
    font-size: 14px;
    letter-spacing: 1px;
}
.weather-card-wide {
    background: linear-gradient(145deg, #1e293b, #0f172a);
    border-radius: 16px;
    padding: 15px 20px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
    border: 1px solid #334155;
    text-align: center;
    margin-top: 15px;
    transition: all 0.2s ease;
}
.weather-card-wide:hover {
    border-color: #3b82f6;
    transform: translateY(-2px);
}
.card-title-wide {
    color: #94a3b8;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.card-value-wide {
    color: #f8fafc;
    font-size: 24px;
    font-weight: 700;
}
.card-sub-wide {
    color: #38bdf8;
    font-size: 11px;
    margin-top: 2px;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ŞANLIURFA İLÇE METEOROLOJİ VERİTABANI
# ==============================================================================
ILCELER = {
    "Haliliye": {"lat": 37.1650, "lon": 38.8300, "itfaiye": "Haliliye Acil Müdahale İstasyonu", "taban_sicaklik": 33.0,
                 "taban_nem": 18.0, "taban_ruzgar": 9.8, "yon": "➡️ Doğu", "senaryo": "safe"},
    "Karaköprü": {"lat": 37.1950, "lon": 38.8150, "itfaiye": "Karaköprü Merkez İtfaiye Amirliği",
                  "taban_sicaklik": 32.5, "taban_nem": 19.0, "taban_ruzgar": 10.2, "yon": "↗️ Kuzeydoğu",
                  "senaryo": "safe"},
    "Eyyübiye": {"lat": 37.1400, "lon": 38.8000, "itfaiye": "Eyyübiye Sanayi Bölgesi İtfaiyesi", "taban_sicaklik": 36.2,
                 "taban_nem": 15.0, "taban_ruzgar": 16.0, "yon": "➡️ Doğu", "senaryo": "warning"},
    "Akçakale": {"lat": 36.7111, "lon": 38.9469, "itfaiye": "Akçakale Sınır İtfaiye Amirliği", "taban_sicaklik": 42.2,
                 "taban_nem": 8.0, "taban_ruzgar": 24.5, "yon": "↗️ Kuzeydoğu", "senaryo": "critical"},
    "Harran": {"lat": 36.8617, "lon": 39.0306, "itfaiye": "Harran İtfaiyesi", "taban_sicaklik": 35.0, "taban_nem": 15.0,
               "taban_ruzgar": 13.0, "yon": "➡️ Doğu", "senaryo": "safe"},
    "Birecik": {"lat": 37.0315, "lon": 37.9782, "itfaiye": "Birecik Sahil İtfaiye Grubu", "taban_sicaklik": 34.1,
                "taban_nem": 16.0, "taban_ruzgar": 8.5, "yon": "↘️ Güneydoğu", "senaryo": "safe"},
    "Bozova": {"lat": 37.3622, "lon": 38.4839, "itfaiye": "Bozova Merkez Müdahale Ekibi", "taban_sicaklik": 32.8,
               "taban_nem": 20.0, "taban_ruzgar": 12.0, "yon": "↖️ Kuzeybatı", "senaryo": "safe"},
    "Ceylanpınar": {"lat": 36.8411, "lon": 40.0428, "itfaiye": "Ceylanpınar TİGEM İtfaiye Merkezi",
                    "taban_sicaklik": 43.0, "taban_nem": 7.0, "taban_ruzgar": 28.0, "yon": "➡️ Doğu",
                    "senaryo": "critical"},
    "Halfeti": {"lat": 37.2475, "lon": 37.8697, "itfaiye": "Halfeti İtfaiye Müfrezesi", "taban_sicaklik": 32.2,
                "taban_nem": 21.0, "taban_ruzgar": 7.8, "yon": "⬇️ Güney", "senaryo": "safe"},
    "Hilvan": {"lat": 37.5856, "lon": 38.9592, "itfaiye": "Hilvan Müdahale İstasyonu", "taban_sicaklik": 31.8,
               "taban_nem": 22.0, "taban_ruzgar": 11.5, "yon": "↖️ Kuzeybatı", "senaryo": "safe"},
    "Siverek": {"lat": 37.7500, "lon": 39.3167, "itfaiye": "Siverek Bölge İtfaiye Amirliği", "taban_sicaklik": 31.0,
                "taban_nem": 24.0, "taban_ruzgar": 13.0, "yon": "⬆️ Kuzey", "senaryo": "safe"},
    "Suruç": {"lat": 36.9764, "lon": 38.4244, "itfaiye": "Suruç İtfaiye Grubu", "taban_sicaklik": 34.5,
              "taban_nem": 16.0, "taban_ruzgar": 10.0, "yon": "➡️ Doğu", "senaryo": "safe"},
    "Viranşehir": {"lat": 37.2353, "lon": 39.7619, "itfaiye": "Viranşehir Organize Sanayi İtfaiyesi",
                   "taban_sicaklik": 35.5, "taban_nem": 13.0, "taban_ruzgar": 12.5, "yon": "↗️ Kuzeydoğu",
                   "senaryo": "safe"}
}

if "manuel_ilce" not in st.session_state:
    st.session_state.manuel_ilce = "Haliliye"

# ==============================================================================
# GÖRÜNTÜLEME MODU SEÇİMİ
# ==============================================================================
goruntuleme_modu = st.radio(
    "📡 İzleme Modu",
    ["📍 Manuel İlçe", "🔄 Otomatik Döngü"],
    horizontal=True,
    key="izleme_modu_secimi"
)

if goruntuleme_modu == "📍 Manuel İlçe":
    ilce_adi = st.selectbox(
        "📍 İlçe Seç",
        list(ILCELER.keys()),
        index=list(ILCELER.keys()).index(st.session_state.manuel_ilce),
        key="manuel_ilce"
    )
else:
    ilce_adi = list(ILCELER.keys())[int(datetime.now().timestamp() / 15) % len(ILCELER)]

koordinat = ILCELER[ilce_adi]

# ==============================================================================
# GERÇEK ZAMANLI TELEMETRİ MOTORU
# ==============================================================================
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

yayilma_yonu = koordinat["yon"]

# ==============================================================================
# DİNAMİK BANNER PANELİ
# ==============================================================================
durum_etiketi = "🎯 OPERATÖR SEÇİMİ" if goruntuleme_modu == "📍 Manuel İlçe" else "📡 OTOMATİK TARAMA"

if risk >= 75:
    seviye, ikon, banner_renk = "KRİTİK", "🚨", "linear-gradient(135deg, #D50000, #FF6D00)"
elif risk >= 45:
    seviye, ikon, banner_renk = "YÜKSEK / RİSKLİ", "⚠️", "linear-gradient(135deg, #FFD600, #FF8F00)"
else:
    seviye, ikon, banner_renk = "DÜŞÜK / GÜVENLİ", "✅", "linear-gradient(135deg, #00C853, #64DD17)"

st.markdown(f"""
<div style="background:{banner_renk}; padding:25px; border-radius:20px; color:white; box-shadow:0 8px 25px rgba(0,0,0,0.25); margin-bottom:20px;">
    <h1>🚨 AFAD ORMAN YANGINI KOMUTA MERKEZİ</h1>
    <h4>{durum_etiketi}</h4>
    <h3>📍 Aktif Bölge: Şanlıurfa / {ilce_adi}</h3>
    <h2>{ikon} Risk Durumu: %{risk} ({seviye})</h2>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# ROBOT PANELİ VE GÜVENLİ HARİTA MİZANPAJI
# ==============================================================================
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("""
    <div class="sahin-robot-container">
        <div class="sahin-core">🦅</div>
        <div style="color: white; font-weight: bold; font-size: 24px;">ŞAHİN v2.5 AI CORE</div>
        <div style="color: #94a3b8; font-size: 14px; margin-top: 5px;">Otonom Risk Değerlendirme Algoritması</div>
        <div class="sahin-status">● CANLI SESLİ ANALİZ VE ASİSTAN MOTORU AKTİF</div>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    m = folium.Map(location=[koordinat["lat"], koordinat["lon"]], zoom_start=11)

    renk = "red" if risk >= 75 else "orange" if risk >= 45 else "green"
    folium.Circle(
        location=[koordinat["lat"], koordinat["lon"]],
        radius=3000,
        color=renk,
        fill=True,
        fill_opacity=0.1,
        tooltip=f"{ilce_adi} Güvenlik Çemberi"
    ).add_to(m)

    folium.Marker(
        [koordinat["lat"], koordinat["lon"]],
        popup=f"AFAD {ilce_adi} İstasyonu",
        tooltip=ilce_adi,
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    st_folium(m, height=480, width=None, key=f"harita_istasyonu_{ilce_adi}", returned_objects=[])

# ==============================================================================
# ALT TELEMETRİ KUTULARI VE ŞAHİN SES ENTEGRASYONU
# ==============================================================================
st.write("---")
st.markdown("### 📊 Real-Time Bölgesel Telemetri ve Analiz Verileri")

# ŞAHİN'in seslendireceği dinamik metin senaryolarını kurguluyoruz
if risk >= 75:
    sahin_metni = f"Dikkat! Şahin yapay zekâ çekirdeği bildiriyor. {ilce_adi} bölgesinde yoğun duman anomalisi saptandı. Yangın riski yüzde {risk} ile kritik seviyededir. Acil müdahale protokolü aktif edildi."
    st.error(
        f"🤖 **ŞAHİN Yapay Zeka Özeti:** 🚨 **DİKKAT:** {ilce_adi} bölgesinde yoğun duman anomalisi ({duman} PPM) saptandı! Yangın riski %{risk}! Acil müdahale protokolü aktif.")
elif risk >= 45:
    sahin_metni = f"Şahin uyarısı. {ilce_adi} bölgesinde meteorolojik şartlar risk sınırında seyrediyor. Hava kalitesi indeksi tehlike arz edebilir. Drone takibi önerilir."
    st.warning(
        f"🤖 **ŞAHİN Yapay Zeka Özeti:** ⚠️ **UYARI:** {ilce_adi} bölgesinde meteorolojik şartlar risk sınırında. Hava kalitesi indeksi: HKE {hke}. Drone takibi önerilir.")
else:
    sahin_metni = f"Şahin sistem raporu. {ilce_adi} istasyon verileri stabil. Yangın riski yüzde {risk} ile tamamen güvenli sınırlar içerisindedir."
    st.info(
        f"🤖 **ŞAHİN Yapay Zeka Özeti:** **{ilce_adi}** istasyon verileri stabil. Yangın riski %{risk} ile tamamen güvenli sınırlar içerisindedir.")

# ŞAHİN SES MOTORUNU ÇAĞIRMA (Sayfa her yüklendiğinde ya da ilçe değiştiğinde konuşur)
sahin_seslendir(sahin_metni)

row_col1, row_col2, row_col3, row_col4, row_col5, row_col6 = st.columns(6)

with row_col1:
    st.markdown(
        f'<div class="weather-card-wide"><div class="card-title-wide">🌡️ Sıcaklık</div><div class="card-value-wide">{sicaklik}°C</div><div class="card-sub-wide">Hissedilen: {sicaklik}°C</div></div>',
        unsafe_allow_html=True)
with row_col2:
    st.markdown(
        f'<div class="weather-card-wide"><div class="card-title-wide">💧 Bağıl Nem</div><div class="card-value-wide">%{nem}</div><div class="card-sub-wide">Kuruluk: Kararlı</div></div>',
        unsafe_allow_html=True)
with row_col3:
    st.markdown(
        f'<div class="weather-card-wide"><div class="card-title-wide">💨 Rüzgar</div><div class="card-value-wide">{ruzgar} <span style="font-size:14px;">km/s</span></div><div class="card-sub-wide">Yön: {yayilma_yonu}</div></div>',
        unsafe_allow_html=True)
with row_col4:
    st.markdown(
        f'<div class="weather-card-wide"><div class="card-title-wide">🌫️ Duman Yoğunluğu</div><div class="card-value-wide">{duman} <span style="font-size:14px;">PPM</span></div><div class="card-sub-wide">Durum: Aktif</div></div>',
        unsafe_allow_html=True)
with row_col5:
    st.markdown(
        f'<div class="weather-card-wide"><div class="card-title-wide">🍃 Hava Kalitesi</div><div class="card-value-wide">HKE {hke}</div><div class="card-sub-wide">Atmosfer İndeksi</div></div>',
        unsafe_allow_html=True)
with row_col6:
    st.markdown(
        f'<div class="weather-card-wide"><div class="card-title-wide">⛰️ Arazi Eğimi</div><div class="card-value-wide">{egim}°</div><div class="card-sub-wide">Topografya: Sabit</div></div>',
        unsafe_allow_html=True)

# ==============================================================================
# SEKMELER VE MÜDAHALE BUTONLARI
# ==============================================================================
st.write("---")
sekme1, sekme2, sekme3 = st.tabs(["🚒 Operasyon Komutları", "📈 İstatistiksel Risk Analizi", "📋 Sistem Günlükleri"])

with sekme1:
    st.subheader("🚒 Mobil Ekipler Hızlı Müdahale")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚨 AFAD Mobil Timi Sevk Et", use_container_width=True, key="afad_sevk_btn"):
            if risk >= 75:
                st.success(f"🚨 Onaylandı! {ilce_adi} risk seviyesi %{risk} (KRİTİK). AFAD Ekipleri sevk edildi!")
            else:
                st.warning(
                    f"⚠️ Sevk Reddedildi: Risk %{risk} seviyesinde. AFAD Mobil Timleri sadece %75 üzerindeki KRİTİK durumlarda sevk edilebilir.")

    with col2:
        if st.button(f"🚒 {koordinat['itfaiye']} Çıkış Ver", use_container_width=True, key="itfaiye_sevk_btn"):
            st.success(f"Yerel itfaiye birimlerine telsiz emri gönderildi. Ekipler {ilce_adi} için çıkış yapıyor.")

    with col3:
        if st.button("🚁 ŞAHİN Otonom Drone Kaldır", use_container_width=True, key="drone_sevk_btn"):
            if risk >= 45:
                st.success(f"🚁 Onaylandı! {ilce_adi} risk seviyesi %{risk}. Termal Otonom Drone keşif uçuşuna başladı.")
            else:
                st.warning(
                    f"⚠️ Kalkış Reddedildi: Risk %{risk} (Düşük). Batarya koruması ve filo sağlığı için drone kaldırılması engellendi.")

with sekme2:
    with st.container(key=f"sekme_grafik_konteyner_yapisi_{ilce_adi}"):
        st.subheader(f"📈 {ilce_adi} Bölgesi Son 24 Saatlik Değişim")

        saatler = pd.date_range(end=datetime.now(), periods=24, freq="h")
        np.random.seed(len(ilce_adi) + int(risk))
        gecmis_risk_verileri = np.random.randint(max(10, risk - 15), min(100, risk + 15), size=24)

        risk_grafik = pd.DataFrame(
            {f"{ilce_adi} Yangın Risk Analizi Trendi": gecmis_risk_verileri}
        )
        risk_grafik.index = saatler
        st.line_chart(risk_grafik, color="#ff4b4b" if risk >= 45 else "#00c853")

with sekme3:
    st.subheader("📋 AFAD İstasyon Log Kayıtları")
    kayitlar = pd.DataFrame({
        "Tarih/Saat": [(datetime.now() - timedelta(minutes=i * 20)).strftime("%d.%m.%Y %H:%M") for i in range(5)],
        "Gözlem Bölgesi": [ilce_adi] * 5,
        "Anlık Sıcaklık": [f"{sicaklik}°C" for _ in range(5)],
        "Hesaplanan Risk": [f"%{risk}" for _ in range(5)],
        "Sistem Kararı": [
            "GÜVENLİ - TAKİP" if risk < 45 else "⚠️ YÜKSEK - DRONE SEVKİ" if risk < 75 else "🚨 KRİTİK ACİL DURUM" for _
            in range(5)]
    })
    st.dataframe(kayitlar, use_container_width=True)
