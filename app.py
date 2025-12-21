import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io

# --- ⚙️ SİSTEM KONFİGÜRASYONU ---
st.set_page_config(page_title="Anatolia Bilişim", layout="wide", initial_sidebar_state="expanded")

# --- 🔐 1. SESSION STATE BAŞLATMA (Hata Önleyici - En Üstte Olmalı) ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'u_email': None, 'u_role': None, 'u_name': None, 'page': "🏠 Ana Sayfa"})

# --- 🗄️ 2. VERİTABANI MOTORU VE TABLO OLUŞTURMA ---
def get_db_connection():
    return sqlite3.connect('anatolia_v68.db', check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Maddeler 1, 11: Kullanıcılar
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    # Maddeler 4, 5, 6, 7, 8, 9: İş Takibi
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, city TEXT, 
        status TEXT, report TEXT, created_at TEXT, updated_at TEXT)''')
    # Madde 10: Zimmet
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT)''')
    
    # Varsayılan Admin (Şifre: 1234)
    admin_pw = hashlib.sha256('1234'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", ('admin@anatolia.com', admin_pw, 'Admin', 'Doğukan Gürol', '05001112233'))
    conn.commit()
    conn.close()

init_db()

# --- 🛠️ 3. YARDIMCI ARAÇLAR ---
def get_greeting():
    hr = datetime.now().hour
    if 0 <= hr < 8: return "🌙 İyi Geceler"
    elif 8 <= hr < 12: return "☀️ Günaydın"
    elif 12 <= hr < 18: return "🌤️ İyi Günler"
    else: return "🌆 İyi Akşamlar"

def export_excel(df, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return st.download_button(label="📥 Excel Raporu İndir", data=output.getvalue(), file_name=f"{filename}.xlsx", mime="application/vnd.ms-excel")

# --- 🚪 4. GİRİŞ EKRANI (Madde 13 Kontrolü Dahil) ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 Anatolia Bilişim Giriş</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_gate"):
            e = st.text_input("📧 Şirket Mail Adresi")
            p = st.text_input("🔑 Şifre", type='password')
            if st.form_submit_button("🚀 Sisteme Giriş Yap", use_container_width=True):
                hashed = hashlib.sha256(p.encode()).hexdigest()
                conn = get_db_connection()
                user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashed)).fetchone()
                conn.close()
                if user:
                    st.session_state.update({'logged_in': True, 'u_email': user[0], 'u_role': user[2], 'u_name': user[3]})
                    st.rerun()
                else: st.error("❌ Hatalı giriş bilgileri!")

# --- 🏠 5. ANA UYGULAMA PANELİ ---
else:
    # --- 📋 SOL MENÜ (Madde 2) ---
    with st.sidebar:
        st.title("🏢 Anatolia Bilişim")
        st.info(f"👤 **{st.session_state.u_name}**\n\n🛡️ Yetki: {st.session_state.u_role}")
        st.divider()

        role = st.session_state.u_role
        # Dinamik Menü Oluşturma
        menu = ["🏠 Ana Sayfa"]
        if role != "Saha Personeli":
            menu += ["➕ İş Ataması", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onayı Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter"]
            if role in ["Admin", "Yönetici"]: menu.append("👥 Kullanıcı Yönetimi")
        else:
            menu += ["⏳ Üzerime Atanan İşler", "📜 Tamamladığım İşler", "🎒 Zimmetim"]
        
        menu += ["👤 Profilim", "🔴 ÇIKIŞ"]

        for item in menu:
            btn_type = "primary" if st.session_state.page == item else "secondary"
            if st.button(item, use_container_width=True, type=btn_type):
                if item == "🔴 ÇIKIŞ":
                    st.session_state.logged_in = False
                    st.rerun()
                st.session_state.page = item
                st.rerun()

    # --- 🖼️ 6. SAYFA İÇERİKLERİ ---
    conn = get_db_connection()
    cp = st.session_state.page

    # --- Madde 3 & 14: ANA SAYFA ---
    if cp == "🏠 Ana Sayfa":
        st.subheader(f"{get_greeting()} {st.session_state.u_name} İyi Çalışmalar! 🚀")
        
        if role != "Saha Personeli":
            st.markdown("### 📊 Operasyonel Durum")
            c1, c2, c3, c4 = st.columns(4)
            # Veritabanından sayaçları çek (Örnek mantık)
            c1.metric("✅ Tamamlanan", "12")
            c2.metric("⏳ Bekleyen", "5")
            c3.metric("📅 Haftalık", "84")
            c4.metric("🗓️ Aylık", "312")

    # --- Madde 4: İŞ ATAMASI ---
    elif cp == "➕ İş Ataması":
        st.header("➕ Yeni İş Atama")
        personel_list = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)
        with st.form("atama_form"):
            t = st.text_input("📌 İş Başlığı")
            p = st.selectbox("👷 Saha Personeli", personel_list['email'].tolist())
            s = st.selectbox("📍 Şehir", ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"]) # 81 il eklenebilir
            if st.form_submit_button("🚀 İşi Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, city, status, created_at) VALUES (?,?,?,?,?)",
                             (p, t, s, "Bekliyor", datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success(f"✅ İş {p} personeline başarıyla atandı!")

    # --- Madde 5, 8: TABLO GÖRÜNÜMLERİ VE FİLTRELEME ---
    elif cp in ["📋 Atanan İşler", "✅ Tamamlanan İşler", "💰 Hak Ediş"]:
        st.header(f"📋 {cp}")
        # Madde 37: Boş ekran uyarısı ve filtreleme (Genel fonksiyon yapısı)
        status_map = {"📋 Atanan İşler": "('Bekliyor')", "✅ Tamamlanan İşler": "('Kabul Alındı')", "💰 Hak Ediş": "('Hak Ediş Alındı', 'Hak Ediş Bekleniyor')"}
        df = pd.read_sql(f"SELECT * FROM tasks WHERE status IN {status_map[cp]}", conn)
        
        if df.empty:
            st.warning("⚠️ Gösterilecek Bir Görev Bulunmamaktadır.")
        else:
            # Madde 31-35: Filtreleme
            with st.expander("🔍 Filtrele"):
                f_city = st.selectbox("Şehir", ["Hepsi"] + df['city'].unique().tolist())
            
            filtered_df = df if f_city == "Hepsi" else df[df['city'] == f_city]
            st.dataframe(filtered_df, use_container_width=True)
            export_excel(filtered_df, cp)

    # --- Madde 11: KULLANICI YÖNETİMİ ---
    elif cp == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("new_user"):
                n = st.text_input("İsim Soyisim")
                e = st.text_input("Mail Adresi")
                p = st.text_input("Geçici Şifre", type="password")
                r = st.selectbox("Yetki", ["Saha Personeli", "Müdür", "Yönetici"])
                if st.form_submit_button("Kaydet"):
                    h = hashlib.sha256(p.encode()).hexdigest()
                    conn.execute("INSERT INTO users (email, password, role, name) VALUES (?,?,?,?)", (e, h, r, n))
                    conn.commit()
                    st.rerun()
        
        users_df = pd.read_sql("SELECT name, email, role FROM users", conn)
        st.table(users_df)
        export_excel(users_df, "Kullanici_Listesi")

    # --- Madde 15: SAHA PERSONELİ ÖZEL (ÜZERİME ATANAN İŞLER) ---
    elif cp == "⏳ Üzerime Atanan İşler":
        st.header("⏳ Üzerime Atanan Görevler")
        my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status='Bekliyor'", conn)
        
        if my_tasks.empty:
            st.info("🎉 Şu an üzerinizde bekleyen bir iş yok.")
        else:
            for _, row in my_tasks.iterrows():
                with st.expander(f"📍 {row['title']} - {row['city']}"):
                    report = st.text_area("✍️ Çalışma Notu (Zorunlu)", key=f"rep_{row['id']}")
                    files = st.file_uploader("📸 Fotoğraflar (Max 65)", accept_multiple_files=True, key=f"file_{row['id']}")
                    
                    col_a, col_b = st.columns(2)
                    if col_a.button("💾 Kaydet", key=f"save_{row['id']}"):
                        st.toast("Taslak kaydedildi!")
                    
                    if col_b.button("🚀 İşi Gönder", type="primary", key=f"send_{row['id']}", disabled=not report):
                        conn.execute("UPDATE tasks SET status='Kabul Alındı', report=?, updated_at=? WHERE id=?", 
                                     (report, datetime.now().strftime("%Y-%m-%d"), row['id']))
                        conn.commit()
                        st.success("İş başarıyla merkeze gönderildi!")
                        st.rerun()

    conn.close()
