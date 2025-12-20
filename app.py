import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
from docx import Document
from docx.shared import Inches

# --- 1. VERİTABANI YÖNETİMİ ---
def init_db():
    conn = sqlite3.connect('isletme_saha_v11.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photo BLOB, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Genel Müdür', 'Yönetici')", (pw,))
    c.execute("INSERT OR IGNORE INTO users VALUES ('deneme123@dev.com', ?, 'worker', 'Deneme Çalışan', 'Saha Ekibi')", (pw,))
    conn.commit()
    return conn

conn = init_db()

def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

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

# --- 2. ARAYÜZ ---
st.set_page_config(page_title="Şirket Yönetim Sistemi", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Giriş Paneli")
    e = st.text_input("E-posta")
    p = st.text_input("Şifre", type='password')
    if st.button("Sisteme Giriş"):
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
    
    if st.session_state['role'] == 'admin':
        menu = ["Ana Sayfa", "İş Atama & Takip", "Zimmet/Envanter", "Kullanıcı Yönetimi"]
    else:
        menu = ["Üstüme Atanan İşler", "Tamamlanan İşlerim", "Zimmetim"]
    
    choice = st.sidebar.radio("Menü", menu)
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- EKRANLAR ---
    if choice == "Ana Sayfa":
        st.header("📊 Genel Durum")
        tasks = pd.read_sql("SELECT status FROM tasks", conn)
        c1, c2 = st.columns(2)
        c1.metric("📌 Bekleyen İşler", len(tasks[tasks['status']=='Bekliyor']))
        c2.metric("✅ Tamamlanan İşler", len(tasks[tasks['status']=='Tamamlandı']))

    elif choice == "İş Atama & Takip":
        t1, t2 = st.tabs(["➕ Yeni İş Ata", "📑 Saha Raporları"])
        with t1:
            workers = pd.read_sql("SELECT email, name FROM users WHERE role='worker'", conn)
            with st.form("is_ata"):
                tit = st.text_input("İş Başlığı")
                who = st.selectbox("Personel", workers['email'])
                dsc = st.text_area("İş Detayı / Adres")
                if st.form_submit_button("Görevi Gönder"):
                    conn.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)", (who, tit, dsc, 'Bekliyor'))
                    conn.commit()
                    st.success("İş atandı!")
        with t2:
            df_d = pd.read_sql("SELECT assigned_to as 'Çalışan', title as 'Başlık', report as 'Rapor', updated_at as 'Tarih', photo FROM tasks WHERE status='Tamamlandı'", conn)
            if not df_d.empty:
                st.download_button("📝 Word Raporu Al (Fotoğraflı)", data=get_word_report(df_d), file_name="saha_raporu.docx")
                st.dataframe(df_d.drop('photo', axis=1), use_container_width=True)

    elif choice == "Kullanıcı Yönetimi":
        st.header("👥 Personel Listesi")
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("u_add"):
                n_e, n_n = st.columns(2)
                email_val = n_e.text_input("E-posta")
                name_val = n_n.text_input("Ad Soyad")
                n_t = st.selectbox("Unvan", ["Müdür", "Müdür Yrd.", "Tekniker", "Saha Personeli", "Ofis"])
                n_p = st.text_input("Şifre", type='password')
                n_r = st.selectbox("Yetki", ["worker", "admin"])
                if st.form_submit_button("Kaydet"):
                    conn.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", (email_val, make_hash(n_p), n_r, name_val, n_t))
                    conn.commit()
                    st.rerun()
        u_list = pd.read_sql("SELECT name as 'Ad Soyad', email as 'E-posta', title as 'Unvan' FROM users", conn)
        st.dataframe(u_list, use_container_width=True)
        for _, r in u_list.iterrows():
            if r['E-posta'] != 'admin@sirket.com':
                if st.button(f"🗑️ {r['Ad Soyad']} Sil", key=r['E-posta']):
                    conn.execute("DELETE FROM users WHERE email=?", (r['E-posta'],))
                    conn.commit()
                    st.rerun()

    elif choice == "Üstüme Atanan İşler":
        st.header("⏳ Tamamlanacak İşlerim")
        my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        if my_tasks.empty: st.info("Şu an bekleyen bir işiniz bulunmuyor.")
        for _, row in my_tasks.iterrows():
            with st.expander(f"📍 {row['title']}"):
                st.write(f"**Açıklama:** {row['description']}")
                rep = st.text_area("Rapor Notunuz", key=f"r_{row['id']}")
                img = st.file_uploader("İş Sonu Fotoğrafı", key=f"i_{row['id']}")
                if st.button("İşi Tamamla", key=f"b_{row['id']}"):
                    if img:
                        conn.execute("UPDATE tasks SET status='Tamamlandı', report=?, photo=?, updated_at=? WHERE id=?", 
                                     (rep, img.read(), datetime.now().strftime("%d/%m/%Y %H:%M"), row['id']))
                        conn.commit()
                        st.success("İş raporlandı!")
                        st.rerun()
                    else: st.error("Fotoğraf yüklemek zorunludur!")

    elif choice == "Tamamlanan İşlerim":
        st.header("✅ Geçmiş İşlerim")
        df_history = pd.read_sql(f"SELECT title as 'İş Başlığı', report as 'Personel Notu', updated_at as 'Tamamlanma Tarihi' FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Tamamlandı' ORDER BY updated_at DESC", conn)
        if df_history.empty:
            st.warning("Henüz tamamladığınız bir iş bulunmuyor.")
        else:
            st.table(df_history)

    elif choice == "Zimmetim" or choice == "Zimmet/Envanter":
        st.header("📦 Zimmet & Envanter")
        if st.session_state['role'] == 'admin':
            df_i = pd.read_sql("SELECT item_name as 'Eşya', assigned_to as 'Personel', quantity as 'Adet', updated_by as 'Düzenleyen' FROM inventory", conn)
            st.dataframe(df_i, use_container_width=True)
        else:
            df_i = pd.read_sql(f"SELECT item_name as 'Eşya', quantity as 'Adet', updated_by as 'Ekleyen' FROM inventory WHERE assigned_to='{st.session_state['user_email']}'", conn)
            st.table(df_i)
        
        with st.expander("➕ Envanter Kaydı Oluştur"):
            with st.form("inv_add"):
                i_n = st.text_input("Eşya Adı")
                i_q = st.number_input("Adet", 1)
                target = st.session_state['user_email'] if st.session_state['role'] == 'worker' else st.text_input("Personel E-posta (Zimmetlenecek Kişi)")
                if st.form_submit_button("Kaydet"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", 
                                 (i_n, target, i_q, st.session_state['user_name']))
                    conn.commit()
                    st.rerun()
