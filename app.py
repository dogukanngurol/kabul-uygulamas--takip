import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
from docx import Document
from docx.shared import Inches

# --- 1. VERİTABANI VE GÜVENLİK ---
def init_db():
    conn = sqlite3.connect('saha_takip_v21.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Ahmet Salça', 'Genel Müdür')", (pw,))
    conn.commit()
    return conn

def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

def get_welcome_message(name):
    hour = datetime.now().hour
    if 5 <= hour < 12: msg = "Günaydın"
    elif 12 <= hour < 18: msg = "İyi Günler"
    elif 18 <= hour < 24: msg = "İyi Akşamlar"
    else: msg = "İyi Geceler"
    return f"✨ {msg} **{name}**, İyi Çalışmalar!"

# --- 2. RAPORLAMA ---
def create_word(row):
    doc = Document()
    doc.add_heading('SAHA İŞ RAPORU', 0)
    doc.add_paragraph(f"İş: {row['title']}\nSorumlu: {row['assigned_to']}\nTarih: {row['updated_at']}")
    doc.add_heading('Rapor Notu', level=2)
    doc.add_paragraph(str(row['report']))
    if row.get('photos_json'):
        try:
            photos = json.loads(row['photos_json'])
            for p_hex in photos:
                doc.add_picture(io.BytesIO(bytes.fromhex(p_hex)), width=Inches(3))
        except: pass
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

# --- 3. ANA UYGULAMA ---
st.set_page_config(page_title="Saha Takip Sistemi v21", layout="wide")
conn = init_db()

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
    # --- SIDEBAR (SOL MENÜ) ---
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
        st.session_state['logged_in'] = False
        st.rerun()

    # --- SAYFA İÇERİKLERİ ---
    current_page = st.session_state.page

    if current_page == "🏠 Ana Sayfa":
        st.info(get_welcome_message(st.session_state['user_name']))
        query = "SELECT status FROM tasks" if st.session_state['role'] == 'admin' else f"SELECT status FROM tasks WHERE assigned_to='{st.session_state['user_email']}'"
        df_tasks = pd.read_sql(query, conn)
        c1, c2 = st.columns(2)
        c1.metric("📌 Bekleyen İşler", len(df_tasks[df_tasks['status']=='Bekliyor']) if not df_tasks.empty else 0)
        c2.metric("✅ Tamamlanan İşler", len(df_tasks[df_tasks['status']=='Tamamlandı']) if not df_tasks.empty else 0)

    elif current_page == "➕ İş Atama & Takip":
        st.header("➕ Yeni İş Atama")
        workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)
        if workers.empty:
            st.warning("Henüz sisteme kayıtlı personel (worker) yok. Kullanıcı Yönetimi'nden ekleyin.")
        else:
            with st.form("ata_form"):
                t = st.text_input("İş Başlığı")
                w = st.selectbox("Personel Seçin", workers['email'])
                d = st.text_area("İş Detayı / Açıklama")
                if st.form_submit_button("Görevi Ata"):
                    conn.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)", (w, t, d, 'Bekliyor'))
                    conn.commit()
                    st.success(f"İş {w} kullanıcısına atandı!")

    elif current_page == "✅ Tamamlanan İşler":
        st.header("📑 Tamamlanan İş Arşivi")
        df_done = pd.read_sql("SELECT * FROM tasks WHERE status='Tamamlandı' ORDER BY id DESC", conn)
        if df_done.empty:
            st.info("Henüz tamamlanan bir iş yok.")
        else:
            for _, row in df_done.iterrows():
                with st.expander(f"📍 {row['title']} - {row['assigned_to']}"):
                    st.write(f"**Rapor:** {row['report']}")
                    st.write(f"**Tarih:** {row['updated_at']}")
                    st.download_button("📄 Word Raporu İndir", data=create_word(row.to_dict()), file_name=f"Rapor_{row['id']}.docx", key=f"dl_{row['id']}")

    elif current_page == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı Kaydı"):
            with st.form("k_ekle"):
                ne, nn, nt = st.text_input("E-posta"), st.text_input("Ad Soyad"), st.text_input("Unvan")
                np = st.text_input("Şifre", type='password')
                nr = st.selectbox("Yetki", ["worker", "admin"])
                if st.form_submit_button("Kaydı Tamamla"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ne, make_hash(np), nr, nn, nt))
                    conn.commit()
                    st.success("Kullanıcı başarıyla eklendi!")
                    st.rerun()
        st.subheader("Mevcut Kullanıcılar")
        st.table(pd.read_sql("SELECT name as 'Ad Soyad', email, role as 'Yetki', title as 'Unvan' FROM users", conn))

    elif current_page == "⏳ Üstüme Atanan İşler":
        st.header("⏳ Bekleyen Görevlerim")
        my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        if my_tasks.empty:
            st.info("Harika! Üzerinizde bekleyen iş yok.")
        else:
            for _, r in my_tasks.iterrows():
                with st.expander(f"📋 {r['title']}"):
                    st.write(f"**Görev Detayı:** {r['description']}")
                    rep = st.text_area("İş Sonu Notu", key=f"r_{r['id']}")
                    fots = st.file_uploader("Fotoğrafları Yükle", accept_multiple_files=True, key=f"f_{r['id']}")
                    if st.button("İşi Bitir ve Gönder", key=f"b_{r['id']}"):
                        if fots:
                            p_json = json.dumps([f.read().hex() for f in fots])
                            conn.execute("UPDATE tasks SET status='Tamamlandı', report=?, photos_json=?, updated_at=? WHERE id=?", 
                                         (rep, p_json, datetime.now().strftime("%d/%m %H:%M"), r['id']))
                            conn.commit()
                            st.success("İş başarıyla tamamlandı!")
                            st.rerun()
                        else: st.error("Fotoğraf yüklemeden işi kapatamazsınız.")

    elif current_page == "📦 Zimmet/Envanter" or current_page == "🎒 Zimmetim":
        st.header("📦 Envanter ve Zimmet")
        if st.session_state['role'] == 'admin':
            st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)
            with st.form("zimmet_ekle"):
                i, a, q = st.text_input("Malzeme Adı"), st.text_input("Personel E-posta"), st.number_input("Adet", 1)
                if st.form_submit_button("Zimmetle"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (i, a, q, st.session_state['user_name']))
                    conn.commit(); st.rerun()
        else:
            st.table(pd.read_sql(f"SELECT item_name, quantity FROM inventory WHERE assigned_to='{st.session_state['user_email']}'", conn))

    elif current_page == "📜 Tamamlanan İşlerim":
        st.header("📜 Bitirdiğim İşler")
        my_done = pd.read_sql(f"SELECT title, report, updated_at FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Tamamlandı'", conn)
        st.table(my_done)
