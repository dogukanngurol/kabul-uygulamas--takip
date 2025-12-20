import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
from docx import Document
from docx.shared import Inches

# --- 1. VERİTABANI VE KARŞILAMA MANTIĞI ---
def init_db():
    # Hataları sıfırlamak için yeni sürüm veritabanı
    conn = sqlite3.connect('isletme_kurumsal_v14.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Genel Müdür', 'Yönetici')", (pw,))
    c.execute("INSERT OR IGNORE INTO users VALUES ('deneme123@dev.com', ?, 'worker', 'Deneme Çalışan', 'Saha Ekibi')", (pw,))
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
    doc.add_heading('SAHA İŞ RAPORU', 0)
    doc.add_paragraph(f"İş: {row['title']}\nPersonel: {row['assigned_to']}\nTarih: {row['updated_at']}")
    doc.add_heading('Rapor Notu', level=2)
    doc.add_paragraph(str(row['report']))
    if row['photos_json']:
        photos = json.loads(row['photos_json'])
        for p_hex in photos:
            try: doc.add_picture(io.BytesIO(bytes.fromhex(p_hex)), width=Inches(4))
            except: pass
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

def create_excel(row):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df = pd.DataFrame([row]).drop('photos_json', axis=1)
    df.to_excel(writer, index=False, sheet_name='Rapor')
    # Excel'e ilk fotoğrafı sığdır
    if row['photos_json']:
        photos = json.loads(row['photos_json'])
        img_data = io.BytesIO(bytes.fromhex(photos[0]))
        writer.sheets['Rapor'].insert_image('G2', 'img.png', {'image_data': img_data, 'x_scale': 0.1, 'y_scale': 0.1})
    writer.close(); return output.getvalue()

# --- 3. ARAYÜZ ---
st.set_page_config(page_title="Saha Yönetim v14", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Şirket Portalı")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş Yap"):
            u = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (e, make_hash(p))).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4]})
                st.rerun()
            else: st.error("Hatalı giriş!")
else:
    # Sidebar Karşılama ve Çıkış
    st.sidebar.subheader(st.session_state['user_name'])
    st.sidebar.caption(st.session_state['user_title'])
    
    if st.sidebar.button("🔴 Güvenli Çıkış Yap", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

    menu = ["Ana Sayfa", "İş Atama & Takip", "Tamamlanan İşler", "Zimmet/Envanter", "Kullanıcı Yönetimi"] if st.session_state['role'] == 'admin' else ["Üstüme Atanan İşler", "Tamamlanan İşlerim", "Zimmetim"]
    choice = st.sidebar.radio("Menü", menu)

    # --- EKRANLAR ---
    if choice == "Ana Sayfa":
        st.info(get_welcome_message(st.session_state['user_name']))
        tasks = pd.read_sql("SELECT status FROM tasks", conn)
        c1, c2 = st.columns(2)
        c1.metric("📌 Bekleyen İşler", len(tasks[tasks['status']=='Bekliyor']))
        c2.metric("✅ Tamamlanan İşler", len(tasks[tasks['status']=='Tamamlandı']))

    elif choice == "Tamamlanan İşler":
        st.header("📑 Tamamlanan İş Raporları")
        df_d = pd.read_sql("SELECT * FROM tasks WHERE status='Tamamlandı' ORDER BY updated_at DESC", conn)
        if df_d.empty: st.info("Henüz tamamlanan iş yok.")
        else:
            for _, row in df_d.iterrows():
                with st.expander(f"📍 {row['title']} ({row['assigned_to']})"):
                    st.write(f"**Tarih:** {row['updated_at']} | **Not:** {row['report']}")
                    col1, col2 = st.columns(2)
                    col1.download_button("📄 Word Olarak İndir", data=create_word(row), file_name=f"{row['title']}.docx", key=f"w_{row['id']}")
                    col2.download_button("📊 Excel Olarak İndir", data=create_excel(row), file_name=f"{row['title']}.xlsx", key=f"e_{row['id']}")

    elif choice == "İş Atama & Takip":
        workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)
        with st.form("ata"):
            t = st.text_input("İş Başlığı")
            w = st.selectbox("Personel", workers['email'])
            d = st.text_area("İş Detayı")
            if st.form_submit_button("Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)", (w, t, d, 'Bekliyor'))
                conn.commit(); st.success("İş Atandı!")

    elif choice == "Kullanıcı Yönetimi":
        with st.expander("➕ Yeni Kullanıcı"):
            with st.form("u"):
                ne, nn, nt, np, nr = st.text_input("E-posta"), st.text_input("Ad"), st.selectbox("Unvan", ["Müdür", "Tekniker", "Saha"]), st.text_input("Şifre"), st.selectbox("Rol", ["worker", "admin"])
                if st.form_submit_button("Ekle"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ne, make_hash(np), nr, nn, nt))
                    conn.commit(); st.rerun()
        st.table(pd.read_sql("SELECT name, email, title FROM users", conn))

    elif choice == "Üstüme Atanan İşler":
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        for _, r in tasks.iterrows():
            with st.expander(r['title']):
                rep = st.text_area("Rapor", key=f"n_{r['id']}")
                fots = st.file_uploader("Fotoğraflar", accept_multiple_files=True, key=f"f_{r['id']}")
                if st.button("Bitir", key=f"b_{r['id']}"):
                    if fots:
                        p_list = json.dumps([f.read().hex() for f in fots])
                        conn.execute("UPDATE tasks SET status='Tamamlandı', report=?, photos_json=?, updated_at=? WHERE id=?", (rep, p_list, datetime.now().strftime("%d/%m %H:%M"), r['id']))
                        conn.commit(); st.rerun()
                    else: st.error("Fotoğraf zorunludur!")

    elif choice == "Tamamlanan İşlerim":
        st.dataframe(pd.read_sql(f"SELECT title, report, updated_at FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Tamamlandı'", conn))

    elif choice == "Zimmetim" or choice == "Zimmet/Envanter":
        if st.session_state['role'] == 'admin':
            st.dataframe(pd.read_sql("SELECT * FROM inventory", conn))
        else:
            st.table(pd.read_sql(f"SELECT * FROM inventory WHERE assigned_to='{st.session_state['user_email']}'", conn))
        with st.form("inv"):
            n, q = st.text_input("Eşya"), st.number_input("Adet", 1)
            target = st.session_state['user_email'] if st.session_state['role'] == 'worker' else st.text_input("Kime")
            if st.form_submit_button("Kaydet"):
                conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (n, target, q, st.session_state['user_name']))
                conn.commit(); st.rerun()
