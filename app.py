import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- AYARLAR VE KLASÖRLER ---
UPLOAD_DIR = "saha_dosyalari"
if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir", "Konya", "Samsun"] # Örnektir, 81 il eklenebilir.

# --- VERİTABANI BAĞLANTISI ---
def get_db():
    return sqlite3.connect('operasyon_v56.db', check_same_thread=False)

def excel_indir(df, dosya_adi):
    if df.empty: return None
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

# --- ORTAK FİLTRELEME ALTYAPISI (Madde 5 ve 8) ---
def apply_filters(df, key_prefix):
    st.write("### 🔍 Filtreler")
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_tarih = st.date_input("Tarih", [], key=f"{key_prefix}_t")
    with c2: f_pers = st.selectbox("Personel", ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"], key=f"{key_prefix}_p")
    with c3: f_sehir = st.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"{key_prefix}_s")
    
    d_opts = ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
    if st.session_state.u_role in ['Admin', 'Müdür']:
        d_opts += ["Türk Telekom Onayında", "Hak Ediş Bekleniyor", "Hak Ediş Alındı"]
    with c4: f_durum = st.selectbox("Durum", d_opts, key=f"{key_prefix}_d")
    
    res_df = df.copy()
    if not res_df.empty:
        if f_pers != "Hepsi": res_df = res_df[res_df['assigned_to'] == f_pers]
        if f_sehir != "Hepsi": res_df = res_df[res_df['city'] == f_sehir]
        if f_durum != "Hepsi":
            if f_durum in ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]:
                res_df = res_df[res_df['result_type'] == f_durum]
            else:
                res_df = res_df[res_df['status'] == f_durum]
    
    ex_data = excel_indir(res_df, key_prefix)
    if ex_data:
        st.download_button(label="📥 Filtrelenmiş Excel İndir", data=ex_data, file_name=f"{key_prefix}_rapor.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"{key_prefix}_btn")
    
    if res_df.empty:
        st.warning("⚠️ Gösterilecek Veri Bulunmamaktadır")
        return pd.DataFrame()
    return res_df

# --- OTURUM KONTROLÜ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    conn = get_db()
    cp = st.session_state.page
    st.sidebar.title(f"Hoş Geldin, {st.session_state.u_name}")

    # --- 10. ATANAN İŞLER TAKİP EKRANI ---
    if cp == "📋 Atanan İşler":
        st.header("📋 Atanan İşler Takip Paneli")
        # Sadece henüz sonuçlanmamış (Bekliyor veya Ret edilmiş) işler
        raw_df = pd.read_sql("SELECT assigned_to, title, city, status, created_at FROM tasks WHERE status IN ('Bekliyor', 'Ret Edildi')", conn)
        df = apply_filters(raw_df, "atananlar")
        if not df.empty:
            st.table(df) # Net görüntüleme için tablo formatı

    # --- 8. GİRİŞ ONAYLARI EKRANI ---
    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Onayı Bekleyen İşler")
        # Personelin 'Giriş Mail Onayı Bekler' olarak gönderdiği işler
        raw_df = pd.read_sql("SELECT * FROM tasks WHERE status = 'Giriş Onayı Bekliyor'", conn)
        df = apply_filters(raw_df, "giris_onay")
        if not df.empty:
            for _, r in df.iterrows():
                with st.expander(f"📌 {r['title']} - {r['assigned_to']}"):
                    st.write(f"**Rapor:** {r['report']}")
                    if st.button("✅ Giriş Onayı Ver ve İşe Başlat", key=f"go_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Bekliyor', result_type=NULL WHERE id=?", (r['id'],))
                        conn.commit(); st.rerun()

    # --- 7 & 8. TT ONAY BEKLEYENLER EKRANI ---
    elif cp == "📡 TT Onay Bekleyenler":
        st.header("📡 TT Onay Bekleyenler")
        # Müdürün 'Türk Telekom Onayında' durumuna aldığı işler
        raw_df = pd.read_sql("SELECT * FROM tasks WHERE status = 'Türk Telekom Onayında'", conn)
        df = apply_filters(raw_df, "tt_onay")
        if not df.empty:
            st.dataframe(df)
            for _, r in df.iterrows():
                with st.expander(f"İş Detayı: {r['title']}"):
                    if st.session_state.u_role in ['Admin', 'Müdür']:
                        if st.button("💰 Hak Edişe Gönder", key=f"heg_{r['id']}"):
                            conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],))
                            conn.commit(); st.rerun()

    # (Diğer ekran kodları v55 ile aynı şekilde devam eder...)
