import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
from docx import Document
from docx.shared import Inches

# --- 1. VERİTABANI ---
def init_db():
    conn = sqlite3.connect('isletme_final_excel_v13.db', check_same_thread=False)
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

conn = init_db()
def make_hash(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. GELİŞMİŞ EXCEL OLUŞTURUCU (FOTOĞRAFLI) ---
def to_excel_with_images(df_tasks):
    output = io.BytesIO()
    # Excel yazarını başlat
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Fotoğrafları içermeyen ana tabloyu yaz (fotoğraflar manuel eklenecek)
    clean_df = df_tasks.drop('photos_json', axis=1)
    clean_df.to_excel(writer, index=False, sheet_name='Saha Raporu')
    
    workbook  = writer.book
    worksheet = writer.sheets['Saha Raporu']
    
    # Satır yüksekliğini fotoğraflara göre ayarla
    for i in range(1, len(df_tasks) + 1):
        worksheet.set_row(i, 100) # 100 birim yükseklik

    # Sütun başlığı ekle
    worksheet.write(0, len(clean_df.columns), "Saha Fotoğrafları")
    worksheet.set_column(len(clean_df.columns), len(clean_df.columns), 25) # Fotoğraf sütun genişliği

    # Veritabanındaki hex fotoğrafları Excel'e işle
    for row_num, photos_raw in enumerate(df_tasks['photos_json']):
        if photos_raw:
            photos = json.loads(photos_raw)
            if photos:
                # Sadece ilk fotoğrafı önizleme olarak Excel'e koyuyoruz (Hücreyi bozmaması için)
                img_data = io.BytesIO(bytes.fromhex(photos[0]))
                worksheet.insert_image(row_num + 1, len(clean_df.columns), "image.png", {
                    'image_data': img_data,
                    'x_scale': 0.15, # %15 boyutuna küçült
                    'y_scale': 0.15,
                    'x_offset': 5,
                    'y_offset': 5,
                    'positioning': 1 # Hücreyle birlikte hareket et
                })
    
    writer.close()
    return output.getvalue()

# --- 3. WORD RAPORU ---
def create_single_task_report(row):
    doc = Document()
    doc.add_heading('İŞ BİTİRME RAPORU', 0)
    doc.add_paragraph(f"İş: {row['title']}\nPersonel: {row['assigned_to']}\nTarih: {row['updated_at']}")
    doc.add_heading('Rapor Notu', level=2)
    doc.add_paragraph(str(row['report']))
    if row['photos_json']:
        photos = json.loads(row['photos_json'])
        for p_hex in photos:
            doc.add_picture(io.BytesIO(bytes.fromhex(p_hex)), width=Inches(4))
    bio = io.BytesIO(); doc.save(bio)
    return bio.getvalue()

# --- 4. ANA ARAYÜZ ---
st.set_page_config(page_title="Saha Rapor v13", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Giriş")
    e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
    if st.button("Giriş"):
        u = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (e, make_hash(p))).fetchone()
        if u:
            st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4]})
            st.rerun()
else:
    st.sidebar.title(f"👋 {st.session_state['user_name']}")
    menu = ["Ana Sayfa", "İş Atama & Takip", "Tamamlanan İşler", "Zimmet/Envanter", "Kullanıcı Yönetimi"] if st.session_state['role'] == 'admin' else ["Üstüme Atanan İşler", "Tamamlanan İşlerim", "Zimmetim"]
    choice = st.sidebar.radio("Menü", menu)

    if choice == "Ana Sayfa":
        tasks = pd.read_sql("SELECT status FROM tasks", conn)
        st.metric("📌 Bekleyen", len(tasks[tasks['status']=='Bekliyor']))
        st.metric("✅ Tamamlanan", len(tasks[tasks['status']=='Tamamlandı']))

    elif choice == "İş Atama & Takip":
        workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)
        with st.form("ata"):
            t, w, d = st.text_input("Başlık"), st.selectbox("Personel", workers['email']), st.text_area("Detay")
            if st.form_submit_button("Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)", (w, t, d, 'Bekliyor'))
                conn.commit(); st.success("Atandı!")

    elif choice == "Tamamlanan İşler":
        st.header("📑 Saha Raporları")
        df_d = pd.read_sql("SELECT * FROM tasks WHERE status='Tamamlandı'", conn)
        if not df_d.empty:
            # FOTOĞRAFLI EXCEL BUTONU
            st.download_button("📊 Fotoğraflı Excel Raporu İndir", 
                             data=to_excel_with_images(df_d), 
                             file_name="saha_ozet_raporu.xlsx")
            
            for _, row in df_d.iterrows():
                with st.expander(f"📍 {row['title']}"):
                    st.download_button("📄 Özel Word İndir", data=create_single_task_report(row), file_name=f"{row['title']}.docx", key=row['id'])
                    if row['photos_json']:
                        for p in json.loads(row['photos_json']): st.image(bytes.fromhex(p), width=200)

    elif choice == "Kullanıcı Yönetimi":
        with st.expander("Yeni Ekle"):
            with st.form("u"):
                e, n, t, p, r = st.text_input("E-posta"), st.text_input("Ad"), st.selectbox("Unvan", ["Müdür", "Tekniker"]), st.text_input("Şifre"), st.selectbox("Rol", ["worker", "admin"])
                if st.form_submit_button("Ekle"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (e, make_hash(p), r, n, t))
                    conn.commit(); st.rerun()
        st.table(pd.read_sql("SELECT name, email, title FROM users", conn))

    elif choice == "Üstüme Atanan İşler":
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        for _, r in tasks.iterrows():
            with st.expander(r['title']):
                notu = st.text_area("Rapor", key=f"n_{r['id']}")
                fots = st.file_uploader("Fotoğraflar", accept_multiple_files=True, key=f"f_{r['id']}")
                if st.button("Bitir", key=f"b_{r['id']}"):
                    if fots:
                        p_list = json.dumps([f.read().hex() for f in fots])
                        conn.execute("UPDATE tasks SET status='Tamamlandı', report=?, photos_json=?, updated_at=? WHERE id=?", (notu, p_list, datetime.now().strftime("%d/%m %H:%M"), r['id']))
                        conn.commit(); st.rerun()

    elif choice == "Tamamlanan İşlerim":
        st.dataframe(pd.read_sql(f"SELECT title, report, updated_at FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Tamamlandı'", conn))

    elif choice == "Zimmetim" or choice == "Zimmet/Envanter":
        if st.session_state['role'] == 'admin':
            st.dataframe(pd.read_sql("SELECT * FROM inventory", conn))
        else:
            st.table(pd.read_sql(f"SELECT * FROM inventory WHERE assigned_to='{st.session_state['user_email']}'", conn))
        with st.form("inv"):
            n, q = st.text_input("Eşya"), st.number_input("Adet", 1)
            target = st.session_state['user_email'] if st.session_state['role'] == 'worker' else st.text_input("Personel E-posta")
            if st.form_submit_button("Kaydet"):
                conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (n, target, q, st.session_state['user_name']))
                conn.commit(); st.rerun()
