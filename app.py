import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
from docx import Document
from docx.shared import Inches
from sqlalchemy import create_engine, text

# --- !!! ÖNEMLİ: BURAYA KENDİ URI ADRESİNİ YAPIŞTIR !!! ---
DB_URI = "= postgresql://postgres:db.Knl2ipyNZhrU5NCC@db.ugpzfpxsiydcvfgibzlj.supabase.co:5432/postgres"

# --- 1. VERİTABANI BAĞLANTISI ---
engine = create_engine(DB_URI)

def init_db():
    with engine.connect() as conn:
        # Kullanıcılar Tablosu
        conn.execute(text('''CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)'''))
        
        # İşler Tablosu
        conn.execute(text('''CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY, assigned_to TEXT, title TEXT, 
            description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT)'''))
        
        # Zimmet Tablosu
        conn.execute(text('''CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY, item_name TEXT, 
            assigned_to TEXT, quantity INTEGER, updated_by TEXT)'''))
        
        # Varsayılan Admin Oluşturma
        pw = hashlib.sha256("1234".encode()).hexdigest()
        conn.execute(text("INSERT INTO users (email, password, role, name, title) VALUES (:e, :p, :r, :n, :t) ON CONFLICT (email) DO NOTHING"),
                     {"e": 'admin@sirket.com', "p": pw, "r": 'admin', "n": 'Ahmet Salça', "t": 'Genel Müdür'})
        conn.commit()

def get_welcome_message(full_name):
    hour = datetime.now().hour
    if 5 <= hour < 12: msg = "Günaydın"
    elif 12 <= hour < 18: msg = "İyi Günler"
    elif 18 <= hour < 24: msg = "İyi Akşamlar"
    else: msg = "İyi Geceler"
    return f"✨ {msg} **{full_name}**, İyi Çalışmalar!"

init_db()
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. RAPORLAMA FONKSİYONLARI ---
def create_word(row):
    doc = Document()
    doc.add_heading('SAHA İŞ RAPORU', 0)
    doc.add_paragraph(f"İş: {row['title']}\nSorumlu: {row['assigned_to']}\nTamamlanma: {row['updated_at']}")
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
    # Row verisini temizle (dict formatına çevirerek)
    data = {k: v for k, v in row.items() if k != 'photos_json'}
    df = pd.DataFrame([data])
    df.to_excel(writer, index=False, sheet_name='Rapor')
    if row['photos_json']:
        photos = json.loads(row['photos_json'])
        img_data = io.BytesIO(bytes.fromhex(photos[0]))
        writer.sheets['Rapor'].insert_image('G2', 'img.png', {'image_data': img_data, 'x_scale': 0.1, 'y_scale': 0.1})
    writer.close(); return output.getvalue()

# --- 3. ARAYÜZ ---
st.set_page_config(page_title="Saha Yönetim v17 (Cloud)", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Şirket Portalı")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş Yap"):
            with engine.connect() as conn:
                res = conn.execute(text("SELECT * FROM users WHERE email=:e AND password=:p"), {"e": e, "p": make_hash(p)}).fetchone()
                if res:
                    u = res._asdict() # PostgreSQL sonucunu sözlüğe çevir
                    st.session_state.update({'logged_in':True, 'user_email':u['email'], 'role':u['role'], 'user_full_name':u['name'], 'user_title':u['title']})
                    st.rerun()
                else: st.error("Hatalı giriş!")
else:
    # --- SIDEBAR ---
    st.sidebar.title(f"👤 {st.session_state['user_full_name']}")
    st.sidebar.caption(f"🏷️ {st.session_state['user_title']}")
    st.sidebar.markdown("---")
    
    if st.session_state['role'] == 'admin':
        if st.sidebar.button("🏠 Ana Sayfa", use_container_width=True): st.session_state.page = "Ana Sayfa"
        if st.sidebar.button("➕ İş Atama & Takip", use_container_width=True): st.session_state.page = "İş Atama & Takip"
        if st.sidebar.button("✅ Tamamlanan İşler", use_container_width=True): st.session_state.page = "Tamamlanan İşler"
        if st.sidebar.button("📦 Zimmet/Envanter", use_container_width=True): st.session_state.page = "Zimmet/Envanter"
        if st.sidebar.button("👥 Kullanıcı Yönetimi", use_container_width=True): st.session_state.page = "Kullanıcı Yönetimi"
    else:
        if st.sidebar.button("🏠 Ana Sayfa", use_container_width=True): st.session_state.page = "Ana Sayfa"
        if st.sidebar.button("⏳ Üstüme Atanan İşler", use_container_width=True): st.session_state.page = "Üstüme Atanan İşler"
        if st.sidebar.button("📜 Tamamlanan İşlerim", use_container_width=True): st.session_state.page = "Tamamlanan İşlerim"
        if st.sidebar.button("🎒 Zimmetim", use_container_width=True): st.session_state.page = "Zimmetim"

    st.sidebar.markdown("---")
    if st.sidebar.button("🔴 Güvenli Çıkış Yap", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

    if 'page' not in st.session_state: st.session_state.page = "Ana Sayfa"
    choice = st.session_state.page

    # --- EKRANLAR ---
    if choice == "Ana Sayfa":
        st.info(get_welcome_message(st.session_state['user_full_name']))
        query = "SELECT status FROM tasks" if st.session_state['role'] == 'admin' else f"SELECT status FROM tasks WHERE assigned_to='{st.session_state['user_email']}'"
        tasks_df = pd.read_sql(query, engine)
        c1, c2 = st.columns(2)
        wait_count = len(tasks_df[tasks_df['status']=='Bekliyor']) if not tasks_df.empty else 0
        done_count = len(tasks_df[tasks_df['status']=='Tamamlandı']) if not tasks_df.empty else 0
        c1.metric("📌 Bekleyen İşler", wait_count)
        c2.metric("✅ Tamamlanan İşler", done_count)

    elif choice == "Tamamlanan İşler":
        st.header("📑 Tamamlanan İş Raporları")
        df_d = pd.read_sql("SELECT * FROM tasks WHERE status='Tamamlandı' ORDER BY id DESC", engine)
        if df_d.empty: st.info("Henüz tamamlanan iş yok.")
        else:
            for _, row in df_d.iterrows():
                with st.expander(f"📍 {row['title']} ({row['assigned_to']})"):
                    st.write(f"**Tarih:** {row['updated_at']} | **Not:** {row['report']}")
                    c1, c2 = st.columns(2)
                    c1.download_button("📄 Word İndir", data=create_word(row.to_dict()), file_name=f"{row['title']}.docx", key=f"w_{row['id']}")
                    c2.download_button("📊 Excel İndir", data=create_excel(row.to_dict()), file_name=f"{row['title']}.xlsx", key=f"e_{row['id']}")

    elif choice == "İş Atama & Takip":
        workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", engine)
        with st.form("ata"):
            t, w, d = st.text_input("İş Başlığı"), st.selectbox("Personel", workers['email']), st.text_area("İş Detayı")
            if st.form_submit_button("Görevi Ata"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO tasks (assigned_to, title, description, status) VALUES (:w, :t, :d, :s)"),
                                 {"w": w, "t": t, "d": d, "s": 'Bekliyor'})
                    conn.commit(); st.success("İş Atandı!")

    elif choice == "Kullanıcı Yönetimi":
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("u"):
                ne, nn, nt, np, nr = st.text_input("E-posta"), st.text_input("Ad Soyad"), st.selectbox("Unvan", ["Müdür", "Saha", "Ofis"]), st.text_input("Şifre"), st.selectbox("Rol", ["worker", "admin"])
                if st.form_submit_button("Kaydet"):
                    with engine.connect() as conn:
                        conn.execute(text("INSERT INTO users VALUES (:e, :p, :r, :n, :t)"), {"e": ne, "p": make_hash(np), "r": nr, "n": nn, "t": nt})
                        conn.commit(); st.rerun()
        st.table(pd.read_sql("SELECT name, email, title FROM users", engine))

    elif choice == "Üstüme Atanan İşler":
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", engine)
        if tasks.empty: st.info("Şu an bekleyen bir göreviniz yok.")
        for _, r in tasks.iterrows():
            with st.expander(f"📌 {r['title']}"):
                st.write(r['description'])
                rep = st.text_area("Rapor", key=f"n_{r['id']}")
                fots = st.file_uploader("Fotoğraflar", accept_multiple_files=True, key=f"f_{r['id']}")
                if st.button("Bitir ve Gönder", key=f"b_{r['id']}"):
                    if fots:
                        p_list = json.dumps([f.read().hex() for f in fots])
                        with engine.connect() as conn:
                            conn.execute(text("UPDATE tasks SET status='Tamamlandı', report=:r, photos_json=:pj, updated_at=:u WHERE id=:id"),
                                         {"r": rep, "pj": p_list, "u": datetime.now().strftime("%d/%m %H:%M"), "id": r['id']})
                            conn.commit(); st.rerun()
                    else: st.error("Fotoğraf yüklemeden iş bitirilemez!")

    elif choice == "Tamamlanan İşlerim":
        st.dataframe(pd.read_sql(f"SELECT title, report, updated_at FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Tamamlandı'", engine))

    elif choice == "Zimmetim" or choice == "Zimmet/Envanter":
        if st.session_state['role'] == 'admin':
            st.dataframe(pd.read_sql("SELECT * FROM inventory", engine))
        else:
            st.table(pd.read_sql(f"SELECT item_name, quantity FROM inventory WHERE assigned_to='{st.session_state['user_email']}'", engine))
        with st.form("inv"):
            n, q = st.text_input("Eşya"), st.number_input("Adet", 1)
            target = st.session_state['user_email'] if st.session_state['role'] == 'worker' else st.text_input("Personel E-posta")
            if st.form_submit_button("Envantere Ekle"):
                with engine.connect() as conn:
                    conn.execute(text("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (:n, :a, :q, :u)"),
                                 {"n": n, "a": target, "q": q, "u": st.session_state['user_full_name']})
                    conn.commit(); st.rerun()
