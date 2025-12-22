import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import hashlib
import io

# --- 1. SİSTEM AYARLARI VE VERİTABANI ---
st.set_page_config(page_title="Anatolia Bilişim | İş Takip", layout="wide")

def init_db():
    conn = sqlite3.connect('anatoli_demo.db')
    c = conn.cursor()
    # Tablo Tanımlamaları (Madde 1, 5, 10, 11)
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, assigned_to TEXT, city TEXT, status TEXT, note TEXT, created_at TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, owner_email TEXT)''')
    
    # Örnek Kullanıcılar (Madde 1)
    hashed_pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (id, name, email, phone, password, role) VALUES (1, 'Doğukan Gürol', 'admin@anatoli.com', '5550001122', ?, 'Admin')", (hashed_pw,))
    c.execute("INSERT OR IGNORE INTO users (id, name, email, phone, password, role) VALUES (2, 'Ahmet Saha', 'saha@anatoli.com', '5559998877', ?, 'Saha Personeli')", (hashed_pw,))
    conn.commit()
    conn.close()

init_db()

# --- 2. YARDIMCI FONKSİYONLAR ---
def get_greeting(): # Madde 3
    hr = datetime.now().hour
    if 8 <= hr < 12: return "Günaydın"
    elif 12 <= hr < 18: return "İyi Günler"
    elif 18 <= hr < 24: return "İyi Akşamlar"
    else: return "İyi Geceler"

def to_excel(df): # Madde 5, 6, 7, 8, 9, 10, 11
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

# --- 3. OTURUM YÖNETİMİ ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Anatolia Bilişim Sistem Girişi")
    with st.form("login_form"):
        email = st.text_input("📧 Şirket Maili")
        password = st.text_input("🔑 Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            hpw = hashlib.sha256(password.encode()).hexdigest()
            conn = sqlite3.connect('anatoli_demo.db')
            user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hpw)).fetchone()
            conn.close()
            if user:
                st.session_state.logged_in = True
                st.session_state.user = {"id": user[0], "name": user[1], "email": user[2], "phone": user[3], "role": user[5]}
                st.session_state.page = "🏠 Ana Sayfa"
                st.rerun()
            else:
                st.error("Hatalı mail veya şifre!")
else:
    # --- 4. SOL MENÜ (Madde 2) ---
    with st.sidebar:
        st.markdown(f"## 🏢 Anatolia Bilişim")
        st.write(f"👤 **{st.session_state.user['name']}**")
        st.caption(f"🛡️ {st.session_state.user['role']}")
        st.divider()
        
        # Rol Bazlı Menü Sekmeleri
        if st.session_state.user['role'] == "Saha Personeli":
            menu = ["🏠 Ana Sayfa", "⏳ Üzerime Atanan İşler", "📜 Tamamladığım İşler", "🎒 Zimmetim", "👤 Profilim", "🚪 Çıkış"]
        else:
            menu = ["🏠 Ana Sayfa", "➕ İş Ataması", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onayı Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi", "👤 Profilim", "🚪 Çıkış"]
        
        for item in menu:
            style = "primary" if st.session_state.page == item else "secondary"
            if st.sidebar.button(item, use_container_width=True, type=style):
                if item == "🚪 Çıkış":
                    st.session_state.logged_in = False
                    st.rerun()
                st.session_state.page = item
                st.rerun()

    # --- 5. SAYFA İÇERİKLERİ ---
    page = st.session_state.page
    conn = sqlite3.connect('anatoli_demo.db')

    if page == "🏠 Ana Sayfa": # Madde 3 & 14
        st.header(f"✨ {get_greeting()} {st.session_state.user['name']}, İyi Çalışmalar")
        
        if st.session_state.user['role'] != "Saha Personeli":
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("✅ Günlük Tamamlanan", "12")
            c2.metric("⏳ Bekleyen Atamalar", "5")
            c3.metric("📅 Haftalık Toplam", "48")
            c4.metric("📊 Aylık Toplam", "184")
        else:
            st.info("💡 Üzerinizdeki aktif işleri görmek için 'Üzerime Atanan İşler' sekmesine geçiniz.")

    elif page == "➕ İş Ataması": # Madde 4
        st.header("➕ Yeni İş Atama")
        personel_list = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)
        with st.form("task_form"):
            title = st.text_input("📌 İş Başlığı")
            pers = st.selectbox("👷 Personel Seçimi", personel_list['email'])
            city = st.selectbox("📍 Şehir Seçimi", ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"]) # 81 il simülasyonu
            if st.form_submit_button("🚀 İşi Ata"):
                conn.execute("INSERT INTO tasks (title, assigned_to, city, status, created_at) VALUES (?, ?, ?, 'Atandı', ?)", (title, pers, city, datetime.now().strftime("%d-%m-%Y")))
                conn.commit()
                st.success("İş başarıyla atandı!")

    elif page == "⏳ Üzerime Atanan İşler": # Madde 15
        st.header("⏳ Üzerime Atanan İşler")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.user['email']}' AND status='Atandı'", conn)
        if tasks.empty:
            st.warning("Atanan Bir Görev Bulunmamaktadır")
        else:
            for index, row in tasks.iterrows():
                with st.expander(f"📌 {row['title']} - {row['city']}"):
                    note = st.text_area("📝 İş Detayı (Zorunlu)", key=f"note_{row['id']}")
                    files = st.file_uploader("📸 Fotoğraflar (Maks 65)", accept_multiple_files=True, key=f"file_{row['id']}")
                    c1, c2, c3 = st.columns(3)
                    if c1.button("💾 Kaydet", key=f"save_{row['id']}"): st.toast("Taslak Kaydedildi")
                    if c2.button("📧 Giriş Maili Gerekli", key=f"mail_{row['id']}"):
                        conn.execute("UPDATE tasks SET status='Giriş Maili Bekler' WHERE id=?", (row['id'],))
                        conn.commit()
                        st.rerun()
                    if c3.button("🚀 İşi Gönder", type="primary", disabled=not note, key=f"send_{row['id']}"):
                        conn.execute("UPDATE tasks SET status='Kabul Alındı', note=? WHERE id=?", (note, row['id']))
                        conn.commit()
                        st.rerun()

    elif page == "📋 Atanan İşler": # Madde 5
        st.header("📋 Günlük Atanan İşler")
        df = pd.read_sql("SELECT * FROM tasks", conn)
        if df.empty: st.info("Atanan Bir Görev Bulunmamaktadır")
        else:
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Excel Olarak İndir", data=to_excel(df), file_name="atanan_isler.xlsx")

    elif page == "👥 Kullanıcı Yönetimi": # Madde 11
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("new_user"):
                name = st.text_input("İsim Soyisim")
                u_email = st.text_input("Mail")
                role = st.selectbox("Yetki", ["Saha Personeli", "Müdür", "Yönetici", "Admin"])
                if st.form_submit_button("Ekle"):
                    pw = hashlib.sha256("1234".encode()).hexdigest()
                    conn.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", (name, u_email, pw, role))
                    conn.commit()
                    st.success(f"{name} eklendi.")
                    st.rerun()

    conn.close()
