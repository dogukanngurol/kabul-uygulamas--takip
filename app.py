import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
from docx import Document # Word için

# --- 1. VERİTABANI VE AYARLAR ---
def init_db():
    conn = sqlite3.connect('isletme_v6_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photo BLOB, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    admin_pw = hashlib.sha256("1234".encode()).hexdigest()
    worker_pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Genel Müdür')", (admin_pw,))
    c.execute("INSERT OR IGNORE INTO users VALUES ('deneme123@dev.com', ?, 'worker', 'Deneme Çalışan')", (worker_pw,))
    conn.commit()
    return conn

conn = init_db()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- 2. YARDIMCI FONKSİYONLAR (İNDİRME) ---
def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Rapor')
    writer.close()
    return output.getvalue()

def to_word(df, title_text):
    doc = Document()
    doc.add_heading(title_text, 0)
    for i, row in df.iterrows():
        doc.add_heading(f"İş: {row['Başlık']}", level=1)
        doc.add_paragraph(f"Personel: {row['Çalışan']}")
        doc.add_paragraph(f"Rapor: {row['Rapor']}")
        doc.add_paragraph(f"Tarih: {row['Tarih']}")
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. ANA ARAYÜZ ---
st.set_page_config(page_title="Pro Takip Sistemi v6", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Giriş Paneli")
    email = st.text_input("E-posta")
    password = st.text_input("Şifre", type='password')
    if st.button("Giriş"):
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, make_hash(password)))
        user = c.fetchone()
        if user:
            st.session_state.update({'logged_in':True, 'user_email':user[0], 'role':user[2], 'user_name':user[3]})
            st.rerun()
        else: st.error("Hatalı giriş!")
else:
    st.sidebar.title(f"👋 {st.session_state['user_name']}")
    menu = ["Ana Sayfa", "İş Atama/Takip", "Zimmet & Envanter", "Kullanıcılar"] if st.session_state['role'] == 'admin' else ["İşlerim", "Zimmetim", "Hesap Makinesi"]
    choice = st.sidebar.radio("Menü", menu)
    if st.sidebar.button("Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- ADMIN EKRANLARI ---
    if choice == "Ana Sayfa":
        st.header("📊 Genel Özet")
        df_tasks = pd.read_sql("SELECT status FROM tasks", conn)
        col1, col2 = st.columns(2)
        col1.metric("Bekleyen İşler", len(df_tasks[df_tasks['status'] == 'Bekliyor']))
        col2.metric("Tamamlananlar", len(df_tasks[df_tasks['status'] == 'Tamamlandı']))

    elif choice == "İş Atama/Takip":
        tab1, tab2 = st.tabs(["➕ Yeni İş Ata", "📑 Tamamlananları İndir"])
        with tab1:
            workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)
            with st.form("is_ata"):
                t_title = st.text_input("İş Başlığı")
                t_worker = st.selectbox("Çalışan", workers['email'])
                t_desc = st.text_area("Açıklama")
                if st.form_submit_button("Ata"):
                    conn.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)", (t_worker, t_title, t_desc, 'Bekliyor'))
                    conn.commit()
                    st.success("İş atandı!")
        with tab2:
            df_done = pd.read_sql("SELECT assigned_to as 'Çalışan', title as 'Başlık', report as 'Rapor', updated_at as 'Tarih', photo FROM tasks WHERE status='Tamamlandı'", conn)
            if not df_done.empty:
                col_ex, col_wd = st.columns(2)
                col_ex.download_button("📥 Excel İndir", data=to_excel(df_done.drop('photo', axis=1)), file_name="is_raporu.xlsx")
                col_wd.download_button("📝 Word İndir", data=to_word(df_done.drop('photo', axis=1), "Tamamlanan İş Raporu"), file_name="is_raporu.docx")
                
                for idx, row in df_done.iterrows():
                    with st.expander(f"🖼️ {row['Başlık']} - {row['Çalışan']}"):
                        st.write(f"Rapor: {row['Rapor']}")
                        if row['photo']:
                            st.image(row['photo'], width=300)
                            st.download_button("🖼️ Fotoğrafı İndir", data=row['photo'], file_name=f"{row['Başlık']}.jpg", key=f"dl_{idx}")

    elif choice == "Zimmet & Envanter":
        st.header("📦 Genel Zimmet Listesi")
        df_inv = pd.read_sql("SELECT * FROM inventory", conn)
        st.download_button("📊 Tüm Envanteri Excel İndir", data=to_excel(df_inv), file_name="envanter.xlsx")
        
        with st.expander("➕ Yeni Zimmet Ekle / Düzenle"):
            with st.form("inv_admin"):
                i_name = st.text_input("Eşya/Araç Adı")
                i_to = st.text_input("Çalışan E-posta")
                i_qty = st.number_input("Adet", min_value=1)
                if st.form_submit_button("Kaydet"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (i_name, i_to, i_qty, 'Admin'))
                    conn.commit()
                    st.rerun()
        st.table(df_inv)

    # --- ÇALIŞAN EKRANLARI ---
    elif choice == "İşlerim":
        st.header("⏳ Bekleyen İşlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        for _, row in tasks.iterrows():
            with st.expander(f"📍 {row['title']}"):
                rep = st.text_area("İş Notu", key=f"r_{row['id']}")
                up_photo = st.file_uploader("Fotoğraf Yükle", type=['jpg','png','jpeg'], key=f"p_{row['id']}")
                if st.button("Bitir", key=f"b_{row['id']}"):
                    p_data = up_photo.read() if up_photo else None
                    conn.execute("UPDATE tasks SET status='Tamamlandı', report=?, photo=?, updated_at=? WHERE id=?", (rep, p_data, datetime.now().strftime("%d/%m/%Y %H:%M"), row['id']))
                    conn.commit()
                    st.rerun()

    elif choice == "Zimmetim":
        st.header("🎒 Üzerimdeki Eşyalar")
        df_my_inv = pd.read_sql(f"SELECT item_name as 'Eşya', quantity as 'Adet' FROM inventory WHERE assigned_to='{st.session_state['user_email']}'", conn)
        st.table(df_my_inv)
        with st.expander("➕ Yeni Eşya Bildir"):
            with st.form("inv_work"):
                new_i = st.text_input("Eşya Adı")
                new_q = st.number_input("Adet", min_value=1)
                if st.form_submit_button("Ekle"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (new_i, st.session_state['user_email'], new_q, 'Çalışan'))
                    conn.commit()
                    st.rerun()
