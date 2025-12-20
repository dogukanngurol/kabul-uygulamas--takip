import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI BAĞLANTISI VE TABLO KONTROLÜ ---
def get_db_connection():
    # Veritabanı adını 'operasyon_merkezi_v33.db' olarak güncelledik (Temiz başlangıç için)
    conn = sqlite3.connect('operasyon_merkezi_v33.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tablo yapılarını oluştur
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, result_type TEXT, hakedis_durum TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    # Varsayılan kullanıcıları ekle/güncelle
    def h(p): return hashlib.sha256(p.encode()).hexdigest()
    users = [
        ('admin@sirket.com', h('1234'), 'admin', 'Sistem Yöneticisi', 'Genel Müdür', '0555'),
        ('filiz@deneme.com', h('1234'), 'admin', 'Filiz Hanım', 'Müdür', '0555'),
        ('dogukan@deneme.com', h('1234'), 'worker', 'Doğukan Gürol', 'Saha Çalışanı', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", u)
    conn.commit()
    return conn

init_db()

# --- 2. YARDIMCI ARAÇLAR ---
def create_zip(photos_json):
    if not photos_json: return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        photos = json.loads(photos_json)
        for i, p_hex in enumerate(photos):
            z.writestr(f"foto_{i+1}.jpg", bytes.fromhex(p_hex))
    return buf.getvalue()

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Erzurum", "Gaziantep", "Konya"]

# --- 3. OTURUM YÖNETİMİ ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Giriş Paneli")
    with st.form("login_form"):
        u_email = st.text_input("E-posta")
        u_pass = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş Yap"):
            conn = get_db_connection()
            hp = hashlib.sha256(u_pass.encode()).hexdigest()
            user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (u_email, hp)).fetchone()
            if user:
                st.session_state.update({
                    'logged_in': True,
                    'user_email': user[0],
                    'user_name': user[3],
                    'user_title': user[4],
                    'role': user[2],
                    'page': "🏠 Ana Sayfa"
                })
                st.rerun()
            else:
                st.error("Giriş başarısız.")
else:
    # Menü Tasarımı
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.caption(f"📍 {st.session_state['user_title']}")
    
    # Sayfa Seçenekleri
    if st.session_state['role'] == 'admin':
        menu = ["🏠 Ana Sayfa", "➕ İş Atama & Takip", "📨 Giriş Onayları", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcılar"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşler", "📜 Geçmiş", "🎒 Zimmetim"]

    for m in menu:
        if st.sidebar.button(m, use_container_width=True):
            st.session_state.page = m
            st.rerun()

    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

    cp = st.session_state.page
    conn = get_db_connection()

    # --- TAMAMLANAN İŞLER EKRANI (VERİ KONTROLLÜ) ---
    if cp == "✅ Tamamlanan İşler":
        st.header("📑 İş Takip Arşivi")
        
        # Filtreler
        f1, f2, f3 = st.columns(3)
        workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist()
        sel_user = f1.selectbox("Çalışan", ["Hepsi"] + workers)
        sel_city = f2.selectbox("Şehir", ["Hepsi"] + SEHIRLER)
        sel_type = f3.selectbox("Durum", ["Hepsi", "Tamamlandı", "Türk Telekom Onayında", "Bekleyen"])

        # Sorgu Oluşturma
        query = "SELECT * FROM tasks WHERE 1=1"
        if sel_user != "Hepsi": query += f" AND assigned_to='{sel_user}'"
        if sel_city != "Hepsi": query += f" AND city='{sel_city}'"
        
        df = pd.read_sql(query, conn)

        if df.empty:
            st.warning("Görüntülenecek veri bulunamadı. Lütfen filtreleri kontrol edin veya yeni iş atayın.")
        else:
            st.dataframe(df, use_container_width=True)
            for _, r in df.iterrows():
                with st.expander(f"🔍 Detay: {r['title']}"):
                    st.write(f"**Rapor:** {r['report']}")
                    c1, c2, c3 = st.columns(3)
                    if r['photos_json']:
                        zip_data = create_zip(r['photos_json'])
                        c1.download_button("📂 ZIP İndir", zip_data, f"is_{r['id']}.zip", key=f"d_{r['id']}")
                    
                    if c2.button("🔵 TT Onayına Al", key=f"tt_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],))
                        conn.commit(); st.rerun()
                    
                    if c3.button("🟡 Beklet", key=f"bk_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Bekliyor' WHERE id=?", (r['id'],))
                        conn.commit(); st.rerun()

    # --- ZİMMET EKRANI ---
    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Envanter Yönetimi")
        inv_df = pd.read_sql("SELECT * FROM inventory", conn)
        if inv_df.empty:
            st.info("Henüz envanter kaydı yok.")
        else:
            st.table(inv_df)
        
        with st.form("new_inv"):
            item = st.text_input("Malzeme")
            target = st.selectbox("Personel", workers)
            qty = st.number_input("Adet", 1)
            if st.form_submit_button("Zimmetle"):
                conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)",
                             (item, target, qty, st.session_state['user_name']))
                conn.commit(); st.rerun()

    # --- DİĞER SAYFALAR İÇİN ANA YAPI ---
    elif cp == "🏠 Ana Sayfa":
        st.success(f"Sistem Aktif. Hoş geldiniz {st.session_state['user_name']}")
        st.info("Lütfen soldaki menüden işlem seçin.")
