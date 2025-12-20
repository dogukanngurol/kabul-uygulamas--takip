import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
from docx import Document
from docx.shared import Inches

# --- 1. VERİTABANI VE AYARLAR ---
def init_db():
    conn = sqlite3.connect('isletme_v8_final.db', check_same_thread=False)
    c = conn.cursor()
    # Kullanıcılar tablosuna 'title' (Unvan) sütunu eklendi
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photo BLOB, updated_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    # Varsayılan Admin ve Çalışan (Unvanlarıyla birlikte)
    admin_pw = hashlib.sha256("1234".encode()).hexdigest()
    worker_pw = hashlib.sha256("1234".encode()).hexdigest()
    
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Genel Müdür', 'Genel Müdür')", (admin_pw,))
    c.execute("INSERT OR IGNORE INTO users VALUES ('deneme123@dev.com', ?, 'worker', 'Deneme Çalışan', 'Saha Personeli')", (worker_pw,))
    
    conn.commit()
    return conn

conn = init_db()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- 2. YARDIMCI FONKSİYONLAR ---
def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Rapor')
    writer.close()
    return output.getvalue()

def to_word_with_images(df_tasks):
    doc = Document()
    doc.add_heading('SAHA İŞ BİTİRME RAPORU', 0)
    for idx, row in df_tasks.iterrows():
        doc.add_heading(f"İş: {row['Başlık']}", level=1)
        doc.add_paragraph(f"Personel: {row['Çalışan']}")
        doc.add_paragraph(f"Tarih: {row['Tarih']}")
        doc.add_paragraph(f"Personel Notu: {row['Rapor']}")
        if row['photo']:
            try:
                image_stream = io.BytesIO(row['photo'])
                doc.add_picture(image_stream, width=Inches(4.5))
            except: pass
        doc.add_page_break()
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. ANA ARAYÜZ ---
st.set_page_config(page_title="İşletme Yönetim Sistemi v8", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Şirket Giriş Paneli")
    e_input = st.text_input("E-posta")
    p_input = st.text_input("Şifre", type='password')
    if st.button("Giriş Yap"):
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (e_input, make_hash(p_input)))
        u = c.fetchone()
        if u:
            st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4]})
            st.rerun()
        else: st.error("Giriş bilgileri hatalı!")
else:
    st.sidebar.title(f"👋 {st.session_state['user_name']}")
    st.sidebar.caption(f"📌 {st.session_state['user_title']}")
    
    menu = ["Ana Sayfa", "İş Atama/Takip", "Zimmet & Envanter", "Kullanıcı Yönetimi"] if st.session_state['role'] == 'admin' else ["İşlerim", "Zimmetim", "Hesap Makinesi"]
    choice = st.sidebar.radio("Menü", menu)
    
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- ADMIN: KULLANICI YÖNETİMİ (YENİ) ---
    if choice == "Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        
        # Kullanıcı Ekleme Formu
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("kullanici_ekle"):
                new_email = st.text_input("E-posta Adresi")
                new_name = st.text_input("Ad Soyad")
                new_title = st.selectbox("Unvan", ["Müdür", "Müdür Yardımcısı", "Çalışan", "Saha Personeli", "Tekniker"])
                new_pass = st.text_input("Şifre", type='password')
                new_role = st.selectbox("Sistem Yetkisi", ["worker", "admin"])
                if st.form_submit_button("Kullanıcıyı Kaydet"):
                    if new_email and new_name and new_pass:
                        c = conn.cursor()
                        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", 
                                  (new_email, make_hash(new_pass), new_role, new_name, new_title))
                        conn.commit()
                        st.success(f"{new_name} başarıyla eklendi!")
                        st.rerun()
                    else: st.warning("Lütfen tüm alanları doldurun.")

        # Kullanıcı Listesi ve Silme
        st.subheader("Mevcut Kullanıcılar")
        df_users = pd.read_sql("SELECT name as 'Ad Soyad', email as 'E-posta', title as 'Unvan', role as 'Yetki' FROM users", conn)
        
        for idx, row in df_users.iterrows():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            col1.write(row['Ad Soyad'])
            col2.write(row['E-posta'])
            col3.write(row['Unvan'])
            if col4.button("❌ Sil", key=f"del_{row['E-posta']}"):
                if row['E-posta'] == 'admin@sirket.com':
                    st.error("Ana admin hesabı silinemez!")
                else:
                    conn.execute("DELETE FROM users WHERE email=?", (row['E-posta'],))
                    conn.commit()
                    st.success("Kullanıcı silindi.")
                    st.rerun()
            st.divider()

    # --- DİĞER EKRANLAR (HIZLI ÖZET) ---
    elif choice == "Ana Sayfa":
        st.header("📊 Genel Durum")
        df_s = pd.read_sql("SELECT status FROM tasks", conn)
        st.metric("Bekleyen İşler", len(df_s[df_s['status']=='Bekliyor']))
        st.metric("Tamamlananlar", len(df_s[df_s['status']=='Tamamlandı']))

    elif choice == "İş Atama/Takip":
        tab1, tab2 = st.tabs(["Ata", "Rapor"])
        with tab1:
            workers = pd.read_sql("SELECT email, name, title FROM users WHERE role='worker'", conn)
            with st.form("ata"):
                t_tit = st.text_input("İş Başlığı")
                # Çalışan seçerken unvanını da gösteriyoruz
                worker_list = [f"{r['name']} ({r['title']}) - {r['email']}" for i, r in workers.iterrows()]
                t_sel = st.selectbox("Çalışan", worker_list)
                t_mail = t_sel.split(" - ")[-1]
                t_desc = st.text_area("Açıklama")
                if st.form_submit_button("Gönder"):
                    conn.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)", (t_mail, t_tit, t_desc, 'Bekliyor'))
                    conn.commit()
                    st.rerun()
        with tab2:
            df_done = pd.read_sql("SELECT assigned_to, title, report, updated_at, photo FROM tasks WHERE status='Tamamlandı'", conn)
            if not df_done.empty:
                st.download_button("📝 Fotoğraflı Word Raporu", data=to_word_with_images(df_done.rename(columns={'assigned_to':'Çalışan','title':'Başlık','report':'Rapor','updated_at':'Tarih'})), file_name="rapor.docx")

    elif choice == "Zimmet & Envanter":
        df_i = pd.read_sql("SELECT * FROM inventory", conn)
        st.download_button("📥 Excel İndir", data=to_excel(df_i), file_name="envanter.xlsx")
        st.dataframe(df_i, use_container_width=True)

    # --- ÇALIŞAN EKRANLARI ---
    elif choice == "İşlerim":
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        for _, r in tasks.iterrows():
            with st.expander(r['title']):
                notu = st.text_area("Not", key=f"n_{r['id']}")
                fot = st.file_uploader("Foto", key=f"f_{r['id']}")
                if st.button("Bitir", key=f"b_{r['id']}"):
                    if fot:
                        conn.execute
