import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="ŞAHİN Operasyon Merkezi", layout="wide")

# ŞAHİN Asistan Analiz Motoru (Mantıksal Raporlama)
def sahin_analiz_et(data):
    riskli_ilceler = data[data['Risk (%)'] > 70]['İlçe'].tolist()
    if not riskli_ilceler:
        return "Şu an tüm bölgelerde risk seviyeleri normal sınırlar içerisinde. Sistem stabil çalışıyor."
    else:
        return f"🚨 DİKKAT: {', '.join(riskli_ilceler)} bölgelerinde risk eşiği aşıldı! Ekiplerin bu bölgelere yönlendirilmesi önerilir."

# Veri Hazırlığı
ILCELER = ["Karaköprü", "Haliliye", "Eyyübiye", "Akçakale", "Birecik", "Bozova", "Ceylanpınar", "Halfeti", "Harran", "Hilvan", "Siverek", "Suruç", "Viranşehir"]
data = pd.DataFrame({
    'İlçe': ILCELER,
    'Sıcaklık (°C)': np.random.uniform(30, 45, len(ILCELER)),
    'Nem (%)': np.random.uniform(5, 20, len(ILCELER)),
    'Rüzgar (km/s)': np.random.uniform(10, 50, len(ILCELER)),
    'Eğim (%)': np.random.uniform(0, 40, len(ILCELER))
})
data['Risk (%)'] = (data['Sıcaklık (°C)'] * 1.5 - data['Nem (%)'] + data['Rüzgar (km/s)'] * 0.5 + data['Eğim (%)'] * 0.2).astype(int)

# Arayüz Yapısı
st.markdown("## 🦅 ŞAHİN: Operasyonel Kontrol Merkezi")

# Asistan Modülü
with st.expander("🤖 ŞAHİN Asistanına Sor", expanded=True):
    soru = st.text_input("ŞAHİN'e bir şey sor (Örn: 'Tüm ilçelerin durumunu analiz et')")
    if soru:
        st.write(f"**ŞAHİN:** {sahin_analiz_et(data)}")

# Ana Gövde: Grafikler ve Veri
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 Bölgesel Risk Analiz Tablosu")
    st.dataframe(data, use_container_width=True)
    
    st.subheader("📈 İlçe Bazlı Risk Dağılımı")
    st.bar_chart(data.set_index('İlçe')['Risk (%)'], color="#FF4B4B")

with col2:
    st.subheader("📋 Sistem Günlük Kayıtları")
    st.write("Son 5 log girişi:")
    for i in range(5):
        st.caption(f"🕒 16:1{i} - {ILCELER[i]} sensör verisi güncellendi.")
    
    st.markdown("---")
    with st.expander("🤝 Ekstra: Gönüllü Ol"):
        st.write("Projeye destek vermek isterseniz gönüllü kayıtları buradadır.")
        if st.button("Gönüllü Başvuru Formunu Aç"):
            st.info("Kayıt formu görüntülendi.")
