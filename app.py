import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
from PIL import Image
import io

# --- 1. VERİTABANI SİSTEMİ ---
def init_db():
    conn = sqlite3.connect('isletme_app.db', check_same_thread=False)
    c = conn.cursor()
    # Kullanıcılar
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT)''')
    # Görevler (Gelişmiş)
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, 
                  title TEXT, description TEXT, status TEXT, 
                  report TEXT, photo BLOB, updated_at TEXT)''')
    # Zimmet
    c.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER)''')
    
    # Varsayılan Admin ve İstediğin Deneme Kullanıcısı
    admin_pw = hashlib.sha256("1234".encode()).hexdigest()
    worker_pw = hashlib.sha256("1234".encode()).hexdigest()
    
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Genel Müdür')", (admin_pw,))
    c.execute("INSERT OR IGNORE INTO users VALUES ('deneme123@dev.com', ?, 'worker', 'Deneme Çalışan')", (worker_pw,))
    
    conn.commit()
    return conn

conn = init_db()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- 2. ARAYÜZ ---
def main():
    st.set_page_config(page_title="İş Takip Sistemi v2", layout="wide")
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_screen()
    else:
        sidebar_menu()

def login_screen():
    st.title("🚀 İşletme Operasyon Paneli")
    col1, _ = st.columns([1, 2])
    with col1:
        email = st.text_input("E-posta")
        password = st.text_input("Şifre", type='password')
        if st.button("Giriş"):
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, make_hash(password)))
            user = c.fetchone()
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user_email'] = user[0]
                st.session_state['role'] = user[2]
                st.session_state['user_name'] = user[3]
                st.rerun()
            else:
                st.error("Giriş başarısız.")

def sidebar_menu():
    st.sidebar.title(f"👋 {st.session_state['user_name']}")
    
    if st.session_state['role'] == 'admin':
        menu = ["Ana Sayfa (Özet)", "Yeni İş Ata", "Tamamlanmış İşler", "Kullanıcı Yönetimi", "Zimmet/Envanter"]
    else:
        menu = ["Üstüme Atanan İşler", "Tamamlanan İşlerim", "Fiyat Hesaplayıcı", "Zimmetim"]
        
    choice = st.sidebar.radio("Menü", menu)
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()

    if choice == "Ana Sayfa (Özet)": admin_dashboard()
    elif choice == "Yeni İş Ata": admin_assign_task()
    elif choice == "Tamamlanmış İşler": admin_completed_tasks()
    elif choice == "Kullanıcı Yönetimi": admin_users()
    elif choice == "Üstüme Atanan İşler": worker_active_tasks()
    elif choice == "Tamamlanan İşlerim": worker_done_tasks()
    elif choice == "Fiyat Hesaplayıcı": price_calc()

# --- 3. ADMIN EKRANLARI ---
def admin_dashboard():
    st.header("📊 Genel Durum Özeti")
    c = conn.cursor()
    
    col1, col2 = st.columns(2)
    with col1:
        c.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'")
        pending = c.fetchone()[0]
        st.metric("Tamamlanmayı Bekleyen İşler", pending)
        
    with col2:
        c.execute("SELECT COUNT(*) FROM tasks WHERE status='Tamamlandı'")
        done = c.fetchone()[0]
        st.metric("Tamamlanan Toplam İş", done)

def admin_assign_task():
    st.subheader("🎯 Yeni Görev Atama")
    workers = pd.read_sql("SELECT email, name FROM users WHERE role='worker'", conn)
    
    with st.form("task_form"):
        title = st.text_input("İş Başlığı (Örn: IB1122 1800 MONTAJ)")
        target_worker = st.selectbox("Çalışan Seç", workers['email'])
        desc = st.text_area("İş Detayları ve Adres")
        if st.form_submit_button("Görevi Gönder"):
            c = conn.cursor()
            c.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)",
                      (target_worker, title, desc, 'Bekliyor'))
            conn.commit()
            st.success("İş başarıyla atandı!")

def admin_completed_tasks():
    st.subheader("✅ Tamamlanmış İşler Raporu")
    df = pd.read_sql("SELECT assigned_to as 'Çalışan', title as 'İş Başlığı', report as 'Rapor', updated_at as 'Tarih' FROM tasks WHERE status='Tamamlandı' ORDER BY updated_at DESC", conn)
    
    for worker in df['Çalışan'].unique():
        with st.expander(f"👤 {worker} Tarafından Yapılan İşler"):
            st.table(df[df['Çalışan'] == worker])

# --- 4. ÇALIŞAN EKRANLARI ---
def worker_active_tasks():
    st.subheader("⏳ Üzerimdeki Aktif İşler")
    user = st.session_state['user_email']
    tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{user}' AND status='Bekliyor'", conn)
    
    if tasks.empty:
        st.info("Şu an bekleyen bir işiniz yok.")
    
    for _, row in tasks.iterrows():
        with st.expander(f"📍 {row['title']}"):
            st.write(f"**Detay:** {row['description']}")
            report = st.text_area("İş Raporu / Notlar", key=f"rep_{row['id']}")
            photo = st.file_uploader("İş Sonu Fotoğrafı Yükle", type=['jpg', 'png', 'jpeg'], key=f"img_{row['id']}")
            
            if st.button("İşi Bitir ve Gönder", key=f"btn_{row['id']}"):
                img_byte = None
                if photo:
                    img_byte = photo.read()
                
                c = conn.cursor()
                c.execute("UPDATE tasks SET status='Tamamlandı', report=?, photo=?, updated_at=? WHERE id=?",
                          ('Tamamlandı', report, img_byte, datetime.now().strftime("%Y-%m-%d %H:%M"), row['id']))
                conn.commit()
                st.success("İş başarıyla raporlandı!")
                st.rerun()

def worker_done_tasks():
    st.subheader("✔️ Tamamladığım İşler")
    user = st.session_state['user_email']
    df = pd.read_sql(f"SELECT title, report, updated_at FROM tasks WHERE assigned_to='{user}' AND status='Tamamlandı'", conn)
    st.dataframe(df, use_container_width=True)

# (Diğer fonksiyonlar: price_calc, admin_users vb. benzer şekilde devam eder...)
def price_calc():
    st.subheader("💰 Fiyat Hesaplayıcı")
    maliyet = st.number_input("Maliyet", min_value=0.0)
    st.write(f"Tahmini Satış: {maliyet * 1.4} TL (Örnek %40 kâr)")

def admin_users():
    st.subheader("👥 Kullanıcı Listesi")
    df = pd.read_sql("SELECT name, email, role FROM users", conn)
    st.table(df)

if __name__ == '__main__':
    main()
