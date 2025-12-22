import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import hashlib
import io

# --- 1. KONFİGÜRASYON VE VERİTABANI ---
st.set_page_config(page_title="Anatolia Bilişim | Operasyon Merkezi", layout="wide")

def init_db():
    conn = sqlite3.connect('anatolia_v75.db')
    c = conn.cursor()
    # Kullanıcılar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, password TEXT, role TEXT)''')
    # İşler/Görevler Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY, title TEXT, assigned_to TEXT, city TEXT, status TEXT, 
                  note TEXT, report_note TEXT, file_count INTEGER, created_at TEXT, updated_at TEXT)''')
    # Envanter Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY, item_name TEXT, serial_no TEXT, owner_email TEXT, date TEXT)''')
    
    # Demo Kullanıcılar (Şifre: 1234)
    pw = hashlib.sha256("1234".encode()).hexdigest()
    demo_users = [
        (1, 'Doğukan Gürol', 'admin@anatolia.com', '05001112233', pw, 'Admin'),
        (2, 'Yönetici Panel', 'yonetici@anatolia.com', '05001112234', pw, 'Yönetici'),
        (3, 'Müdür Panel', 'mudur@anatolia.com', '05001112235', pw, 'Müdür'),
        (4, 'Saha Ekibi', 'saha@anatolia.com', '05001112236', pw, 'Saha Personeli')
    ]
    c.executemany('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)', demo_users)
    conn.commit()
    conn.close()

if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state['db_initialized'] = True

# --- 2. YARDIMCI ARAÇLAR ---
def get_greeting():
    hr = datetime.now().hour
    if hr < 12: return "Günaydın"
    elif hr < 18: return "İyi Günler"
    else: return "İyi Akşamlar"

def check_auth(email, password):
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect('anatolia_v75.db')
    df = pd.read_sql_query("SELECT * FROM users WHERE email=? AND password=?", conn, params=(email, pw_hash))
    conn.close()
    return df.to_dict('records')[0] if not df.empty else None

# --- 3. OTURUM YÖNETİMİ ---
if 'user' not in st.session_state:
    st.title("Anatolia Bilişim - Giriş")
    with st.form("login_form"):
        email = st.text_input("E-Posta")
        password = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            user = check_auth(email, password)
            if user:
                st.session_state['user'] = user
                st.rerun()
            else: st.error("Hatalı e-posta veya şifre.")
    st.stop()

user = st.session_state['user']
role = user['role']

# --- 4. NAVİGASYON (Sidebar) ---
st.sidebar.title(f"👤 {user['name']}")
st.sidebar.info(f"Yetki: {role}")

menu_options = ["Ana Sayfa"]
if role in ['Admin', 'Yönetici', 'Müdür']:
    menu_options += ["İş Atama", "Atanan İşler", "TT Onay Bekleyenler"]
if role in ['Admin', 'Yönetici']:
    menu_options += ["Hak Ediş", "Giriş Onayları", "Kullanıcı Yönetimi"]
if role == 'Saha Personeli':
    menu_options += ["Üzerime Atanan İşler", "Tamamladığım İşler"]
menu_options += ["Zimmet & Envanter", "Profilim"]

choice = st.sidebar.selectbox("Menü", menu_options)

if st.sidebar.button("Çıkış Yap"):
    del st.session_state['user']
    st.rerun()

# --- 5. MODÜLLER ---

# ANA SAYFA
if choice == "Ana Sayfa":
    st.title(f"{get_greeting()}, {user['name']} 👋")
    conn = sqlite3.connect('anatolia_v75.db')
    tasks_df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam İş", len(tasks_df))
    col2.metric("Onay Bekleyen", len(tasks_df[tasks_df['status'] == 'TT_Onayi_Bekliyor']))
    col3.metric("Tamamlanan", len(tasks_df[tasks_df['status'] == 'Hakedis_Alindi']))

# İŞ ATAMA
elif choice == "İş Atama":
    st.subheader("Yeni İş Atama")
    conn = sqlite3.connect('anatolia_v75.db')
    saha_users = pd.read_sql_query("SELECT name FROM users WHERE role='Saha Personeli'", conn)
    conn.close()

    if saha_users.empty:
        st.warning("⚠️ Önce kullanıcı yönetimi ekranından saha personeli eklemelisiniz.")
    else:
        with st.form("job_form"):
            t_title = st.text_input("İş Başlığı")
            t_assigned = st.selectbox("Personel Seçin", saha_users['name'].tolist())
            t_city = st.selectbox("Şehir", ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"])
            t_note = st.text_area("İş Notu")
            if st.form_submit_button("İşi Ata"):
                conn = sqlite3.connect('anatolia_v75.db')
                conn.execute("INSERT INTO tasks (title, assigned_to, city, status, note, created_at) VALUES (?,?,?,?,?,?)",
                          (t_title, t_assigned, t_city, 'Atandı', t_note, datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit(); conn.close()
                st.success("İş başarıyla atandı.")
                st.rerun()

# SAHA PERSONELİ EKRANI
elif choice == "Üzerime Atanan İşler":
    st.subheader("Aktif Görevlerim")
    conn = sqlite3.connect('anatolia_v75.db')
    my_tasks = pd.read_sql_query("SELECT * FROM tasks WHERE assigned_to=? AND status IN ('Atandı', 'Taslak')", 
                                 conn, params=(user['name'],))
    conn.close()

    if my_tasks.empty: st.info("Şu an üzerinizde bekleyen iş yok.")
    for _, row in my_tasks.iterrows():
        with st.expander(f"📌 {row['title']} - {row['city']}"):
            r_note = st.text_area("Çalışma Notu", key=f"n_{row['id']}")
            files = st.file_uploader("Fotoğraflar", accept_multiple_files=True, key=f"f_{row['id']}")
            if st.button("İşi Onaya Gönder", key=f"b_{row['id']}"):
                if r_note:
                    conn = sqlite3.connect('anatolia_v75.db')
                    conn.execute("UPDATE tasks SET status='TT_Onayi_Bekliyor', report_note=?, file_count=? WHERE id=?", 
                              (r_note, len(files), row['id']))
                    conn.commit(); conn.close()
                    st.success("İş merkeze gönderildi."); st.rerun()
                else: st.error("Lütfen rapor notu yazın.")

# TT ONAY EKRANI
elif choice == "TT Onay Bekleyenler":
    st.subheader("Onay Bekleyen İşler")
    conn = sqlite3.connect('anatolia_v75.db')
    pending = pd.read_sql_query("SELECT * FROM tasks WHERE status='TT_Onayi_Bekliyor'", conn)
    conn.close()
    
    st.dataframe(pending[['id', 'title', 'assigned_to', 'report_note', 'file_count']], use_container_width=True)
    sel_id = st.number_input("İşlem Yapılacak İş ID", step=1)
    if st.button("✅ TT Onayı Ver"):
        conn = sqlite3.connect('anatolia_v75.db')
        conn.execute("UPDATE tasks SET status='Hakedis_Bekliyor' WHERE id=?", (sel_id,))
        conn.commit(); conn.close()
        st.rerun()

# ZİMMET & ENVANTER
elif choice == "Zimmet & Envanter":
    st.subheader("Envanter Takibi")
    conn = sqlite3.connect('anatolia_v75.db')
    if role == 'Saha Personeli':
        inv_df = pd.read_sql_query("SELECT * FROM inventory WHERE owner_email=?", conn, params=(user['email'],))
    else:
        inv_df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    st.dataframe(inv_df, use_container_width=True)

# PROFİLİM
elif choice == "Profilim":
    st.subheader("Hesap Bilgilerim")
    new_phone = st.text_input("Telefon Güncelle", value=user['phone'])
    if st.button("Kaydet"):
        conn = sqlite3.connect('anatolia_v75.db')
        conn.execute("UPDATE users SET phone=? WHERE id=?", (new_phone, user['id']))
        conn.commit(); conn.close()
        st.success("Bilgiler güncellendi. Yeni bilgiler bir sonraki girişte aktif olur.")
