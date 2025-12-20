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
    conn = sqlite3.connect('saha_yonetim_lokal.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT)'''))
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    # Varsayılan Admin Hesabı
    pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Ahmet Salça', 'Genel Müdür')", (pw,))
    conn.commit()
    return conn

def get_welcome_message(name):
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
    doc.add_heading('İŞ RAPORU', 0)
    doc.add_paragraph(f"İş: {row['title']}\nSorumlu: {row['assigned_to']}\nTarih: {row['updated_at']}")
    doc.add_heading('Rapor Notu', level=2)
    doc.add_paragraph(str(row['report']))
    if row['photos_json']:
        photos = json.loads(row['photos_json'])
        for p_hex in photos:
            try: doc.add_picture(io.BytesIO(bytes.fromhex(p_hex)), width=Inches(3))
            except: pass
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

def create_excel(row):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df = pd.DataFrame([row]).drop('photos_json', axis=1)
    df.to_excel(writer, index=False, sheet_name='Ozet')
    if row['photos_json']:
        photos = json.loads(row['photos_json'])
        img_data = io.BytesIO(bytes.fromhex(photos[0]))
        writer.sheets['Ozet'].insert_image('G2', 'img.png', {'image_data': img_data, 'x_scale': 0.1, 'y_scale': 0.1})
    writer.close(); return output.getvalue()

# --- 3. ARAYÜZ ---
st.set_page_config(page_title="Saha Yönetim v18", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Giriş Paneli")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            u = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (e, make_hash(p))).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4]})
                st.rerun()
            else: st.error("Hatalı bilgiler!")
else:
    # --- MODERNIZE SIDEBAR ---
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.caption(f"🏷️ {st.session_state['user_title']}")
    st.sidebar.markdown("---")
    
    # Menü Butonları
    pages = ["🏠 Ana Sayfa"]
    if st.session_state['role'] == 'admin':
        pages += ["➕ İş Atama", "✅ Tamamlanan İşler", "📦 Zimmet Takibi", "👥 Kullanıcı Yönetimi"]
    else:
        pages += ["⏳ Üstüme Atanan İşler", "📜 İş Geçmişim", "🎒 Zimmetim"]

    for p in pages:
        if st.sidebar.button(p, use_container_width=True):
            st.session_state.current_page = p

    st.sidebar.markdown("---")
    if st.sidebar.button("🔴 Güvenli Çıkış", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

    if 'current_page' not in st.session_state: st.session_state.current_page = "🏠 Ana Sayfa"
    choice = st.session_state.current_page

    # --- SAYFALAR ---
    if choice == "🏠 Ana Sayfa":
        st.info(get_welcome_message(st.session_state['user_name']))
        q = "SELECT status FROM tasks" if st.session_state['role'] == 'admin' else f"SELECT status FROM tasks WHERE assigned_to='{st.session_state['user_email']}'"
        df_stats = pd.read_sql(q, conn)
        c1, c2 = st.columns(2)
        c1.metric("📌 Bekleyen", len(df_stats[df_stats['status']=='Bekliyor']))
        c2.metric("✅ Tamamlanan", len(df_stats[df_stats['status']=='Tamamlandı']))

    elif choice == "✅ Tamamlanan İşler":
        st.header("📑 Rapor Arşivi")
        df_d = pd.read_sql("SELECT * FROM tasks WHERE status='Tamamlandı'", conn)
        for _, row in df_d.iterrows():
            with st.expander(f"📍 {row['title']} - {row['assigned_to']}"):
                st.write(f"Not: {row['report']}")
                col1, col2 = st.columns(2)
                col1.download_button("📄 Word", data=create_word(row), file_name=f"{row['id']}.docx", key=f"w{row['id']}")
                col2.download_button("📊 Excel", data=create_excel(row), file_name=f"{row['id']}.xlsx", key=f"e{row['id']}")

    elif choice == "➕ İş Atama":
        workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)
        with st.form("yeni"):
            t, w, d = st.text_input("Başlık"), st.selectbox("Personel", workers['email']), st.text_area("Detay")
            if st.form_submit_button("Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)", (w, t, d, 'Bekliyor'))
                conn.commit(); st.success("İş başarıyla atandı!")

    elif choice == "👥 Kullanıcı Yönetimi":
        with st.form("k_ekle"):
            ne, nn, nt, np, nr = st.text_input("E-posta"), st.text_input("Ad Soyad"), st.text_input("Unvan"), st.text_input("Şifre"), st.selectbox("Rol", ["worker", "admin"])
            if st.form_submit_button("Kullanıcıyı Kaydet"):
                conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ne, make_hash(np), nr, nn, nt))
                conn.commit(); st.success("Eklendi!"); st.rerun()
        st.dataframe(pd.read_sql("SELECT name, email, title FROM users", conn))

    elif choice == "⏳ Üstüme Atanan İşler":
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']}"):
                st.write(r['description'])
                rep = st.text_area("Raporun", key=f"r{r['id']}")
                fots = st.file_uploader("Fotoğraflar", accept_multiple_files=True, key=f"f{r['id']}")
                if st.button("İşi Bitir", key=f"b{r['id']}"):
                    if fots:
                        p_json = json.dumps([f.read().hex() for f in fots])
                        conn.execute("UPDATE tasks SET status='Tamamlandı', report=?, photos_json=?, updated_at=? WHERE id=?", (rep, p_json, datetime.now().strftime("%H:%M"), r['id']))
                        conn.commit(); st.rerun()
