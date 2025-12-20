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
    conn = sqlite3.connect('saha_takip_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    # Varsayılan Admin
    pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Ahmet Salça', 'Müdür')", (pw,))
    conn.commit()
    return conn

def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. RAPORLAMA FONKSİYONU ---
def create_word(row):
    doc = Document()
    doc.add_heading('SAHA İŞ RAPORU', 0)
    doc.add_paragraph(f"İş: {row['title']}\nSorumlu: {row['assigned_to']}\nTarih: {row.get('updated_at', 'Belirtilmedi')}")
    doc.add_heading('Rapor Notu', level=2)
    doc.add_paragraph(str(row.get('report', 'Not girilmemiş.')))
    if row.get('photos_json'):
        try:
            photos = json.loads(row['photos_json'])
            for p_hex in photos:
                doc.add_picture(io.BytesIO(bytes.fromhex(p_hex)), width=Inches(3))
        except: pass
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

# --- 3. ANA ARAYÜZ ---
st.set_page_config(page_title="Saha Takip v23", layout="wide")
conn = init_db()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Şirket Giriş Paneli")
    with st.form("login_form"):
        e = st.text_input("E-posta")
        p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş Yap"):
            u = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (e, make_hash(p))).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4], 'page': "🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı bilgiler!")
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

    # --- SAYFA İÇERİKLERİ (Boş ekranı düzelten kısım) ---
    cp = st.session_state.page

    if cp == "🏠 Ana Sayfa":
        st.info(f"✨ İyi Çalışmalar **{st.session_state['user_name']}**!")
        q = "SELECT status FROM tasks" if st.session_state['role'] == 'admin' else f"SELECT status FROM tasks WHERE assigned_to='{st.session_state['user_email']}'"
        df_tasks = pd.read_sql(q, conn)
        c1, c2 = st.columns(2)
        c1.metric("📌 Bekleyen İşler", len(df_tasks[df_tasks['status']=='Bekliyor']) if not df_tasks.empty else 0)
        c2.metric("✅ Tamamlanan İşler", len(df_tasks[df_tasks['status']=='Tamamlandı']) if not df_tasks.empty else 0)

    elif cp == "➕ İş Atama & Takip":
        st.header("➕ Yeni İş Atama")
        workers = pd.read_sql("SELECT email, name FROM users", conn) # Tüm kullanıcıları çekiyoruz
        with st.form("task_form"):
            t = st.text_input("İş Başlığı")
            w = st.selectbox("Personel Seçin", options=workers['email'].tolist())
            d = st.text_area("İş Detayı")
            if st.form_submit_button("Görevi Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)", (w, t, d, 'Bekliyor'))
                conn.commit(); st.success("İş başarıyla atandı!")

    elif cp == "✅ Tamamlanan İşler":
        st.header("📑 Tamamlanan İş Arşivi")
        df_done = pd.read_sql("SELECT * FROM tasks WHERE status='Tamamlandı' ORDER BY id DESC", conn)
        if df_done.empty: st.info("Henüz tamamlanan iş yok.")
        for _, r in df_done.iterrows():
            with st.expander(f"📍 {r['title']} - {r['assigned_to']}"):
                st.write(f"Not: {r['report']}"); st.write(f"Tarih: {r['updated_at']}")
                st.download_button("📄 Word İndir", data=create_word(r.to_dict()), file_name=f"Rapor_{r['id']}.docx", key=f"d_{r['id']}")

    elif cp == "📦 Zimmet/Envanter" or cp == "🎒 Zimmetim":
        st.header("📦 Envanter ve Zimmet")
        if st.session_state['role'] == 'admin':
            st.subheader("Mevcut Zimmetler")
            st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)
            st.markdown("---")
            users = pd.read_sql("SELECT email, name FROM users", conn)
            with st.form("inv_form"):
                item = st.text_input("Malzeme Adı")
                target = st.selectbox("Zimmetlenecek Personel", options=users['email'].tolist())
                qty = st.number_input("Adet", 1)
                if st.form_submit_button("Zimmetle"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (item, target, qty, st.session_state['user_name']))
                    conn.commit(); st.rerun()
        else:
            st.table(pd.read_sql(f"SELECT item_name as 'Malzeme', quantity as 'Adet' FROM inventory WHERE assigned_to='{st.session_state['user_email']}'", conn))

    elif cp == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı"):
            with st.form("u_form"):
                ne, nn = st.text_input("E-posta"), st.text_input("Ad Soyad")
                nt = st.selectbox("Unvan", ["Müdür", "Saha Çalışanı", "Teknisyen", "Ofis"])
                np, nr = st.text_input("Şifre"), st.selectbox("Yetki", ["worker", "admin"])
                if st.form_submit_button("Kaydet"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ne, make_hash(np), nr, nn, nt))
                    conn.commit(); st.success("Eklendi!"); st.rerun()
        st.table(pd.read_sql("SELECT name as 'Ad Soyad', email, title as 'Unvan', role as 'Yetki' FROM users", conn))

    elif cp == "⏳ Üstüme Atanan İşler":
        st.header("⏳ Bekleyen Görevlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        if tasks.empty: st.info("Bekleyen işiniz yok.")
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']}"):
                st.write(r['description'])
                rep = st.text_area("Rapor", key=f"r_{r['id']}")
                fots = st.file_uploader("Fotoğraflar", accept_multiple_files=True, key=f"f_{r['id']}")
                if st.button("Bitir", key=f"b_{r['id']}"):
                    if fots:
                        p_json = json.dumps([f.read().hex() for f in fots])
                        conn.execute("UPDATE tasks SET status='Tamamlandı', report=?, photos_json=?, updated_at=? WHERE id=?", (rep, p_json, datetime.now().strftime("%d/%m %H:%M"), r['id']))
                        conn.commit(); st.rerun()
                    else: st.error("Fotoğraf yükleyin!")

    elif cp == "📜 Tamamlanan İşlerim":
        st.header("📜 Geçmiş İşlerim")
        st.table(pd.read_sql(f"SELECT title, report, updated_at FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Tamamlandı'", conn))
