import streamlit as st
import pandas as pd
from datetime import datetime

# --- YARDIMCI FONKSİYON: FİLTRELEME VE BOŞ EKRAN KONTROLÜ ---
def render_filtered_view(df, page_title, is_hakedis=False):
    st.header(f"📋 {page_title}")
    
    if df.empty:
        # Madde 37: Eğer tablo boşsa sadece filtreleri göster ve uyarı ver
        st.info(f"✨ Şu anda gösterilecek bir '{page_title}' kaydı bulunmamaktadır.")
        
        # Boş olsa bile filtre kutucuklarını göster (Kullanıcı deneyimi için)
        with st.expander("🔍 Filtreleme Seçenekleri (Aktif Veri Yok)"):
            c1, c2, c3, c4 = st.columns(4)
            c1.date_input("Tarih Seçin", key=f"d_{page_title}")
            c2.selectbox("Personel", ["Tüm Personeller"], key=f"p_{page_title}")
            c3.selectbox("Şehir", ["Tüm Şehirler"], key=f"s_{page_title}")
            c4.selectbox("Durum", ["Hepsi"], key=f"st_{page_title}")
        return

    # --- Madde 31, 32, 33, 34, 35: AKTİF FİLTRELEME PANELİ ---
    with st.sidebar.expander("🎯 Görünüm Filtreleri", expanded=True):
        # Tarih Filtresi
        f_tarih = st.date_input("📅 Tarih Aralığı", [], key=f"date_{page_title}")
        
        # Personel Filtresi (Madde 33)
        personel_list = ["Hepsi"] + sorted(df['assigned_to'].unique().tolist())
        f_pers = st.selectbox("👷 Personel", personel_list, key=f"pers_{page_title}")
        
        # Şehir Filtresi (Madde 32)
        sehir_list = ["Hepsi"] + sorted(df['city'].unique().tolist())
        f_sehir = st.selectbox("📍 Şehir", sehir_list, key=f"city_{page_title}")
        
        # Durum Filtresi (Madde 34 & 35)
        # Sadece yetkililerin göreceği özel durumlar otomatik olarak df içinde gelmelidir
        durum_list = ["Hepsi"] + sorted(df['status'].unique().tolist())
        f_durum = st.selectbox("🚦 Durum", durum_list, key=f"status_{page_title}")

    # Filtreleri Uygula
    filtrelenmis_df = df.copy()
    
    if f_pers != "Hepsi":
        filtrelenmis_df = filtrelenmis_df[filtrelenmis_df['assigned_to'] == f_pers]
    if f_sehir != "Hepsi":
        filtrelenmis_df = filtrelenmis_df[filtrelenmis_df['city'] == f_sehir]
    if f_durum != "Hepsi":
        filtrelenmis_df = filtrelenmis_df[filtrelenmis_df['status'] == f_durum]
    if len(f_tarih) == 2:
        filtrelenmis_df = filtrelenmis_df[
            (pd.to_datetime(filtrelenmis_df['created_at']).dt.date >= f_tarih[0]) & 
            (pd.to_datetime(filtrelenmis_df['created_at']).dt.date <= f_tarih[1])
        ]

    # --- SONUÇLARI GÖSTER ---
    if filtrelenmis_df.empty:
        st.warning("⚠️ Seçili filtrelere uygun sonuç bulunamadı.")
    else:
        st.dataframe(filtrelenmis_df, use_container_width=True)
        
        # Madde 9 & 30: Excel İndirme Özelliği
        csv = filtrelenmis_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Filtrelenmiş Veriyi Excel (CSV) Olarak İndir",
            data=csv,
            file_name=f"{page_title}_Rapor_{datetime.now().strftime('%d-%m-%Y')}.csv",
            mime='text/csv',
        )

# --- SAYFA YÖNLENDİRMELERİNDE KULLANIM ÖRNEĞİ ---
if st.session_state.page == "✅ Tamamlanan İşler":
    # Veritabanından veriyi çek (Örnektir)
    # raw_df = pd.read_sql("SELECT * FROM tasks WHERE status IN ('İŞ TAMAMLANDI', 'GİRİŞ YAPILAMADI', 'TEPKİLİ', 'MAL SAHİBİ GELMİYOR')", conn)
    render_filtered_view(raw_df, "Tamamlanan İşler")

elif st.session_state.page == "💰 Hak Ediş":
    # Madde 23: Hak Ediş Bekleniyor / Alındı durumlarını içeren tabloyu çek
    render_filtered_view(hakedis_df, "Hak Ediş Paneli", is_hakedis=True)
