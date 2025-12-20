import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

# --- 1. VERİTABANI VE YARDIMCI FONKSİYONLAR ---

def init_db():
    """Veritabanını ve tabloları oluşturur."""
    conn = sqlite3.connect('isletme_app.db')
    c = conn.cursor()
    
    # Kullanıcılar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT)''')
    
    # Görevler Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, 
                  description TEXT, status TEXT, report TEXT, created_at TEXT)''')
    
    # Envanter (Zimmet) Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER)''')
    
    # İlk Yöneticiyi Oluştur (Eğer yoksa)
    c.execute("SELECT * FROM users WHERE email = 'admin@sirket.com'")
    if not c.fetchone():
        # Şifreleme (Basit hash)
        password = hashlib.sha256("1234".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES ('admin@sirket.com', ?, 'admin', 'Genel Müdür')", (password,))
        
    conn.commit()
    conn.close()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_user(email, password):
    conn = sqlite3.connect('isletme_app.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email =? AND password =?", (email, make_hash(password)))
    data = c.fetchall()
    conn.close()
    return data

# --- 2. ARAYÜZ FONKSİYONLARI ---

def main():
    st.set_page_config(page_title="İşletme Takip Sistemi", layout="wide")
    init_db()

    # Oturum Yönetimi
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_screen()
    else:
        sidebar_menu()

def login_screen():
    st.title("🔐 Personel Giriş Ekranı")
    
    col1, col2 = st.columns([1,2])
    with col1:
        email = st.text_input("Şirket E-postası")
        password = st.text_input("Şifre", type='password')
        
        if st.button("Giriş Yap"):
            user = check_user(email, password)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user_email'] = user[0][0]
                st.session_state['role'] = user[0][2]
                st.session_state['user_name'] = user[0][3]
                st.success(f"Hoşgeldiniz {st.session_state['user_name']}")
                st.rerun()
            else:
                st.error("Hatalı E-posta veya Şifre")
    with col2:
        st.info("İlk giriş için: admin@sirket.com / 1234")

def sidebar_menu():
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.text(f"Yetki: {st.session_state['role']}")
    
    menu_options = ["Ana Sayfa", "Fiyat Hesaplayıcı"]
    
    if st.session_state['role'] == 'admin':
        menu_options += ["Görev Atama & Takip", "Kullanıcı Yönetimi", "Tüm Envanter"]
    else:
        menu_options += ["Görevlerim", "Zimmetim"]
        
    choice = st.sidebar.radio("Menü", menu_options)
    
    if st.sidebar.button("Çıkış Yap"):
        st.session_state['logged_in'] = False
        st.rerun()
        
    # Sayfa Yönlendirmeleri
    if choice == "Ana Sayfa":
        st.header("🏢 İşletme Yönetim Paneli")
        st.write("Sol taraftaki menüden işlem seçebilirsiniz.")
        
    elif choice == "Kullanıcı Yönetimi":
        admin_user_management()
        
    elif choice == "Görev Atama & Takip":
        admin_task_management()
        
    elif choice == "Görevlerim":
        worker_task_view()
        
    elif choice == "Fiyat Hesaplayıcı":
        price_calculator()
        
    elif choice == "Tüm Envanter":
        admin_inventory_view()
        
    elif choice == "Zimmetim":
        worker_inventory_view()

# --- 3. MODÜLLER ---

def admin_user_management():
    st.subheader("👥 Kullanıcı Yönetimi")
    
    # Yeni Kullanıcı Ekleme
    with st.expander("Yeni Kullanıcı Ekle"):
        new_name = st.text_input("Ad Soyad")
        new_email = st.text_input("E-posta (Kullanıcı Adı)")
        new_pass = st.text_input("Şifre", type='password')
        new_role = st.selectbox("Rol", ["worker", "admin"])
        
        if st.button("Kullanıcıyı Kaydet"):
            conn = sqlite3.connect('isletme_app.db')
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", 
                          (new_email, make_hash(new_pass), new_role, new_name))
                conn.commit()
                st.success("Kullanıcı başarıyla oluşturuldu!")
            except sqlite3.IntegrityError:
                st.error("Bu e-posta adresi zaten kayıtlı.")
            conn.close()
            
    # Kullanıcı Silme ve Listeleme
    st.markdown("---")
    conn = sqlite3.connect('isletme_app.db')
    users_df = pd.read_sql("SELECT name, email, role FROM users", conn)
    st.dataframe(users_df, use_container_width=True)
    
    delete_email = st.selectbox("Silinecek Kullanıcıyı Seç", users_df['email'])
    if st.button("Kullanıcıyı Sil"):
        if delete_email == 'admin@sirket.com':
            st.error("Ana yönetici silinemez!")
        else:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE email=?", (delete_email,))
            conn.commit()
            st.success(f"{delete_email} silindi.")
            st.rerun()
    conn.close()

def admin_task_management():
    st.subheader("📋 Görev Atama ve Raporlar")
    
    conn = sqlite3.connect('isletme_app.db')
    
    # Görev Atama
    workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Yeni Görev Ata**")
        assign_to = st.selectbox("Çalışan Seç", workers['email']) if not workers.empty else None
        task_desc = st.text_area("İş Tanımı / Adres / Detay")
        if st.button("Görevi Ata"):
            if assign_to:
                c = conn.cursor()
                c.execute("INSERT INTO tasks (assigned_to, description, status, created_at) VALUES (?, ?, ?, ?)",
                          (assign_to, task_desc, 'Bekliyor', str(datetime.now())[:19]))
                conn.commit()
                st.success("Görev atandı.")
            else:
                st.warning("Önce çalışan eklemelisiniz.")
                
    with col2:
        st.markdown("**Tamamlanan İş Raporları**")
        completed_tasks = pd.read_sql("SELECT * FROM tasks WHERE status='Tamamlandı'", conn)
        st.dataframe(completed_tasks[['assigned_to', 'description', 'report', 'created_at']], hide_index=True)

    st.markdown("---")
    st.markdown("**Aktif Görev Listesi (Tümü)**")
    all_tasks = pd.read_sql("SELECT * FROM tasks", conn)
    st.dataframe(all_tasks, use_container_width=True)
    conn.close()

def worker_task_view():
    st.subheader("🛠️ Görevlerim")
    user = st.session_state['user_email']
    
    conn = sqlite3.connect('isletme_app.db')
    my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{user}' AND status!='Tamamlandı'", conn)
    
    if my_tasks.empty:
        st.info("Aktif bir göreviniz bulunmuyor.")
    else:
        for index, row in my_tasks.iterrows():
            with st.container(border=True):
                st.write(f"**İş:** {row['description']}")
                st.caption(f"Tarih: {row['created_at']}")
                
                report_text = st.text_area("Rapor / Notlar", key=f"rep_{row['id']}")
                if st.button("İşi Tamamla ve Raporla", key=f"btn_{row['id']}"):
                    c = conn.cursor()
                    c.execute("UPDATE tasks SET status=?, report=? WHERE id=?", 
                              ('Tamamlandı', report_text, row['id']))
                    conn.commit()
                    st.success("Rapor iletildi.")
                    st.rerun()
    conn.close()

def price_calculator():
    st.subheader("💰 Ürün Fiyat Hesaplayıcı")
    
    col1, col2 = st.columns(2)
    with col1:
        maliyet = st.number_input("Ürün Maliyeti (TL)", min_value=0.0, format="%.2f")
        kar_orani = st.number_input("İstenen Kâr Oranı (%)", min_value=0.0, value=20.0)
        vergi_orani = st.number_input("KDV Oranı (%)", value=20.0)
        
    with col2:
        st.markdown("### Sonuçlar")
        satis_fiyati = maliyet * (1 + kar_orani/100) * (1 + vergi_orani/100)
        st.metric(label="Satış Fiyatı (KDV Dahil)", value=f"{satis_fiyati:.2f} TL")
        
        net_kar = (maliyet * (kar_orani/100))
        st.write(f"**Ürün Başı Net Kâr:** {net_kar:.2f} TL")

def admin_inventory_view():
    st.subheader("📦 Zimmet / Envanter Yönetimi")
    
    conn = sqlite3.connect('isletme_app.db')
    
    with st.expander("Envantere Eşya Ekle / Zimmetle"):
        users = pd.read_sql("SELECT email FROM users", conn)
        
        item_name = st.text_input("Eşya Adı (Örn: Laptop Dell)")
        assigned_user = st.selectbox("Kime Zimmetlenecek?", users['email'])
        qty = st.number_input("Adet", min_value=1, value=1)
        
        if st.button("Envantere Kaydet"):
            c = conn.cursor()
            c.execute("INSERT INTO inventory (item_name, assigned_to, quantity) VALUES (?, ?, ?)",
                      (item_name, assigned_user, qty))
            conn.commit()
            st.success("Zimmetlendi.")
            st.rerun()
            
    st.markdown("### Tüm Zimmet Listesi")
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    st.dataframe(inv_df, use_container_width=True)
    conn.close()

def worker_inventory_view():
    st.subheader("🎒 Zimmetimdeki Eşyalar")
    user = st.session_state['user_email']
    conn = sqlite3.connect('isletme_app.db')
    my_inv = pd.read_sql(f"SELECT item_name, quantity FROM inventory WHERE assigned_to='{user}'", conn)
    
    if my_inv.empty:
        st.info("Üzerinize zimmetli eşya görünmüyor.")
    else:
        st.table(my_inv)
    conn.close()

if __name__ == '__main__':
    main()
