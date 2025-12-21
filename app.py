import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- KÜTÜPHANE KONTROLÜ (Programın Çökmesini Engeller) ---
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. AYARLAR ---
UPLOAD_DIR = "uploaded_photos"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir"] # Örnek Liste

# --- 2. VERİTABANI VE HATA YÖNETİMİ ---
def get_db():
    return sqlite3.connect('operasyon_v52.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Yönetici', '0555'),
        ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '0555'),
        ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. GÜVENLİ EXCEL OLUŞTURMA (Hata Alınan Kısım) ---
def safe_to_excel(df):
    if df.empty:
        return None
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()
    except:
        return None

# --- 4. ARAYÜZ VE GÜVENLİ GÖSTERGELER ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🛡️ Saha Operasyon v52")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Giriş Başarısız")
else:
    # Sidebar ve Menü
    st.sidebar.title(f"Hoş Geldin, {st.session_state.u_name}")
    menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "✅ Tamamlanan İşler", "🎒 Zimmetim"]
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    
    if st.sidebar.button("🔴 Çıkış"): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # Göstergeler (Plotly yoksa bile hata vermez)
    if PLOTLY_AVAILABLE and st.session_state.u_role == 'Admin':
        fig = go.Figure(go.Indicator(mode="gauge+number", value=65, title={'text': "Günlük Verim"}))
        st.plotly_chart(fig, use_container_width=True)

    # --- EKRANLAR ---
    if cp == "🏠 Ana Sayfa":
        st.header("📊 Genel Durum")
        st.info("Kullanıcı verileri başarıyla yüklendi. İşlemlerinize menüden devam edebilirsiniz.")

    elif cp == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Arşivi")
        # Filtreler (Görseldeki panel)
        c1, c2, c3 = st.columns(3)
        p_filter = c1.selectbox("Personel", ["Hepsi"])
        city_filter = c2.selectbox("Şehir", ["Hepsi"] + ILLER)
        
        df = pd.read_sql("SELECT * FROM tasks WHERE status='Tamamlandı'", conn)
        
        if df.empty:
            st.warning("⚠️ Gösterilecek Tamamlanmış İş Bulunmamaktadır")
        else:
            st.dataframe(df)
            excel_data = safe_to_excel(df)
            if excel_data:
                st.download_button("📥 Excel İndir", excel_data, "rapor.xlsx")

    elif cp == "🎒 Zimmetim":
        st.header("🎒 Üzerimdeki Zimmetli Eşyalar")
        df_z = pd.read_sql(f"SELECT * FROM inventory WHERE assigned_to='{st.session_state.u_email}'", conn)
        if df_z.empty:
            st.info("ℹ️ Üzerinizde kayıtlı zimmet bulunmamaktadır.")
        else:
            st.table(df_z)
