import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
from docx import Document
from docx.shared import Inches

# --- 1. VERİTABANI YAPILANDIRMASI ---
def init_db():
    conn = sqlite3.connect('isletme_v9_kurumsal.db', check_same_thread=False)
    c = conn.cursor()
    # Kullanıcılar: Unvan (title) eklendi
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)''')
    # Görevler: Tüm detaylar eklendi
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photo BLOB, updated_at TEXT)''')
    # Zimmet: Düzenleyen bilgisi eklendi
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    # Varsayılan Admin ve İstediğiniz Deneme Kullanıcısı
    admin_pw = hashlib.sha256("1234".encode()).hexdigest()
    worker_pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Genel Müdür', 'Yönetici')", (admin_pw,))
    c.execute("INSERT OR IGNORE INTO users VALUES ('deneme123@dev.com', ?, 'worker', 'Deneme Kullanıcı', 'Saha Ekibi')", (worker_pw,))
    
    conn.commit()
    return conn

conn = init_db()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- 2. RAPORLAMA FONKSİYONLARI ---
def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Rapor')
    writer.close()
    return output.getvalue()

def to_word_report(df_tasks):
    doc = Document()
    doc.add_heading('KURUMSAL İŞ BİTİRME RAPORU', 0)
    for idx, row in df_tasks.iterrows():
        doc.add_heading(f"İŞ: {row['Başlık']}", level=1)
        doc.add_paragraph(f"Sorumlu: {row['Çalışan']}")
        doc.add_paragraph(f"Tarih: {row['Tarih']}")
        doc.add_paragraph(f"Durum Notu: {row['Rapor']}")
        if row['photo']:
            try:
                img_stream = io.BytesIO(row['photo'])
                doc.add_picture(img_stream, width=Inches(4))
            except: pass
        doc.add_page_break()
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. ANA ARAYÜZ ---
st.set_page_config(page_title="İşletme Yönetim Paneli", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Şirket Portalı Girişi")
    e_in = st.text_input("E-posta")
    p_in = st.text_input("Şifre", type='password')
    if st.button("Giriş Yap"):
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (e_in, make_hash(p_in)))
        user = c.fetchone()
        if user:
            st.session_state.update({'logged_in':True, 'user_email':user[0], 'role':user[2], 'user_name':user[3], 'user_title':user[4]})
            st.rerun()
        else: st.error("E-posta veya şifre hatalı!")
else:
    # Sidebar
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.write(f"🏷️ {st.session_state['user_title']}")
    
    if st.session_state['role'] == 'admin':
        menu = ["Ana Sayfa", "İş Atama & Takip", "Zimmet/Envanter Yönetimi", "Kullanıcı Yönetimi"]
    else:
        menu = ["Üstüme Atanan İşler", "Tamamlanan İşlerim", "Zimmetim & Envanter", "Fiyat Hesaplama"]
    
    choice = st.sidebar.radio("Menü", menu)
    if st.sidebar.button("🚪 Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()

    # ---
