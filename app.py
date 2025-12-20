import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

# --- 1. VERİTABANI SİSTEMİ (KENDİ KENDİNİ DÜZELTEN VERSİYON) ---
def init_db():
    # Yeni bir dosya ismi kullanarak eski hatalı dosyadan kurtuluyoruz
    conn = sqlite3.connect('isletme_v4_final.db', check_same_thread=False)
    c = conn.cursor()
    
    # Kullanıcılar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT)''')
    
    # Görevler Tablosu (Tüm sütunlar dahil)
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  assigned_to TEXT, 
                  title TEXT, 
                  description TEXT, 
                  status TEXT, 
                  report TEXT, 
                  photo BLOB, 
                  updated_at TEXT)''')
    
    # Zimmet Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER)''')
    
    # Varsayılan Kullanıcıları Ekle
    admin_pw = hashlib.sha256("1234".encode()).hexdigest()
    worker_pw = hashlib.sha256("1234".encode()).hexdigest()
    
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Genel Müdür')", (admin_pw,))
    c.execute("INSERT OR IGNORE INTO users VALUES ('deneme123@dev.com', ?, 'worker', 'Deneme Çalışan')", (worker_pw,))
    
    conn.commit()
    return conn

conn = init_db()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- 2. ANA ARAYÜZ ---
def main():
    st.set_page_config(page_title="İş Takip Sistemi v4", layout="wide")
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_screen()
    else:
        sidebar_menu()

def login_screen():
    st.title("🚀 İşletme Operasyon Merkezi")
    col1, _ = st.columns([1, 2])
    with col1:
        email = st.text_input("Şirket E-postası")
        password = st.text_input("Şifre", type='password')
        if st.button("Giriş Yap"):
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
                st.error("E-posta veya şifre hatalı!")

def sidebar_menu():
    st.sidebar.title(f"👋 {st.session_state['user_name']}")
    
    if st.session_state['role'] == 'admin':
        menu = ["Ana Sayfa (Özet)", "Yeni İş Ata", "Tamamlanmış İşler", "Kullanıcı Yönetimi", "Zimmet/Envanter"]
    else:
        menu = ["Üstüme Atanan İşler", "Tamamlanan İşlerim", "Fiyat Hesaplayıcı", "Zimmetim"]
        
    choice = st.sidebar.radio("Menü Seçiniz", menu)
    
    if st.sidebar.button("Güvenli Çıkış"):
        st.session_state['logged_in'] = False
        st.rerun()

    # Sayfa Yönlendirmeleri
    if choice == "Ana Sayfa (Özet)": admin_dashboard()
    elif choice == "Yeni İş Ata": admin_assign_task()
    elif choice == "Tamamlanmış İşler": admin_completed_tasks()
    elif choice == "Kullanıcı Yönetimi": admin_users()
    elif choice == "Zimmet/Envanter": admin_inventory()
    elif choice == "Üstüme Atanan İşler": worker_active_tasks()
    elif choice == "Tamamlanan İşlerim": worker_done_tasks()
    elif choice == "Fiyat Hesaplayıcı": price_calc()
    elif choice == "Zimmetim": worker_inventory()

# --- 3. YÖNETİCİ (ADMIN) FONKSİYONLARI ---
def admin_dashboard():
    st.header("📊 Genel Durum Paneli")
    c = conn.cursor()
    col1, col2 = st.columns(2)
    
    c.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'")
    pending = c.fetchone()[0]
    col1.metric("Bekleyen İşler", pending)
    
    c.execute("SELECT COUNT(*) FROM tasks WHERE status='Tamamlandı'")
    done = c.fetchone()[0]
    col2.metric("Tamamlanan İşler", done)

def admin_assign_task():
    st.subheader("🎯 Yeni Görev Atama")
    workers = pd.read_sql("SELECT email, name FROM users WHERE role='worker'", conn)
    
    with st.form("yeni_is_formu"):
        title = st.text_input("İş Başlığı (Örn: IB1122 1800 MONTAJ)")
        target_worker = st.selectbox("Çalışan Seç", workers['email'])
        desc = st.text_area("İş Detayları ve Adres")
        if st.form_submit_button("Görevi Gönder"):
            c = conn.cursor()
            c.execute("INSERT INTO tasks (assigned_to, title, description, status) VALUES (?,?,?,?)",
                      (target_worker, title, desc, 'Bekliyor'))
            conn.commit()
            st.success(f"İş başarıyla {target_worker} kullanıcısına atandı.")

def admin_completed_tasks():
    st.subheader("✅ Tamamlanmış İş Raporları")
    df = pd.read_sql("SELECT assigned_to as 'Çalışan', title as 'Başlık', report as 'Rapor', updated_at as 'Tarih' FROM tasks WHERE status='Tamamlandı'", conn)
    if df.empty:
        st.info("Henüz tamamlanan bir iş yok.")
    else:
        for worker in df['Çalışan'].unique():
            with st.expander(f"👤 Personel: {worker}"):
                st.table(df[df['Çalışan'] == worker])

def admin_users():
    st.subheader("👥 Kullanıcı Yönetimi")
    with st.expander("Yeni Kullanıcı Ekle"):
        n_email = st.text_input("E-posta")
        n_name = st.text_input("İsim Soyisim")
        n_pass = st.text_input("Şifre (Geçici)", type='password')
        n_role = st.selectbox("Yetki", ["worker", "admin"])
        if st.button("Kaydet"):
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", (n_email, make_hash(n_pass), n_role, n_name))
            conn.commit()
            st.rerun()
    df = pd.read_sql("SELECT name, email, role FROM users", conn)
    st.dataframe(df, use_container_width=True)

def admin_inventory():
    st.subheader("📦 Zimmet Yönetimi")
    # Basit zimmetleme alanı
    with st.form("zimmet_form"):
        esya = st.text_input("Eşya Adı")
        kisi = st.text_input("E-posta")
        adet = st.number_input("Adet", min_value=1)
        if st.form_submit_button("Zimmetle"):
            c = conn.cursor()
            c.execute("INSERT INTO inventory (item_name, assigned_to, quantity) VALUES (?,?,?)", (esya, kisi, adet))
            conn.commit()
            st.success("Zimmet kaydedildi.")
    df = pd.read_sql("SELECT * FROM inventory", conn)
    st.table(df)

# --- 4. ÇALIŞAN (WORKER) FONKSİYONLARI ---
def worker_active_tasks():
    st.subheader("⏳ Üzerimdeki Aktif İşler")
    user = st.session_state['user_email']
    tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{user}' AND status='Bekliyor'", conn)
    
    if tasks.empty:
        st.success("Tebrikler! Bekleyen işiniz bulunmuyor.")
    
    for _, row in tasks.iterrows():
        with st.expander(f"📌 {row['title']}"):
            st.write(f"**Açıklama:** {row['description']}")
            report = st.text_area("Rapor Yazınız", key=f"r_{row['id']}")
            photo = st.file_uploader("İş Sonu Fotoğrafı (Opsiyonel)", type=['jpg','png','jpeg'], key=f"p_{row['id']}")
            
            if st.button("İşi Tamamla", key=f"b_{row['id']}"):
                img_data = photo.read() if photo else None
                c = conn.cursor()
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute("UPDATE tasks SET status='Tamamlandı', report=?, photo=?, updated_at=? WHERE id=?",
                          (report, img_data, now, row['id']))
                conn.commit()
                st.success("İş raporlandı!")
                st.rerun()

def worker_done_tasks():
    st.subheader("✔️ Tamamladığım İşler")
    user = st.session_state['user_email']
    df = pd.read_sql(f"SELECT title, report, updated_at FROM tasks WHERE assigned_to='{user}' AND status='Tamamlandı'", conn)
    st.dataframe(df, use_container_width=True)

def price_calc():
    st.subheader("💰 Fiyat Hesaplayıcı")
    maliyet = st.number_input("Ürün Maliyeti (TL)", min_value=0.0)
    st.write(f"**%20 Kârlı Satış:** {maliyet * 1.20:.2f} TL")
    st.write(f"**%40 Kârlı Satış:** {maliyet * 1.40:.2f} TL")

def worker_inventory():
    st.subheader("🎒 Üzerimdeki Zimmetli Eşyalar")
    user = st.session_state['user_email']
    df = pd.read_sql(f"SELECT item_name, quantity FROM inventory WHERE assigned_to='{user}'", conn)
    st.table(df)

if __name__ == '__main__':
    main()
