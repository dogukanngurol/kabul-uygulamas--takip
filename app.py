import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI BAĞLANTISI VE KURULUM ---
def get_db():
    conn = sqlite3.connect('saha_operasyon_v34.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, result_type TEXT, hakedis_durum TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    def h(p): return hashlib.sha256(p.encode()).hexdigest()
    pw = h('1234')
    users = [
        ('admin@sirket.com', pw, 'admin', 'Sistem Yöneticisi', 'Genel Müdür', '0555'),
        ('filiz@deneme.com', pw, 'admin', 'Filiz Hanım', 'Müdür', '0555'),
        ('dogukan@deneme.com', pw, 'worker', 'Doğukan Gürol', 'Saha Çalışanı', '0555'),
        ('doguscan@deneme.com', pw, 'worker', 'Doğuşcan Gürol', 'Saha Çalışanı', '0555'),
        ('cuneyt@deneme.com', pw, 'worker', 'Cüneyt Bey', 'Saha Çalışanı', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", u)
    conn.commit()
    return conn

init_db()

# --- 2. YARDIMCI ARAÇLAR ---
def get_welcome_msg(name):
    hr = datetime.now().hour
    if 0 <= hr < 8: m = "İyi Geceler"
    elif 8 <= hr < 12: m = "Günaydın"
    elif 12 <= hr < 18: m = "İyi Günler"
    else: m = "İyi Akşamlar"
    return f"✨ {m} **{name}**, İyi Çalışmalar!"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

def create_zip(photos_json):
    if not photos_json: return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        photos = json.loads(photos_json)
        for i, p_hex in enumerate(photos):
            z.writestr(f"foto_{i+1}.jpg", bytes.fromhex(p_hex))
    return buf.getvalue()

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Erzurum", "Gaziantep", "Konya", "Samsun", "Trabzon"]

# --- 3. OTURUM VE GİRİŞ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Saha Yönetim Girişi")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4], 'user_phone':u[5], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı bilgiler.")
else:
    # Menü ve Yetki Kontrolü
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    if st.session_state['user_title'] in ['Müdür', 'Genel Müdür', 'Sistem Yöneticisi']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama & Takip", "📨 Giriş Onayları", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcılar"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşler", "📜 Çalışma Geçmişim", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    cp = st.session_state.page
    conn = get_db()

    # --- SAYFA: ANA SAYFA ---
    if cp == "🏠 Ana Sayfa":
        st.info(get_welcome_msg(st.session_state['user_name']))
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 Bekleyen İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
        c2.metric("✅ Tamamlananlar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Hak Edişi Alındı'").fetchone()[0])
        weekly = conn.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('Tamamlandı', 'Hak Edişi Alındı')").fetchone()[0]
        c3.metric("📊 Haftalık Toplam", weekly)

    # --- SAYFA: SAHA ÇALIŞANI - ATANAN İŞLER ---
    elif cp == "⏳ Atanan İşler":
        st.header("⏳ Üstüme Atanan İşler")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status IN ('Bekliyor', 'Kabul Yapılabilir')", conn)
        if tasks.empty: st.info("Bekleyen iş yok.")
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']} ({r['city']})"):
                res_opts = ["Seçiniz", "Giriş Mail Onayı Bekler", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
                res = st.selectbox("Sonuç Tipi", res_opts, key=f"res_{r['id']}")
                rep = st.text_area("İşte Yapılan Notlar", value=r['report'] if r['report'] else "", key=f"rep_{r['id']}")
                fots = st.file_uploader("Dosya/Fotoğraf", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                if c1.button("💾 Taslağı Kaydet", key=f"s_{r['id']}"):
                    p_hex = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET report=?, photos_json=?, result_type=? WHERE id=?", (rep, p_hex, res, r['id']))
                    conn.commit(); st.toast("Kaydedildi!")
                if c2.button("🚀 İşi Gönder", key=f"b_{r['id']}", type="primary"):
                    p_hex = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    new_status = 'Giriş Mail Onayı Bekler' if res == 'Giriş Mail Onayı Bekler' else 'Onay Bekliyor'
                    conn.execute("UPDATE tasks SET status=?, report=?, photos_json=?, result_type=?, updated_at=? WHERE id=?", 
                                 (new_status, rep, p_hex, res, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                    conn.commit(); st.rerun()

    # --- SAYFA: ÇALIŞAN - ZİMMET & GEÇMİŞ ---
    elif cp == "🎒 Zimmetim":
        st.header("🎒 Üzerimdeki Zimmetli Envanterler")
        df = pd.read_sql(f"SELECT item_name, quantity, updated_by FROM inventory WHERE assigned_to='{st.session_state['user_email']}'", conn)
        if df.empty: st.warning("Zimmet bulunamadı.")
        else: st.table(df)

    elif cp == "📜 Çalışma Geçmişim":
        st.header("📜 Geçmiş İşlerim")
        df = pd.read_sql(f"SELECT title, city, result_type, status, updated_at FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status NOT IN ('Bekliyor')", conn)
        st.dataframe(df, use_container_width=True)

    # --- SAYFA: TAMAMLANAN İŞLER (ADMİN/MÜDÜR) ---
    elif cp == "✅ Tamamlanan İşler":
        st.header("📑 İş Takip Arşivi")
        f1, f2, f3 = st.columns(3)
        workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist()
        f_user = f1.selectbox("Çalışan", ["Hepsi"] + workers)
        f_city = f2.selectbox("Şehir", ["Hepsi"] + SEHIRLER)
        f_type = f3.selectbox("Filtre Tipi", ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler", "Türk Telekom Onayında", "Bekleyen", "Hak Edişi Alındı"])
        
        q = "SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Mail Onayı Bekler')"
        if f_user != "Hepsi": q += f" AND assigned_to='{f_user}'"
        if f_city != "Hepsi": q += f" AND city='{f_city}'"
        if f_type == "Tamamlanan İşler": q += " AND result_type='İŞ TAMAMLANDI'"
        elif f_type == "Tamamlanamayan İşler": q += " AND result_type IN ('GİRİŞ YAPILAMADI', 'TEPKİLİ', 'MAL SAHİBİ GELMİYOR')"
        elif f_type == "Türk Telekom Onayında": q += " AND status='Türk Telekom Onayında'"
        elif f_type == "Bekleyen": q += " AND status='Bekliyor'"

        df = pd.read_sql(q, conn)
        st.dataframe(df[['id', 'title', 'assigned_to', 'city', 'result_type', 'status', 'updated_at']], use_container_width=True)
        st.download_button("📊 Excel Olarak İndir", to_excel(df), "Rapor.xlsx")

        for _, r in df.iterrows():
            with st.expander(f"🔍 Detay: {r['title']}"):
                st.write(f"**Not:** {r['report']}")
                c1, c2, c3, c4 = st.columns(4)
                if r['photos_json']:
                    c1.download_button("📂 ZIP İndir", create_zip(r['photos_json']), f"fotos_{r['id']}.zip", key=f"z_{r['id']}")
                if c2.button("🔵 TT Onayında", key=f"tt_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                if c3.button("🟡 Bekleyen", key=f"bk_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Bekliyor' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                if c4.button("🟢 Hak Edişe", key=f"he_{r['id']}"):
                    conn.execute("UPDATE tasks SET hakedis_durum='Hak Ediş Bekliyor', status='Tamamlandı' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
