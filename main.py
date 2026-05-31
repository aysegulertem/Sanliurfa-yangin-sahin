import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

# --- AYARLAR ---
st.set_page_config(page_title="ŞAHİN | Operasyonel Merkez", layout="wide")

# --- TEMA VE SESSION STATE ---
if 'tema' not in st.session_state: st.session_state.tema = 'Koyu'

def apply_theme():
    # Koyu/Açık mod mantığı
    if st.session_state.tema == 'Koyu':
        st.markdown("<style>.stApp {background-color: #0E1117; color: #FAFAFA;}</style>", unsafe_allow_html=True)
    else:
        st.markdown("<style>.stApp {background-color: #FFFFFF; color: #262730;}</style>", unsafe_allow_html=True)

apply_theme()

# --- VERİ VE ANALİZ ---
ILCELER = ["Karaköprü", "Haliliye", "Eyyübiye", "Akçakale", "Birecik", "Bozova", "Ceylanpınar", "Halfeti", "Harran", "Hilvan", "Siverek", "Suruç", "Viranşehir"]
df = pd.DataFrame({
    'İlçe': ILCELER,
    'Sıcaklık (°C)': np.random.uniform(32, 45, len(ILCELER)),
    'Nem (%)': np.random.uniform(5, 20, len(ILCELER)),
    'Rüzgar (km/s)': np.random.uniform(10, 60, len(ILCELER)),
    'Eğim (%)': np.random.uniform(0, 50, len(ILCELER))
})
df['Risk (%)'] = (df['Sıcaklık (°C)'] * 1.5 - df['Nem (%)'] + df['Rüzgar (km/s)'] * 0.4 + df['Eğim (%)'] * 0.3).astype(int)

# --- ŞAHİN ASİSTANI (GÜÇLÜ ANALİZ) ---
def sahin_analyze(df):
    high_risk = df[df['Risk (%)'] > 80]
    if high_risk.empty: return "🦅 ŞAHİN: Tüm bölgeler tarandı, sistem stabil."
    return f"⚠️ KRİTİK RAPOR: {', '.join(high_risk['İlçe'].tolist())} bölgelerinde risk tavan yaptı. Acil durum protokolü devrede!"

# --- ARAYÜZ (Geri dönen muazzam yapımız) ---
st.sidebar.title("🦅 ŞAHİN Operasyonel Panel")
st.sidebar.radio("Arayüz Teması", ["Koyu", "Açık"], key='tema', on_change=apply_theme)
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 ŞAHİN Asistanı")
query = st.sidebar.text_input("ŞAHİN'e komut ver...")
if query: st.sidebar.write(f"**Asistan:** {sahin_analyze(df)}")

st.title("🦅 ŞAHİN | Operasyonel İzleme Merkezi")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 Bölgesel Risk Veri Tablosu")
    # Hata veren background_gradient yerine daha stabil ve şık bir tablo gösterimi
    st.dataframe(df, use_container_width=True)
    
    st.subheader("📈 Veri Görselleştirme")
    st.line_chart(df.set_index('İlçe')[['Sıcaklık (°C)', 'Risk (%)']])

with col2:
    st.subheader("📍 Canlı Harita Takibi")
    m = folium.Map(location=[37.165, 38.83], zoom_start=9)
    # İkonlar ve markerlar geri döndü
    for _, row in df.iterrows():
        color = 'red' if row['Risk (%)'] > 75 else 'green'
        folium.Marker([37.165 + np.random.uniform(-0.5, 0.5), 38.83 + np.random.uniform(-0.5, 0.5)],
                      icon=folium.Icon(color=color, icon='info-sign')).add_to(m)
    st_folium(m, width=400, height=400)

with st.expander("📋 Sistem Günlük Kayıtları (Veritabanı Logları)"):
    st.table(df.head(10))

with st.expander("🤝 Ekstra: Saha Gönüllülüğü"):
    st.write("Yangınla mücadele süreçlerine lojistik destek sağlamak için gönüllü ağımıza katılın.")
