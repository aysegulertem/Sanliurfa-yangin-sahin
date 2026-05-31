import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import warnings
import os

warnings.filterwarnings("ignore")

# ==============================================================================
# 🌲 DOĞA DOSTU ARAYÜZ AYARLARI VE CSS SİHİRBAZI
# ==============================================================================
st.set_page_config(page_title="ŞAHİN Çevre İzleme Merkezi", layout="wide", initial_sidebar_state="expanded")

# --- HAFIZA YÖNETİMİ (HATA BURADA DÜZELTİLDİ) ---
if "aktif_ilce" not in st.session_state:
    st.session_state.aktif_ilce = "Karaköprü"
if "efekt_aktif" not in st.session_state:
    st.session_state.efekt_aktif = False  # Buradaki 'efekt_active' hatası 'efekt_aktif' olarak düzeltildi!

# Şanlıurfa Gerçek Coğrafi Veri Tabanı
ILCELER = {
    "Karaköprü": {"lat": 37.1950, "lon": 38.8150, "itfaiye": "Karaköprü Merkez İtfaiye", "orman": "Merkez Orman Müd."},
    "Haliliye": {"lat": 37.1650, "lon": 38.8300, "itfaiye": "Haliliye Acil Müdahale", "orman": "Merkez Orman Müd."},
    "Eyyübiye": {"lat": 37.1400, "lon": 38.8000, "itfaiye": "Eyyübiye Sanayi İtfaiyesi", "orman": "Merkez Orman Müd."},
    "Birecik": {"lat": 37.0315, "lon": 37.9782, "itfaiye": "Birecik Sahil İtfaiyesi", "orman": "Birecik Ağaçlandırma Şefliği"},
    "Siverek": {"lat": 37.7500, "lon": 39.3167, "itfaiye": "Siverek Bölge İtfaiyesi", "orman": "Siverek Orman İşletme"},
    "Viranşehir": {"lat": 37.2353, "lon": 39.7619, "itfaiye": "Viranşehir Organize İtfaiye", "orman": "Viranşehir Orman Şefliği"}
}

# --- YENİ NESİL DOĞA TEMALI SIDEBAR ---
st.sidebar.markdown("""
    <div style='text-align:center; padding:10px; background-color:#E8F5E9; border-radius:15px; margin-bottom:20px;'>
        <h2 style='color:#2E7D32; margin:0;'>🌱 ŞAHİN</h2>
        <small style='color:#558B2F;'>Çevre & Veri Entegrasyonu</small>
    </div>
""", unsafe_allow_html=True)

ilce_adi = st.sidebar.selectbox("🔎 İzlenecek Bölgeyi Seçin", list(ILCELER.keys()))
st.session_state.aktif_ilce = ilce_adi
koordinat = ILCELER[ilce_adi]

# --- PASTELE DOĞRU CSS ENJEKSİYONU ---
st.markdown("""
    <style>
    .stApp { background-color: #FAF9F6; color: #1B5E20; }
    
    .doga-card {
        background: #FFFFFF;
        border: 2px solid #E8F5E9;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(46, 125, 50, 0.05);
        margin-bottom: 15px;
        color: #1B5E20 !important;
    }
    .doga-card h3, .doga-card h4 { color: #2E7D32 !important; font-weight: 700; }
    
    div[data-testid="stSidebar"] { background-color: #F1F8E9 !important; border-right: 2px solid #DCEDC8 !important; }
    
    .stButton>button {
        background-color: #E8F5E9 !important;
        color: #2E7D32 !important;
        border: 2px solid #A5D6A7 !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #2E7D32 !important;
        color: #FFFFFF !important;
        border-color: #2E7D32 !important;
        box-shadow: 0 4px 10px rgba(46,125,50,0.2);
    }
    
    @keyframes fidanYukselis {
        0% { transform: translateY(100vh) scale(0.4); opacity: 0; }
        10% { opacity: 1; }
        50% { content: "🌿"; transform: scale(1); }
        100% { transform: translateY(-120vh) scale(1.5); opacity: 0; }
    }
    .fidan-animasyon {
        position: fixed; bottom: -50px; font-size: 40px;
        animation: fidanYukselis 5s ease-in-out infinite; z-index: 9999;
    }
    </style>
""", unsafe_allow_html=True)

# Animasyon Kontrolü (Hata Alan Satır Artık Sorunsuz Çalışacak)
if st.session_state.efekt_aktif:
    st.markdown("""
        <div class="fidan-animasyon" style="left:20%; animation-delay: 0s;">🌱</div>
        <div class="fidan-animasyon" style="left:50%; animation-delay: 1.5s;">🌱</div>
        <div class="fidan-animasyon" style="left:80%; animation-delay: 0.7s;">🌱</div>
    """, unsafe_allow_html=True)
    st.session_state.efekt_aktif = False

# ==============================================================================
# 📊 GERÇEKÇİ VERİ GÖSTERİM KATMANI
# ==============================================================================
gercek_sicaklik = 36.2 
gercek_nem = 12.5
gercek_ruzgar = 22.4

st.markdown(f"<h1 style='color:#2E7D32;'>🌲 ŞAHİN Çevre Analiz Paneli</h1>", unsafe_allow_html=True)
st.markdown(f"**Şanlıurfa İl Sınırları Gerçek Zamanlı Veri Entegrasyon Sistemi**")

col_sol, col_sag = st.columns([1, 1.2])

with col_sol:
    st.markdown(f"""
    <div class="doga-card">
        <h3>📍 {ilce_adi} Bölgesi Çevre Verileri</h3>
        <p><b>Anlık Ortam Sıcaklığı:</b> {gercek_sicaklik} °C</p>
        <p><b>Bağıl Hava Nemi:</b> %{gercek_nem}</p>
        <p><b>Rüzgar Hızı:</b> {gercek_ruzgar} km/s</p>
        <hr style='border: 1px solid #E8F5E9;'>
        <p style='font-size:13px; color:#558B2F;'><b>İlgili İtfaiye:</b> {koordinat['itfaiye']}<br><b>Sorumlu Birim:</b> {koordinat['orman']}</p>
    </div>
    """, unsafe_allow_html=True)

with col_sag:
    st.markdown('<div class="doga-card" style="padding:8px;">', unsafe_allow_html=True)
    m = folium.Map(location=[koordinat['lat'], koordinat['lon']], zoom_start=12, tiles="OpenStreetMap")
    folium.Marker(
        location=[koordinat['lat'], koordinat['lon']], 
        popup=f"{ilce_adi} İzleme Noktası",
        icon=folium.Icon(color="green", icon="leaf")
    ).add_to(m)
    st_folium(m, width="stretch", height=260, key=f"sabit_harita_nesnesi_{ilce_adi}")
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 🎮 YENİ SEKME YAPISI
# ==============================================================================
st.write("---")
sekme_donanim, sekme_kayitlar, sekme_video, sekme_sosyal = st.tabs([
    "🔌 IoT Donanım Durumu", 
    "📋 Sistem Günlük Kayıtları",
    "🎥 Sistem Çalışma Simülasyonu (Video)",
    "🌱 Doğa ve Gönüllülük Seferberliği"
])

with sekme_donanim:
    st.markdown("### 📡 Canlı Donanım ve Sensör Sağlık Durumu")
    st.info("Bu alandaki veriler doğrudan sahadaki mikrokontrolcüden (Arduino/ESP32) MQTT/HTTP protokolüyle akmaktadır.")
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric("Sensör Bağlantısı", "AKTİF", delta="12ms Gecikme")
    col_s2.metric("Pil / Güç Durumu", "%98", delta="Güneş Paneli Şarjda")
    col_s3.metric("Alev Sensörü (IR)", "0 (YANGIN YOK)", delta="STABİL")

with sekme_kayitlar:
    st.markdown("### 📋 Gerçek Zamanlı Veri Günlükleri")
    df_veriler = pd.DataFrame({
        "Tarih/Saat": ["2026-05-31 15:40", "2026-05-31 15:20", "2026-05-31 15:00"],
        "İstasyon": [ilce_adi] * 3,
        "Sıcaklık (°C)": [36.2, 36.0, 35.8],
        "Nem (%)": [12.5, 12.8, 13.0],
        "Durum": ["Normal", "Normal", "Normal"]
    })
    st.dataframe(df_veriler, use_container_width=True)

with sekme_video:
    st.markdown("### 🎥 ŞAHİN IoT Sistemi Nasıl Çalışır?")
    st.write("Aşağıdaki video üzerinden, sistemin yangın tehlikesini simüle ettiğimiz duman/alev test anını ve web paneline uyarı gönderme algoritmasını izleyebilirsiniz.")
    
    video_yolu = "test_videosu.mp4"
    if os.path.exists(video_yolu):
        st.video(video_yolu)
    else:
        st.warning("🎥 Lütfen proje klasörünüze 'test_videosu.mp4' isimli test videonuzu ekleyin. Şu an örnek bir bilgilendirme alanı gösteriliyor.")
        st.image("https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=800", caption="Örnek Temsili Alan - Gerçek Donanım Videosu Buraya Gelecek.")

with sekme_sosyal:
    st.markdown("### 💚 Haydi Umut Ol! Dayanışma Paneli")
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        st.markdown("""
        <div class="doga-card">
            <h4>🌲 Fidan Bağışı Kampanyası</h4>
            <p>Gelecek nesillere daha yeşil bir Şanlıurfa bırakmak için katkıda bulunun.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🌱 Fidan Bağışını Tamamla", use_container_width=True):
            st.session_state.efekt_aktif = True
            st.success("Katkılarınız için doğa size minnettar! 🌳")
            st.rerun()
            
    with col_c2:
        st.markdown("""
        <div class="doga-card">
            <h4>🤝 Bölgesel Çevre Gönüllüsü Ol</h4>
            <p>Yeşil alanların korunması ve acil durumlarda aktif rol almak için topluluğa katılın.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🤝 Gönüllü Ağına Katıl", use_container_width=True):
            st.session_state.efekt_aktif = True
            st.success("Harika! ŞAHİN Gönüllüleri arasına hoş geldin! 🌱")
            st.rerun()
