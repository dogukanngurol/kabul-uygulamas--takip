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
    # İşler/Görevler Tablosu (Geliştirilmiş Şema)
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

init_db()

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
            else:
                st.error("Hatalı bilgiler.")
    st.stop()

user = st.session_state['user']
role = user['role']

# --- 4. NAVİGASYON (Sidebar) ---
st.sidebar.title(f"Merhaba, {user['name']}")
st.sidebar.info(f"Yetki: {role}")

menu_options = ["Ana Sayfa"]
if role in ['Admin', 'Yönetici', 'Müdür']:
    menu_options += ["İş Atama", "Atanan İşler", "Giriş Onayları", "TT Onay Bekleyenler"]
if role in ['Admin', 'Yönetici']:
    menu_options += ["Hak Ediş", "Kullanıcı Yönetimi"]
if role == 'Saha Personeli':
    menu_options += ["Üzerime Atanan İşler", "Tamamladığım İşler"]
menu_options += ["Zimmet & Envanter", "Profilim"]

choice = st.sidebar.selectbox("Menü", menu_options)

if st.sidebar.button("Çıkış Yap"):
    del st.session_state['user']
    st.rerun()

# --- 5. MODÜLLER ---

# A. ANA SAYFA & DASHBOARD
if choice == "Ana Sayfa":
    st.title(f"{get_greeting()}, {user['name']} 👋")
    conn = sqlite3.connect('anatolia_v75.db')
    tasks_df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam İş", len(tasks_df))
    col2.metric("Onay Bekleyen", len(tasks_df[tasks_df['status'] == 'TT_Onayi_Bekliyor']))
    col3.metric("Tamamlanan", len(tasks_df[tasks_df['status'] == 'Hakedis_Alindi']))

# B. İŞ ATAMA (Admin/Yön/Müdür)
elif choice == "İş Atama":
    st.subheader("Yeni İş Atama")
    conn = sqlite3.connect('anatolia_v75.db')
    saha_users = pd.read_sql_query("SELECT name FROM users WHERE role='Saha Personeli'", conn)
    conn.close()

    with st.form("job_form"):
        t_title = st.text_input("İş Başlığı")
        t_assigned = st.selectbox("Personel Seçin", saha_users['name'].tolist())
        t_city = st.selectbox("Şehir", ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"])
        t_note = st.text_area("İş Notu")
        if st.form_submit_button("İşi Ata"):
            conn = sqlite3.connect('anatolia_v75.db')
            c = conn.cursor()
            c.execute("INSERT INTO tasks (title, assigned_to, city, status, note, created_at) VALUES (?,?,?,?,?,?)",
                      (t_title, t_assigned, t_city, 'Atandı', t_note, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()
            st.success("İş başarıyla atandı.")

# C. SAHA PERSONELİ - ÜZERİME ATANAN İŞLER
elif choice == "Üzerime Atanan İşler":
    st.subheader("Aktif Görevlerim")
    conn = sqlite3.connect('anatolia_v75.db')
    my_tasks = pd.read_sql_query("SELECT * FROM tasks WHERE assigned_to=? AND status IN ('Atandı', 'Taslak')", 
                                 conn, params=(user['name'],))
    conn.close()

    for index, row in my_tasks.iterrows():
        with st.expander(f"📌 {row['title']} - {row['city']}"):
            st.write(f"**Not:** {row['note']}")
            r_note = st.text_area("Çalışma Notu (Zorunlu)", key=f"note_{row['id']}")
            files = st.file_uploader("Fotoğraflar (Max 65)", accept_multiple_files=True, key=f"file_{row['id']}")
            
            c1, c2 = st.columns(2)
            if c1.button("Taslak Kaydet", key=f"draft_{row['id']}"):
                # Taslak mantığı (Veritabanı update)
                st.info("Taslak kaydedildi.")
            if c2.button("İşi Gönder", key=f"send_{row['id']}"):
                if r_note:
                    conn = sqlite3.connect('anatolia_v75.db')
                    c = conn.cursor()
                    c.execute("UPDATE tasks SET status='TT_Onayi_Bekliyor', report_note=?, file_count=? WHERE id=?", 
                              (r_note, len(files), row['id']))
                    conn.commit()
                    conn.close()
                    st.success("İş onaya gönderildi.")
                    st.rerun()
                else: st.warning("Not girmelisiniz.")

# D. TT ONAY BEKLEYENLER (Admin/Müdür)
elif choice == "TT Onay Bekleyenler":
    st.subheader("Türk Telekom Onayı Bekleyen İşler")
    conn = sqlite3.connect('anatolia_v75.db')
    pending = pd.read_sql_query("SELECT * FROM tasks WHERE status='TT_Onayi_Bekliyor'", conn)
    conn.close()

    st.table(pending[['title', 'assigned_to', 'city', 'report_note', 'file_count']])
    
    selected_id = st.selectbox("İşlem Yapılacak İş ID", pending['id'].tolist() if not pending.empty else [None])
    if selected_id:
        c1, c2 = st.columns(2)
        if c1.button("✅ Onayla (Hak Edişe Gönder)"):
            conn = sqlite3.connect('anatolia_v75.db')
            conn.execute("UPDATE tasks SET status='Hakedis_Bekliyor' WHERE id=?", (selected_id,))
            conn.commit() ; conn.close()
            st.rerun()
        if c2.button("❌ Reddet"):
            conn = sqlite3.connect('anatolia_v75.db')
            conn.execute("UPDATE tasks SET status='Reddedildi' WHERE id=?", (selected_id,))
            conn.commit() ; conn.close()
            st.rerun()

# E. ZİMMET & ENVANTER (Tüm Kullanıcılar)
elif choice == "Zimmet & Envanter":
    st.subheader("📦 Envanter ve Zimmet Takibi")
    if role in ['Admin', 'Yönetici', 'Müdür']:
        with st.expander("➕ Yeni Zimmet Ekle"):
            i_name = st.text_input("Ekipman Adı")
            i_serial = st.text_input("Seri No")
            i_owner = st.text_input("Zimmetlenecek E-Posta")
            if st.button("Kaydet"):
                conn = sqlite3.connect('anatolia_v75.db')
                conn.execute("INSERT INTO inventory (item_name, serial_no, owner_email, date) VALUES (?,?,?,?)",
                             (i_name, i_serial, i_owner, datetime.now().strftime("%Y-%m-%d")))
                conn.commit() ; conn.close()
                st.success("Envanter eklendi.")

    conn = sqlite3.connect('anatolia_v75.db')
    if role == 'Saha Personeli':
        inv_df = pd.read_sql_query("SELECT * FROM inventory WHERE owner_email=?", conn, params=(user['email'],))
    else:
        inv_df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    st.dataframe(inv_df, use_container_width=True)

# F. PROFİLİM
elif choice == "Profilim":
    st.subheader("Profil Bilgileri")
    st.write(f"**İsim:** {user['name']}")
    st.write(f"**E-Posta:** {user['email']}")
    new_phone = st.text_input("Telefon Numarası Güncelle", value=user['phone'])
    if st.button("Güncelle"):
        conn = sqlite3.connect('anatolia_v75.db')
        conn.execute("UPDATE users SET phone=? WHERE id=?", (new_phone, user['id']))
        conn.commit() ; conn.close()
        st.success("Telefon güncellendi. Lütfen yeniden giriş yapın.")

# --- 6. EXCEL RAPORLAMA FONKSİYONU ---
if choice in ["Atanan İşler", "Tamamladığım İşler", "Hak Ediş"]:
    st.sidebar.markdown("---")
    if st.sidebar.button("📊 Excel Raporu Al"):
        # Excel oluşturma mantığı buraya entegre edilir
        st.sidebar.write("Rapor hazırlanıyor...")
