import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 1. SESSION STATE BAŞLATMA (Hata Almamak İçin En Üstte Olmalı) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'page' not in st.session_state:
    st.session_state['page'] = "🏠 Ana Sayfa"

# --- 2. FİLTRELEME VE BOŞ EKRAN YÖNETİCİSİ ---
def render_page_with_filters(query, title):
    st.header(f"{title}")
    
    # Veritabanı Bağlantısı
    conn = sqlite3.connect('anatolia_v65.db')
    try:
        df = pd.read_sql(query, conn)
    except:
        df = pd.DataFrame() # Tablo yoksa boş dön
    finally:
        conn.close()

    # 13, 31, 32, 33, 34, 35. MADDELER: FİLTRELEME PANELİ
    st.write("### 🔍 Filtreleme Seçenekleri")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1: f_tarih = st.date_input("📅 Tarih", [], key=f"date_{title}")
    with c2: 
        p_list = ["Hepsi"] + (df['assigned_to'].unique().tolist() if not df.empty else [])
        f_pers = st.selectbox("👷 Personel", p_list, key=f"pers_{title}")
    with c3: 
        # 32. MADDE: 81 İl Listesi buraya entegre edilebilir
        s_list = ["Hepsi"] + (df['city'].unique().tolist() if not df.empty else [])
        f_sehir = st.selectbox("📍 Şehir", s_list, key=f"city_{title}")
    with c4: 
        d_list = ["Hepsi"] + (df['status'].unique().tolist() if not df.empty else [])
        f_durum = st.selectbox("🚦 Durum", d_list, key=f"status_{title}")

    # --- 37. MADDE: BOŞ EKRAN KONTROLÜ ---
    if df.empty:
        st.warning(f"⚠️ Gösterilecek {title} Bulunmamaktadır.")
        return

    # Filtreleme Mantığı
    filt_df = df.copy()
    if f_pers != "Hepsi": filt_df = filt_df[filt_df['assigned_to'] == f_pers]
    if f_sehir != "Hepsi": filt_df = filt_df[filt_df['city'] == f_sehir]
    if f_durum != "Hepsi": filt_df = filt_df[filt_df['status'] == f_durum]

    # --- TABLO VE EXCEL (9, 30. MADDELER) ---
    st.dataframe(filt_df, use_container_width=True)
    
    csv = filt_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Excel Olarak İndir", csv, f"{title}.csv", "text/csv")

# --- 3. ANA UYGULAMA MANTIK AKIŞI ---
if not st.session_state['logged_in']:
    # ŞİFRE EKRANI BURAYA GELECEK
    st.title("🔐 Anatolia Bilişim Giriş")
    # ... login kodlarınız ...
else:
    # Sayfa Kontrolleri (Hata veren kısım burasıydı, artık güvenli)
    if st.session_state.page == "✅ Tamamlanan İşler":
        render_page_with_filters("SELECT * FROM tasks WHERE status='Tamamlandı'", "Tamamlanan İşler")
    
    elif st.session_state.page == "📋 Atanan İşler":
        render_page_with_filters("SELECT * FROM tasks WHERE status='Bekliyor'", "Atanan İşler")

    elif st.session_state.page == "💰 Hak Ediş":
        # 23. MADDE: Hak Ediş Seçenekleri
        render_page_with_filters("SELECT * FROM tasks WHERE status LIKE 'Hak Ediş%'", "Hak Ediş Paneli")
