import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- SABİT DEĞİŞKENLER ---
ROLES = ["Admin", "Yönetici", "Müdür", "Saha Personeli"]
DB_NAME = "app.db"

# --- VERİTABANI YARDIMCI FONKSİYONLARI ---
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE,
                        password TEXT,
                        user_name TEXT,
                        user_role TEXT,
                        phone TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
                        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        assigned_to INTEGER,
                        city TEXT,
                        status TEXT,
                        hakedis_status TEXT,
                        created_at TIMESTAMP,
                        FOREIGN KEY(assigned_to) REFERENCES users(user_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS job_files (
                        file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id INTEGER,
                        file_path TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
                        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_name TEXT,
                        assigned_user_id INTEGER,
                        FOREIGN KEY(assigned_user_id) REFERENCES users(user_id))''')
    
    # Varsayılan Admin Kullanıcısı
    cursor.execute("SELECT * FROM users WHERE email='admin1@sirket.com'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (email, password, user_name, user_role) VALUES (?,?,?,?)",
                       ("admin1@sirket.com", "admin123", "Sistem Admin", "Admin"))
        cursor.execute("INSERT INTO users (email, password, user_name, user_role) VALUES (?,?,?,?)",
                       ("yonetici1@sirket.com", "yonetici123", "Proje Yöneticisi", "Yönetici"))
        cursor.execute("INSERT INTO users (email, password, user_name, user_role) VALUES (?,?,?,?)",
                       ("saha1@sirket.com", "saha123", "Saha Personeli 1", "Saha Personeli"))
    conn.commit()
    conn.close()

def db_execute(query, params=(), fetch=False):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return result

# --- YETKİ KONTROLLERİ ---
def is_admin(): return st.session_state.get("user_role") == "Admin"
def is_manager(): return st.session_state.get("user_role") in ["Admin", "Yönetici", "Müdür"]
def is_field_staff(): return st.session_state.get("user_role") == "Saha Personeli"

# --- YARDIMCI FONKSİYONLAR ---
def get_greeting():
    hour = datetime.now().hour
    if hour < 12: return "Günaydın"
    elif hour < 18: return "Tünaydın"
    else: return "İyi Akşamlar"

def export_to_excel(table_name):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# --- SAYFA FONKSİYONLARI ---
def login_screen():
    st.title("İş Takip Sistemi Giriş")
    email = st.text_input("Email")
    password = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        user = db_execute("SELECT user_id, user_name, user_role FROM users WHERE email=? AND password=?", (email, password), True)
        if user:
            st.session_state.logged_in = True
            st.session_state.user_id = user[0][0]
            st.session_state.user_name = user[0][1]
            st.session_state.user_role = user[0][2]
            st.rerun()
        else:
            st.error("Hatalı email veya şifre")

def dashboard():
    st.subheader(f"{get_greeting()}, {st.session_state.user_name}")
    if is_manager():
        col1, col2, col3 = st.columns(3)
        total_jobs = len(db_execute("SELECT job_id FROM jobs", fetch=True))
        pending_jobs = len(db_execute("SELECT job_id FROM jobs WHERE status='Beklemede'", fetch=True))
        completed_jobs = len(db_execute("SELECT job_id FROM jobs WHERE status='Tamamlandı'", fetch=True))
        col1.metric("Toplam İş", total_jobs)
        col2.metric("Bekleyen İş", pending_jobs)
        col3.metric("Tamamlanan İş", completed_jobs)

def job_assignment():
    if not is_manager(): return st.warning("Yetkiniz yok.")
    st.subheader("Yeni İş Ata")
    users = db_execute("SELECT user_id, user_name FROM users", fetch=True)
    user_dict = {u[1]: u[0] for u in users}
    
    title = st.text_input("İş Başlığı")
    selected_user = st.selectbox("Personel", list(user_dict.keys()))
    city = st.selectbox("Şehir", ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana", "Konya", "Diğer..."])
    
    if st.button("Ata"):
        db_execute("INSERT INTO jobs (title, assigned_to, city, status, hakedis_status, created_at) VALUES (?,?,?,?,?,?)",
                   (title, user_dict[selected_user], city, "Beklemede", "Beklemede", datetime.now()))
        st.success("İş başarıyla atandı.")

def job_list():
    st.subheader("İş Listesi")
    query = "SELECT * FROM jobs"
    if is_field_staff():
        query += f" WHERE assigned_to = {st.session_state.user_id}"
    
    df = pd.read_sql(query, get_connection())
    st.dataframe(df)
    
    if not df.empty:
        job_to_update = st.selectbox("Güncellenecek İş ID", df['job_id'])
        new_status = st.selectbox("Yeni Durum", ["Beklemede", "Devam Ediyor", "Tamamlandı"])
        if st.button("Durum Güncelle"):
            db_execute("UPDATE jobs SET status=? WHERE job_id=?", (new_status, job_to_update))
            st.rerun()
        
        st.download_button("Excel Olarak İndir", export_to_excel("jobs"), "is_listesi.xlsx")

def hakedis_management():
    st.subheader("Hak Ediş Yönetimi")
    df = pd.read_sql("SELECT job_id, title, hakedis_status FROM jobs", get_connection())
    st.dataframe(df)
    
    if is_manager():
        job_id = st.number_input("İş ID", step=1)
        status = st.selectbox("Hak Ediş Durumu", ["Beklemede", "Alındı"])
        if st.button("Güncelle"):
            db_execute("UPDATE jobs SET hakedis_status=? WHERE job_id=?", (status, job_id))
            st.rerun()

def user_management():
    if not is_admin(): return st.warning("Bu sayfa sadece Admin erişimine açıktır.")
    st.subheader("Kullanıcı Yönetimi")
    
    with st.expander("Yeni Kullanıcı Ekle"):
        new_email = st.text_input("Email")
        new_pass = st.text_input("Şifre", type="password")
        new_name = st.text_input("Ad Soyad")
        new_role = st.selectbox("Rol", ROLES)
        if st.button("Ekle"):
            db_execute("INSERT INTO users (email, password, user_name, user_role) VALUES (?,?,?,?)",
                       (new_email, new_pass, new_name, new_role))
            st.success("Kullanıcı eklendi.")
    
    users_df = pd.read_sql("SELECT user_id, email, user_name, user_role FROM users", get_connection())
    st.dataframe(users_df)
    
    del_id = st.number_input("Silinecek Kullanıcı ID", step=1)
    if st.button("Kullanıcıyı Sil"):
        db_execute("DELETE FROM users WHERE user_id=?", (del_id,))
        st.rerun()

# --- ANA UYGULAMA DÖNGÜSÜ ---
def main():
    init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_screen()
    else:
        st.sidebar.title("Anatoli Bilişim")
        st.sidebar.write(f"**Kullanıcı:** {st.session_state.user_name}")
        st.sidebar.write(f"**Rol:** {st.session_state.user_role}")
        
        menu = ["Dashboard", "İş Atama", "İş Listesi", "Hak Ediş", "Envanter", "Kullanıcı Yönetimi", "Profil"]
        choice = st.sidebar.radio("Menü", menu)
        
        if st.sidebar.button("Çıkış Yap"):
            st.session_state.logged_in = False
            st.rerun()

        if choice == "Dashboard": dashboard()
        elif choice == "İş Atama": job_assignment()
        elif choice == "İş Listesi": job_list()
        elif choice == "Hak Ediş": hakedis_management()
        elif choice == "Kullanıcı Yönetimi": user_management()
        elif choice == "Profil":
            st.subheader("Profil Güncelleme")
            new_phone = st.text_input("Telefon Numarası")
            if st.button("Güncelle"):
                db_execute("UPDATE users SET phone=? WHERE user_id=?", (new_phone, st.session_state.user_id))
                st.success("Profil güncellendi.")

if __name__ == "__main__":
    main()
