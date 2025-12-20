import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
from docx import Document
from docx.shared import Inches

# --- 1. VERİTABANI: KENDİ KENDİNİ ONARAN SİSTEM ---
def init_db():
    # Veritabanı adını tamamen yeni bir isim yapıyoruz ki eski hatalar silinsin
    conn = sqlite3.connect('isletme_saha_v10.db', check_same_thread=False)
    c = conn.cursor()
    
    # Tabloları oluştur
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photo BLOB, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    # Sütun kontrolü (Hata almanı engelleyen en önemli kısım)
    existing_columns = [col[1] for col in c.execute("PRAGMA table_info(tasks)").fetchall()]
    if 'title' not in existing_columns: c.execute("ALTER TABLE tasks ADD COLUMN title TEXT")
    if 'photo' not in existing_columns: c.execute("ALTER TABLE tasks ADD COLUMN photo BLOB")
    
    # Varsayılan Kullanıcılar
    pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Genel Müdür', 'Yönetici')", (pw,))
    c.execute("INSERT OR IGNORE INTO users VALUES ('deneme123@dev.com', ?, 'worker', 'Deneme Çalışan', 'Saha Ekibi')", (pw,))
    
    conn.commit()
    return conn

conn = init_db()

def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. RAPORLAMA ---
def get_word_report(df):
    doc = Document()
    doc.add_heading('SAHA İŞ BİTİRME RAPORU', 0)
    for _, row in df.iterrows():
        doc.add_heading(f"İŞ: {row['Başlık']}", level=1)
        doc.add_paragraph(f"Personel: {row['Çalışan']} | Tarih: {row['Tarih']}")
        doc.add_paragraph(f"Not: {row['Rapor']}")
        if row['photo']:
            try: doc.add_picture(io.BytesIO(row['photo']), width=Inches(4))
            except: pass
        doc.add_page_break()
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. ARAYÜZ ---
st.set_page_config(page_title="Şirket Yönetim v10", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Giriş Paneli")
    e = st.text_input("E-posta")
    p = st.text_input("Şifre", type='password')
    if st.button("Giriş"):
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (e, make_hash(p)))
        u = c.fetchone()
        if u:
            st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4]})
            st.rerun()
        else: st.error("Hatalı giriş!")
else:
    st.sidebar.title(f"👋 {st.session_state['user_name']}")
    st.sidebar.caption(f"📌 {st.session_state['user_title']}")
    
    # Menü Belirleme
    if st.session_state['role'] == 'admin':
        menu = ["Ana Sayfa", "İş Atama & Takip", "Zimmet/Envanter", "Kullanıcı Yönetimi"]
    else:
        menu = ["Üstüme Atanan İşler", "Tamamlanan İşlerim", "Zimmetim", "Hesaplayıcı"]
    
    choice = st.sidebar.radio("Menü", menu)
    if st.sidebar.button("Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- EKRANLAR ---
    if choice == "Ana Sayfa":
        st.header("📊 Genel Durum")
        tasks = pd.read_sql("SELECT status FROM tasks", conn)
        c1, c2 = st.columns(2)
        c1.metric("Bekleyen İşler", len(tasks[tasks['status']=='Bekliyor']))
        c2.metric("Tamamlananlar", len(tasks[tasks['status']=='Tamamlandı']))

    elif choice == "İş Atama & Takip":
        t1, t2 = st.tabs(["➕ Yeni İş Ata", "📑 Tamamlanan İşler"])
        with t1:
            workers = pd.read_sql("SELECT email, name FROM users WHERE role='worker'", conn)
            with st.form("is_ata"):
                tit = st.text_input("İş Başlığı")
                who = st.selectbox("Çalışan", workers['email'])
                dsc = st.text_area("Detaylar")
                if st.form_submit_button("Ata"):
                    conn.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)", (who, tit, dsc, 'Bekliyor'))
                    conn.commit()
                    st.success("İş başarıyla atandı!")
        with t2:
            df_d = pd.read_sql("SELECT assigned_to as 'Çalışan', title as 'Başlık', report as 'Rapor', updated_at as 'Tarih', photo FROM tasks WHERE status='Tamamlandı'", conn)
            if not df_d.empty:
                st.download_button("📝 Word Raporu (Fotoğraflı)", data=get_word_report(df_d), file_name="saha_raporu.docx")
                st.dataframe(df_d.drop('photo', axis=1))
            else: st.info("Henüz tamamlanan iş yok.")

    elif choice == "Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Ekle"):
            with st.form("u_add"):
                n_e = st.text_input("E-posta")
                n_n = st.text_input("Ad Soyad")
                n_t = st.selectbox("Unvan", ["Müdür", "Müdür Yrd.", "Saha Ekibi", "Tekniker"])
                n_p = st.text_input("Şifre", type='password')
                n_r = st.selectbox("Yetki", ["worker", "admin"])
                if st.form_submit_button("Ekle"):
                    conn.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", (n_e, make_hash(n_p), n_r, n_n, n_t))
                    conn.commit()
                    st.rerun()
        u_list = pd.read_sql("SELECT name, email, title FROM users", conn)
        st.table(u_list)
        for _, r in u_list.iterrows():
            if r['email'] != 'admin@sirket.com':
                if st.button(f"🗑️ {r['name']} Sil", key=r['email']):
                    conn.execute("DELETE FROM users WHERE email=?", (r['email'],))
                    conn.commit()
                    st.rerun()

    elif choice == "Üstüme Atanan İşler":
        st.header("⏳ Bekleyen İşlerim")
        my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        for _, row in my_tasks.iterrows():
            with st.expander(f"📍 {row['title']}"):
                st.write(row['description'])
                rep = st.text_area("Rapor Notu", key=f"r_{row['id']}")
                img = st.file_uploader("Fotoğraf", key=f"i_{row['id']}")
                if st.button("Bitir", key=f"b_{row['id']}"):
                    if img:
                        conn.execute("UPDATE tasks SET status='Tamamlandı', report=?, photo=?, updated_at=? WHERE id=?", 
                                     (rep, img.read(), datetime.now().strftime("%d/%m/%Y %H:%M"), row['id']))
                        conn.commit()
                        st.rerun()
                    else: st.error("Lütfen fotoğraf yükleyin!")

    elif choice == "Zimmetim" or choice == "Zimmet/Envanter":
        st.header("📦 Zimmet & Envanter")
        if st.session_state['role'] == 'admin':
            df_i = pd.read_sql("SELECT * FROM inventory", conn)
            st.dataframe(df_i)
        else:
            df_i = pd.read_sql(f"SELECT item_name, quantity FROM inventory WHERE assigned_to='{st.session_state['user_email']}'", conn)
            st.table(df_i)
        
        with st.form("inv_add"):
            i_n = st.text_input("Eşya Adı")
            i_q = st.number_input("Adet", 1)
            target = st.session_state['user_email'] if st.session_state['role'] == 'worker' else st.text_input("Kime (E-posta)")
            if st.form_submit_button("Sisteme İşle"):
                conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", 
                             (i_n, target, i_q, st.session_state['user_name']))
                conn.commit()
                st.rerun()
