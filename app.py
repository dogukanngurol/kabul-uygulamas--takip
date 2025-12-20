import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
from docx import Document
from docx.shared import Inches

# --- 1. VERİTABANI ---
def init_db():
    conn = sqlite3.connect('saha_takip_v22.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Ahmet Salça', 'Müdür')", (pw,))
    conn.commit()
    return conn

conn = init_db()
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. ANA UYGULAMA MANTIĞI ---
st.set_page_config(page_title="Saha Takip v22", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Şirket Giriş Paneli")
    with st.form("login"):
        e = st.text_input("E-posta")
        p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş Yap"):
            u = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (e, make_hash(p))).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4], 'page': "🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı giriş!")
else:
    # --- YAN MENÜ ---
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.caption(f"🏷️ {st.session_state['user_title']}")
    st.sidebar.markdown("---")
    
    if st.session_state['role'] == 'admin':
        menu = ["🏠 Ana Sayfa", "➕ İş Atama & Takip", "✅ Tamamlanan İşler", "📦 Zimmet/Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Üstüme Atanan İşler", "📜 Tamamlanan İşlerim", "🎒 Zimmetim"]

    for item in menu:
        if st.sidebar.button(item, use_container_width=True):
            st.session_state.page = item

    st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
    if st.sidebar.button("🔴 GÜVENLİ ÇIKIŞ", use_container_width=True):
        st.session_state.logged_in = False
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

    elif current_page == "📦 Zimmet/Envanter":
        st.header("📦 Envanter ve Zimmet")
        if st.session_state['role'] == 'admin':
            st.subheader("Mevcut Zimmet Listesi")
            st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)
            
            st.markdown("---")
            st.subheader("➕ Yeni Zimmet Ekle")
            
            # 🌟 OTOMATİK KULLANICI SEÇİMİ (İSTEDİĞİNİZ ÖZELLİK)
            all_users = pd.read_sql("SELECT email, name FROM users", conn)
            user_options = {f"{row['name']} ({row['email']})": row['email'] for _, row in all_users.iterrows()}
            
            with st.form("zimmet_ekle"):
                item_name = st.text_input("Malzeme Adı (Örn: Matkap, Araç vb.)")
                selected_user_label = st.selectbox("Zimmetlenecek Personel", options=list(user_options.keys()))
                quantity = st.number_input("Adet", min_value=1, step=1)
                
                if st.form_submit_button("Zimmetle"):
                    target_email = user_options[selected_user_label]
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", 
                                 (item_name, target_email, quantity, st.session_state['user_name']))
                    conn.commit()
                    st.success(f"{item_name} başarıyla {target_email} adresine zimmetlendi!")
                    st.rerun()

    elif current_page == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı Kaydı"):
            with st.form("k_ekle"):
                ne = st.text_input("E-posta")
                nn = st.text_input("Ad Soyad")
                
                # 🌟 OTOMATİK UNVAN SEÇİMİ (İSTEDİĞİNİZ ÖZELLİK)
                nt = st.selectbox("Unvan", ["Saha Çalışanı", "Müdür", "Teknisyen", "Operatör", "Stajyer"])
                
                np = st.text_input("Şifre", type='password')
                nr = st.selectbox("Yetki (Sistem Rolü)", ["worker", "admin"])
                
                if st.form_submit_button("Kaydı Tamamla"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ne, make_hash(np), nr, nn, nt))
                    conn.commit()
                    st.success("Kullanıcı başarıyla sisteme eklendi!")
                    st.rerun()
        
        st.subheader("Mevcut Kullanıcılar")
        st.table(pd.read_sql("SELECT name as 'Ad Soyad', email as 'E-posta', title as 'Unvan', role as 'Rol' FROM users", conn))

    # Diğer sayfalar (İş Atama vb.) v21 ile aynı mantıkta devam eder.
