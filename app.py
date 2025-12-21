import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- KÜTÜPHANE VE GÖRSEL KORUMA ---
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. AYARLAR ---
UPLOAD_DIR = "saha_depo"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir"] # Örnektir, 81 il eklenebilir.

# --- 2. VERİTABANI ---
def get_db():
    return sqlite3.connect('saha_v54.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [('admin@sirket.com', pw, 'Admin', 'Admin', '0555'), 
             ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '0555')]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. YENİLENMİŞ VE HATASIZ EXCEL FONKSİYONU ---
def download_excel_logic(df, filename):
    """Excel indirme butonunu güvenli bir şekilde oluşturur."""
    if df.empty:
        st.warning("⚠️ İndirilecek veri bulunmadığı için Excel butonu oluşturulmadı.")
        return
    
    # Bellek üzerinde Excel dosyası oluşturma
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Rapor')
        
        processed_data = output.getvalue()
        
        st.download_button(
            label="📥 Excel Raporu İndir",
            data=processed_data,
            file_name=f"{filename}_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"btn_{filename}"
        )
    except Exception as e:
        st.error(f"Excel oluşturulurken bir hata oluştu: {e}")

# --- 4. ARAYÜZ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🛡️ Saha Operasyon v54")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Giriş Başarısız!")
else:
    # Sidebar Karşılama
    st.sidebar.markdown(f"### Merhaba, {st.session_state.u_name}")
    
    # 13. GÖRSEL İLERLEME (Gauge)
    if PLOTLY_AVAILABLE:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=65, title={'text': "Günlük İlerleme"}))
        fig.update_layout(height=180, margin=dict(l=10, r=10, t=30, b=10))
        st.sidebar.plotly_chart(fig, use_container_width=True)

    menu = ["🏠 Ana Sayfa", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter"]
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    
    if st.sidebar.button("🔴 ÇIKIŞ"): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- TAMAMLANAN İŞLER EKRANI ---
    if cp == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Arşivi")
        
        # 4. FİLTRELEME ALTYAPISI
        st.write("### 🔍 Filtreler")
        c1, c2, c3 = st.columns(3)
        f_city = c1.selectbox("Şehir", ["Hepsi"] + ILLER)
        f_status = c2.selectbox("Durum", ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ"])
        
        # Veriyi çekme
        query = "SELECT * FROM tasks"
        df = pd.read_sql(query, conn)
        
        # Filtreleme Mantığı
        if f_city != "Hepsi": df = df[df['city'] == f_city]
        if f_status != "Hepsi": df = df[df['result_type'] == f_status]

        # 12. BOŞ EKRAN DAVRANIŞI
        if df.empty:
            st.info("ℹ️ Gösterilecek Tamamlanmış İş Bulunmamaktadır")
            # Boş olsa bile filtreler yukarıda kalmaya devam eder
        else:
            st.dataframe(df, use_container_width=True)
            # EXCEL İNDİRME BUTONU (Sadece veri varsa görünür)
            download_excel_logic(df, "Tamamlanan_Isler")

    # --- HAK EDİŞ EKRANI ---
    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Yönetimi")
        df_h = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleyen', 'Hak Ediş Alındı')", conn)
        
        if df_h.empty:
            st.warning("ℹ️ Hak ediş ekranında gösterilecek veri bulunmamaktadır.")
        else:
            st.dataframe(df_h)
            download_excel_logic(df_h, "Hak_Edis_Raporu")

    # --- ZİMMET EKRANI ---
    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Envanter Listesi")
        df_z = pd.read_sql("SELECT * FROM inventory", conn)
        
        if st.session_state.u_role == 'Admin':
            download_excel_logic(df_z, "Genel_Envanter")
        
        st.table(df_z)
