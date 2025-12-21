import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(page_title="Anatolia Bilişim", layout="wide")

# 🌍 81 İl Listesi (Özet)
ILLER = ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir", "Konya", "Samsun"] 

# --- 2. SESSION STATE BAŞLATMA (HATA ÖNLEYİCİ) ---
# AttributeError'u engellemek için kodun en başında tanımlanmalıdır.
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'page' not in st.session_state:
    st.session_state['page'] = "🏠 Ana Sayfa"

# --- 3. VERİTABANI VE TABLO OLUŞTURMA ---
def init_db():
    conn = sqlite3.connect('anatolia_v67.db')
    c = conn.cursor()
    # Kullanıcılar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    # İşler Tablosu (Madde 4, 5, 6, 7, 8, 9)
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  city TEXT, status TEXT, report TEXT, created_at TEXT, updated_at TEXT)''')
    # Zimmet Tablosu (Madde 10)
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT)''')
    
    # Varsayılan Admin Hesabı (Şifre: 1234)
    admin_pw = hashlib.sha256('1234'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", 
              ('admin@anatolia.com', admin_pw, 'Admin', 'Admin Ana Hesap', '05000000000'))
    conn.commit()
    conn.close()

init_db()

# --- 4. GENEL FİLTRELEME VE GÖRÜNÜM MOTORU (Madde 31-37) ---
def render_filtered_page(title, query_params):
    st.title(f"{title}")
    
    conn = sqlite3.connect('anatolia_v67.db')
    # Belirtilen statüye göre verileri çek
    query = f"SELECT * FROM tasks WHERE status IN {query_params}"
    df = pd.read_sql(query, conn)
    conn.close()

    # Filtreleme Paneli (Madde 5, 31, 32, 33, 34)
    with st.expander("🔍 Arama ve Filtreleme Seçenekleri", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1: f_pers = st.selectbox("👷 Personel", ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"])
        with c2: f_sehir = st.selectbox("📍 Şehir", ["Hepsi"] + sorted(df['city'].unique().tolist()) if not df.empty else ["Hepsi"])
        with c3: f_durum = st.selectbox("🚦 Durum", ["Hepsi"] + sorted(df['status'].unique().tolist()) if not df.empty else ["Hepsi"])

    # Veri Kontrolü ve Uyarı Mesajı (Madde 37)
    if df.empty:
        st.info(f"✨ Şu anda gösterilecek bir **'{title}'** kaydı bulunmamaktadır.")
        return

    # Filtreleri Uygula
    if f_pers != "Hepsi": df = df[df['assigned_to'] == f_pers]
    if f_sehir != "Hepsi": df = df[df['city'] == f_sehir]
    if f_durum != "Hepsi": df = df[df['status'] == f_durum]

    # Tablo Gösterimi
    st.dataframe(df, use_container_width=True)

    # Excel Raporu (Madde 5, 30)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Excel (CSV) Olarak İndir", csv, f"{title}.csv", "text/csv")

# --- 5. GİRİŞ EKRANI (Madde 13) ---
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔐 Anatolia Bilişim Giriş</h1>", unsafe_allow_html=True)
    with st.container():
        left, mid, right = st.columns([1, 2, 1])
        with mid:
            email = st.text_input("📧 Şirket Mail Adresi")
            password = st.text_input("🔑 Şifre", type='password')
            if st.button("🚀 Sisteme Giriş Yap", use_container_width=True):
                hashed_pw = hashlib.sha256(password.encode()).hexdigest()
                conn = sqlite3.connect('anatolia_v67.db')
                u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hashed_pw)).fetchone()
                conn.close()
                if u:
                    st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3]})
                    st.rerun()
                else:
                    st.error("❌ Hatalı mail adresi veya şifre!")

# --- 6. ANA UYGULAMA PANELİ ---
else:
    # Sol Menü (Madde 2)
    with st.sidebar:
        st.markdown(f"## 🏢 Anatolia Bilişim")
        st.success(f"👤 **{st.session_state.u_name}**\n🛡️ Yetki: *{st.session_state.u_role}*")
        st.divider()

        # Menü Listesi
        menu_items = ["🏠 Ana Sayfa", "➕ İş Ataması", "📋 Atanan İşler", "📨 Giriş Onayları", 
                      "📡 TT Onayı Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", 
                      "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi", "👤 Profilim", "🔴 ÇIKIŞ"]
        
        for item in menu_items:
            # Aktif Sayfa Rengi Farklılığı (Madde 2)
            if st.button(item, use_container_width=True, type="primary" if st.session_state.page == item else "secondary"):
                if item == "🔴 ÇIKIŞ":
                    st.session_state.logged_in = False
                    st.rerun()
                st.session_state.page = item
                st.rerun()

    # Sayfa İçerikleri
    p = st.session_state.page

    if p == "🏠 Ana Sayfa":
        st.header("✨ Hoş Geldiniz, Anatolia Bilişim Operasyon Merkezi")
        # Saat bazlı karşılama mesajı buraya eklenebilir (Madde 3)

    elif p == "➕ İş Ataması":
        st.header("➕ Yeni İş Ataması")
        with st.form("atama"):
            title = st.text_input("📌 İş Başlığı")
            city = st.selectbox("📍 Şehir", ILLER)
            personel = st.text_input("👷 Saha Personeli Maili")
            if st.form_submit_button("🚀 İşi Ata"):
                conn = sqlite3.connect('anatolia_v67.db')
                conn.execute("INSERT INTO tasks (assigned_to, title, city, status, created_at) VALUES (?,?,?,?,?)",
                             (personel, title, city, "Bekliyor", datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                conn.close()
                st.success("✅ İş başarıyla atandı!")

    elif p == "📋 Atanan İşler":
        render_filtered_page("📋 Atanan İşler", "('Bekliyor')")

    elif p == "📨 Giriş Onayları":
        render_filtered_page("📨 Giriş Onayları", "('Giriş Maili Bekler')")

    elif p == "✅ Tamamlanan İşler":
        render_filtered_page("✅ Tamamlanan İşler", "('Kabul Alındı')")

    elif p == "💰 Hak Ediş":
        render_filtered_page("💰 Hak Ediş Paneli", "('Hak Ediş Alındı', 'Hak Ediş Bekleniyor')")
