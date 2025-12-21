import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

# --- 1. SESSION STATE AYARLARI (HATA ÖNLEME) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'page' not in st.session_state:
    st.session_state['page'] = "🏠 Ana Sayfa"

# --- 2. VERİTABANI BAĞLANTISI ---
def init_db():
    conn = sqlite3.connect('anatolia.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, city TEXT, status TEXT)''')
    
    # Örnek Admin Hesabı (Şifre: 1234)
    hashed_pw = hashlib.sha256('1234'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@anatolia.com', ?, 'Admin', 'Doğukan Gürol')", (hashed_pw,))
    conn.commit()
    conn.close()

init_db()

# --- 3. GİRİŞ EKRANI ---
if not st.session_state['logged_in']:
    st.title("🔐 Anatolia Bilişim Giriş")
    with st.form("login_form"):
        u_email = st.text_input("E-posta")
        u_pass = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            h_pw = hashlib.sha256(u_pass.encode()).hexdigest()
            conn = sqlite3.connect('anatolia.db')
            res = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (u_email, h_pw)).fetchone()
            conn.close()
            
            if res:
                st.session_state['logged_in'] = True
                st.session_state['u_name'] = res[3]
                st.session_state['u_role'] = res[2]
                st.rerun()
            else:
                st.error("Hatalı giriş!")

# --- 4. ANA PANEL (GİRİŞ YAPILINCA GÖRÜNECEK) ---
else:
    # Sidebar Menüsü
    with st.sidebar:
        st.markdown(f"### 🏢 Anatolia Bilişim\n**{st.session_state.u_name}** - *{st.session_state.u_role}*")
        st.divider()
        
        menu = ["🏠 Ana Sayfa", "📋 Atanan İşler", "✅ Tamamlanan İşler", "🔴 Çıkış"]
        selected = st.radio("Menü", menu)
        
        if selected == "🔴 Çıkış":
            st.session_state['logged_in'] = False
            st.rerun()
        else:
            st.session_state['page'] = selected

    # Sayfa İçerikleri
    if st.session_state.page == "🏠 Ana Sayfa":
        st.header(f"👋 Hoş Geldin, {st.session_state.u_name}")
        st.info("Sistem aktif. Yapmak istediğiniz işlemi soldaki menüden seçin.")

    elif st.session_state.page == "📋 Atanan İşler":
        st.header("📋 Atanan İşler Takip Paneli")
        conn = sqlite3.connect('anatolia.db')
        df = pd.read_sql("SELECT * FROM tasks WHERE status='Bekliyor'", conn)
        conn.close()
        
        if df.empty:
            st.warning("⚠️ Atanmış bir iş bulunmamaktadır.")
        else:
            st.dataframe(df, use_container_width=True)
