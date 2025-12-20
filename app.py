import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI BAĞLANTISI ---
def get_db():
    conn = sqlite3.connect('saha_operasyon_v35.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, result_type TEXT, hakedis_durum TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'admin', 'Ahmet Salça', 'Genel Müdür', '0555'),
        ('filiz@deneme.com', pw, 'admin', 'Filiz Hanım', 'Müdür', '0555'),
        ('dogukan@deneme.com', pw, 'worker', 'Doğukan Gürol', 'Saha Personeli', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 2. YARDIMCI ARAÇLAR ---
def get_welcome_msg(name):
    hr = datetime.now().hour
    if 0 <= hr < 8: m = "İyi Geceler"
    elif 8 <= hr < 12: m = "Günaydın"
    elif 12 <= hr < 18: m = "İyi Günler"
    else: m = "İyi Akşamlar"
    return f"{m} **{name}**, İyi Çalışmalar!"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Gaziantep", "Konya", "Samsun", "Trabzon"]

# --- 3. ARAYÜZ YÖNETİMİ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Saha Operasyon Giriş")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı bilgiler.")
else:
    # MENÜ
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.caption(f"📍 {st.session_state['user_title']}")
    
    if st.session_state['user_title'] in ['Müdür', 'Genel Müdür']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama & Takip", "📨 Giriş Onayları", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcılar"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşler", "📜 Çalışma Geçmişim", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    cp = st.session_state.page
    conn = get_db()

    # --- SORGULANAN EKRANLARDAKİ DÜZELTMELER ---

    if cp == "🏠 Ana Sayfa":
        st.info(get_welcome_msg(st.session_state['user_name']))
        st.write("Lütfen soldaki menüden yapmak istediğiniz işlemi seçin.")

    elif cp == "➕ İş Atama & Takip":
        st.header("➕ Yeni İş Atama")
        workers = pd.read_sql("SELECT email, name FROM users WHERE role='worker'", conn)
        with st.form("task_form"):
            t_title = st.text_input("İş Başlığı / ID")
            t_worker = st.selectbox("Personel", workers['email'].tolist())
            t_city = st.selectbox("Şehir", SEHIRLER)
            t_desc = st.text_area("İş Açıklaması")
            if st.form_submit_button("Atama Yap"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city) VALUES (?,?,?,?,?)",
                             (t_worker, t_title, t_desc, 'Bekliyor', t_city))
                conn.commit(); st.success("İş başarıyla atandı!"); st.rerun()

    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Mail Onayları")
        tasks = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        if tasks.empty:
            st.info("✅ Onay Bekleyen Atama Yok")
        else:
            st.dataframe(tasks)

    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Yönetimi")
        tasks = pd.read_sql("SELECT * FROM tasks WHERE hakedis_durum='Hak Ediş Bekliyor'", conn)
        if tasks.empty:
            st.info("✅ Hak Ediş Bekleyen Atama Yok")
        else:
            st.dataframe(tasks)
            if st.button("Hakediş Raporunu Excel Al"):
                st.download_button("İndir", to_excel(tasks), "Hakedis.xlsx")

    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Envanter ve Zimmet")
        inv = pd.read_sql("SELECT * FROM inventory", conn)
        if inv.empty:
            st.warning("⚠️ Henüz kayıtlı envanter yok.")
        else:
            st.dataframe(inv, use_container_width=True)
            st.download_button("📋 Tüm Envanteri Excel İndir", to_excel(inv), "Envanter.xlsx")
        
        with st.expander("➕ Yeni Zimmet Ekle"):
            workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist()
            with st.form("inv_add"):
                item = st.text_input("Malzeme Adı")
                target = st.selectbox("Personel", workers)
                qty = st.number_input("Adet", 1)
                if st.form_submit_button("Zimmetle"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)",
                                 (item, target, qty, st.session_state['user_name']))
                    conn.commit(); st.rerun()

    elif cp == "👥 Kullanıcılar":
        st.header("👥 Kullanıcı Yönetimi")
        users = pd.read_sql("SELECT name, email, role, title FROM users", conn)
        st.dataframe(users, use_container_width=True)
        
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("u_add"):
                nu_email = st.text_input("E-post")
                nu_name = st.text_input("Ad Soyad")
                nu_title = st.text_input("Unvan")
                nu_pass = st.text_input("Şifre", type='password')
                nu_role = st.selectbox("Yetki", ["worker", "admin"])
                if st.form_submit_button("Kaydet"):
                    hp = hashlib.sha256(nu_pass.encode()).hexdigest()
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (nu_email, hp, nu_role, nu_name, nu_title, ""))
                    conn.commit(); st.rerun()
