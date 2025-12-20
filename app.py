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
    conn = sqlite3.connect('saha_yonetim_v19.db', check_same_thread=False)
    c = conn.cursor()
    # Kullanıcılar tablosu
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)')
    # İşler tablosu (Hatalı parantez burada düzeltildi)
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT)''')
    # Zimmet tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    # Varsayılan Yönetici Hesabı (Eğer yoksa oluşturur)
    pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Ahmet Salça', 'Genel Müdür')", (pw,))
    conn.commit()
    return conn

def get_welcome_message(name):
    # Sistem saatine göre dinamik karşılama
    hour = datetime.now().hour
    if 5 <= hour < 12: msg = "Günaydın"
    elif 12 <= hour < 18: msg = "İyi Günler"
    elif 18 <= hour < 24: msg = "İyi Akşamlar"
    else: msg = "İyi Geceler"
    return f"✨ {msg} **{name}**, İyi Çalışmalar!"

conn = init_db()
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. RAPORLAMA FONKSİYONLARI ---
def create_word(row):
    doc = Document()
    doc.add_heading('SAHA İŞ RAPORU', 0)
    doc.add_paragraph(f"İş: {row['title']}\nSorumlu: {row['assigned_to']}\nTarih: {row['updated_at']}")
    doc.add_heading('Rapor Notu', level=2)
    doc.add_paragraph(str(row['report']))
    if row['photos_json']:
        try:
            photos = json.loads(row['photos_json'])
            for p_hex in photos:
                doc.add_picture(io.BytesIO(bytes.fromhex(p_hex)), width=Inches(3))
        except: pass
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

def create_excel(row):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    # Fotoğraf verisini Excel tablosundan çıkar (hata vermemesi için)
    clean_row = {k: v for k, v in row.items() if k != 'photos_json'}
    df = pd.DataFrame([clean_row])
    df.to_excel(writer, index=False, sheet_name='Ozet')
    writer.close(); return output.getvalue()

# --- 3. ARAYÜZ ---
st.set_page_config(page_title="Saha Takip v19", layout="wide")

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
                    'logged_in': True, 
                    'user_email': u[0], 
                    'role': u[2], 
                    'user_name': u[3], 
                    'user_title': u[4],
                    'page': "🏠 Ana Sayfa"
                })
                st.rerun()
            else: st.error("E-posta veya şifre hatalı!")
else:
    # --- MODERN YAN MENÜ ---
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.caption(f"🏷️ {st.session_state['user_title']}")
    st.sidebar.markdown("---")
    
    # Menü Butonları (Kutucuklu ve Emojili)
    if st.session_state['role'] == 'admin':
        menu = ["🏠 Ana Sayfa", "➕ İş Atama & Takip", "✅ Tamamlanan İşler", "📦 Zimmet/Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Üstüme Atanan İşler", "📜 Tamamlanan İşlerim", "🎒 Zimmetim"]

    for item in menu:
        if st.sidebar.button(item, use_container_width=True):
            st.session_state.page = item

    st.sidebar.markdown("---")
    # Çıkış Butonu (Kullanıcı Yönet
