import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
import time

# --- ARAYÜZ AYARLARI VE TEMA KONTROLÜ ---
# Kullanıcının tema seçimine bağlı kalıcı yapı
if 'tema' not in st.session_state:
    st.session_state.tema = 'Koyu'

def apply_theme():
    if st.session_state.tema == 'Koyu':
        bg_color, text_color = "#0E1117", "#FAFAFA"
    else:
        bg_color, text_color = "#FFFFFF", "#262730"
    
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {bg_color}; color: {text_color}; }}
        .css-1r6slp0 {{ color: {text_color} !important; }}
        </style>
    """, unsafe_allow_html=True)

apply_theme()

# --- VERİ VE ANALİZ MOTORU ---
ILCELER = ["Karaköprü", "Haliliye", "Eyyübiye", "Akçakale", "Birecik", "Bozova", "Ceylanpınar", "Halfeti", "Harran", "Hilvan", "Siverek", "Suruç", "Viranşehir"]

def get_data():
    df = pd.DataFrame({
        'İlçe': ILCELER,
        'Sıcaklık (°C)': np.random.uniform(32, 45, len(ILCELER)),
        'Nem (%)': np.random.uniform(5, 20, len(ILCELER)),
        'Rüzgar (km/s)': np.random.uniform(10, 60, len(ILCELER)),
        'Eğim (%)': np.random.uniform(0, 50, len(ILCELER))
    })
    df['Risk (%)'] = (df['Sıcaklık (°C)'] * 1.5 - df['Nem (%)'] + df['Rüzgar (km/s)'] * 0.4 + df['Eğim (%)'] * 0.3).astype(int)
    return df

data = get_data()

# --- ŞAHİN ASİSTANI MANTIĞI ---
def sahin_analyze(df):
    high_risk = df[df['Risk (%)'] > 80]
    if high_risk.empty:
        return "Tüm ilçeler tarandı. Genel yangın riski kontrol altında, sistem stabil."
    return f"ANALİZ RAPORU: {', '.join(high_risk['İlçe'].tolist())} bölgelerinde kritik eşik aşıldı. Eğim ve yüksek rüzgar nedeniyle yayılma hızı çok yüksek, acil müdahale ekibi yönlendirilmeli."

# --- SIDEBAR: KONTROL VE ASİSTAN ---
with st.sidebar:
    st.title("🦅 ŞAHİN Operasyonel Panel")
    st.session_state.tema = st.radio("Arayüz Teması", ["Koyu", "Açık"])
    st.markdown("---")
    st.subheader("🤖 ŞAHİN Asistanı")
    query = st.text_input("ŞAHİN'e sor...")
    if query:
        st.write(f"**Asistan:** {sahin_analyze(data)}")

# --- ANA GÖVDE: DERİNLİKLİ VERİ ANALİZİ ---
st.title("Operasyonel İzleme Merkezi")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Bölgesel Risk Veri Tablosu")
    st.dataframe(data.style.background_gradient(subset=['Risk (%)'], cmap='Reds'), use_container_width=True)
    
    st.subheader("Detaylı Risk Trend Analizi")
    st.line_chart(data.set_index('İlçe')[['Sıcaklık (°C)', 'Risk (%)']])

with col2:
    st.subheader("Canlı Harita Entegrasyonu")
    # Harita katmanı ve ilçe markerleri burada kompleks bir şekilde render edilir
    m = folium.Map(location=[37.165, 38.83], zoom_start=9)
    for _, row in data.iterrows():
        folium.CircleMarker(
            location=[37.165 + np.random.uniform(-0.5, 0.5), 38.83 + np.random.uniform(-0.5, 0.5)],
            radius=row['Risk (%)']/5,
            color='red' if row['Risk (%)'] > 75 else 'green',
            fill=True
        ).add_to(m)
    st_folium(m, width=400, height=350)

# --- SİSTEM GÜNLÜK KAYITLARI (MODÜLER YAPI) ---
with st.expander("📋 Sistem Günlük Kayıtları (Database Log)"):
    st.table(data.head(10))

# --- GÖNÜLLÜLÜK (Düşük öncelikli modül) ---
with st.expander("🤝 Ekstra: Saha Gönüllülüğü"):
    st.write("Yangınla mücadele süreçlerine lojistik destek sağlamak için gönüllü ağımıza katılın.")
