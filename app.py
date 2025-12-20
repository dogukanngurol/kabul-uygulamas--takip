import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
from docx import Document
from docx.shared import Inches

# --- 1. VERİTABANI AYARLARI ---
def init_db():
    conn = sqlite3.connect('saha_yonetim_v20.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Ahmet Salça', 'Genel Müdür')", (pw,))
    conn.commit()
    return conn

conn = init_db()
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. ARAYÜZ ---
st.set_page_config(page_title="Saha Takip v20", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Şirket Giriş Paneli")
    with st.form("login_form"):
        e = st.text_input("E-posta Adresi")
        p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Sisteme Giriş Yap"):
            u = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (e, make_hash(p))).fetchone()
            if u:
                st.session_state.update({
                    'logged_in': True, 'user_email': u[0], 'role': u[2], 
                    'user_name': u[3], 'user_title': u[4], 'page': "🏠 Ana Sayfa"
                })
                st.rerun()
            else: st.error("E-posta veya şifre hatalı!")
else:
    # --- YAN MENÜ (SIDEBAR) ---
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.caption(f"🏷️ {st.session_state['user_title']}")
    st.sidebar.markdown("---")
    
    # Sayfa Seçenekleri
    if st.session_state['role'] == 'admin':
        menu = ["🏠 Ana Sayfa", "➕ İş Atama & Takip", "✅ Tamamlanan İşler", "📦 Zimmet/Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Üstüme Atanan İşler", "📜 Tamamlanan İşlerim", "🎒 Zimmetim"]

    # Menü Butonlarını Oluşturma
    for item in menu:
        if st.sidebar.button(item, use_container_width=True):
            st.session_state.page = item

    # --- ÇIKIŞ BUTONU (Kırmızı ve Belirgin) ---
    st.sidebar.markdown("<br><br>", unsafe_allow_html=True) # Boşluk bırakır
    if st.sidebar.button("🔴 GÜVENLİ ÇIKIŞ", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state.page = "🏠 Ana Sayfa"
        st.rerun()

    current_page = st.session_state.page

    # --- SAYFA İÇERİKLERİ ---
    if current_page == "🏠 Ana Sayfa":
        st.info(f"✨ İyi Çalışmalar **{st.session_state['user_name']}**!")
        query = "SELECT status FROM tasks" if st.session_state['role'] == 'admin' else f"SELECT status FROM tasks WHERE assigned_to='{st.session_state['user_email']}'"
        df_tasks = pd.read_sql(query, conn)
        c1, c2 = st.columns(2)
        c1.metric("📌 Bekleyen İşler", len(df_tasks[df_tasks['status']=='Bekliyor']) if not df_tasks.empty else 0)
        c2.metric("✅ Tamamlanan İşler", len(df_tasks[df_tasks['status']=='Tamamlandı']) if not df_tasks.empty else 0)

    elif current_page == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("user_form"):
                ne, nn, nt, np, nr = st.text_input("E-posta"), st.text_input("Ad Soyad"), st.text_input("Unvan"), st.text_input("Şifre"), st.selectbox("Yetki", ["worker", "admin"])
                if st.form_submit_button("Kaydet"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ne, make_hash(np), nr, nn, nt))
                    conn.commit()
                    st.success("Kullanıcı oluşturuldu!"); st.rerun()
        st.table(pd.read_sql("SELECT name as 'Ad Soyad', email, title as 'Unvan' FROM users", conn))

    # Not: Diğer sayfaların (İş Atama vb.) kodları v19 ile aynıdır, buraya sığması için özetlenmiştir. 
    # v19'daki ilgili blokları bu yapının altına ekleyebilirsiniz.
