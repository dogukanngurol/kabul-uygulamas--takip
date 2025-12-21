import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- 1. AYARLAR VE STORAGE ---
UPLOAD_DIR = "uploaded_photos"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]

# --- 2. VERİTABANI YÖNETİMİ ---
def get_db():
    return sqlite3.connect('operasyon_v46.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [('admin@sirket.com', pw, 'Admin', 'Sistem Admin', '0555'),
             ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '0555'),
             ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', '0555')]
    for u in users: c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. YARDIMCI FONKSİYONLAR ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

def advanced_filter(df, key_suffix):
    with st.expander("🔍 Filtreleme ve Raporlama", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        p_list = ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"]
        p_filter = c1.selectbox("Personel", p_list, key=f"p_{key_suffix}")
        c_filter = c2.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"c_{key_suffix}")
        d_list = ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler", "Onay Bekliyor", "Giriş Mail Onayı Bekler", "Türk Telekom Onayında", "Hak Ediş Bekleyen", "Hak Ediş Alındı"]
        d_filter = c3.selectbox("Durum", d_list, key=f"d_{key_suffix}")
        t_filter = c4.date_input("Tarih Aralığı", [], key=f"t_{key_suffix}")
        
        if p_filter != "Hepsi": df = df[df['assigned_to'] == p_filter]
        if c_filter != "Hepsi": df = df[df['city'] == c_filter]
        if d_filter == "Tamamlanan İşler": df = df[df['result_type'] == "İŞ TAMAMLANDI"]
        elif d_filter == "Tamamlanamayan İşler": df = df[df['result_type'].isin(["GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"])]
        elif d_filter != "Hepsi": df = df[df['status'] == d_filter]
        
        st.download_button("📥 Seçili Filtrelerle Excel İndir", to_excel(df), f"Rapor_{key_suffix}.xlsx", key=f"dl_{key_suffix}")
    return df

# --- 4. ARAYÜZ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🛡️ Saha Operasyon v46")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
else:
    # Sidebar Karşılama
    hr = datetime.now().hour
    msg = "Günaydın" if 8<=hr<12 else "İyi Günler" if 12<=hr<18 else "İyi Akşamlar" if 18<=hr<24 else "İyi Geceler"
    st.sidebar.markdown(f"### {msg}, {st.session_state.u_name}")
    
    # Menü Tanımları
    if st.session_state.u_role in ['Admin', 'Müdür']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler Takip", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- YÖNETİCİ EKRANLARI ---
    if cp == "🏠 Ana Sayfa":
        st.header(f"📊 Genel Durum Paneli")
        if st.session_state.u_role in ['Admin', 'Müdür']:
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Tamamlanan", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Atanan Bekleyen", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            c3.metric("Haftalık İş", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", (week_ago,)).fetchone()[0])
        else:
            st.info("Kendi çalışmalarınızı 'Çalışmalarım' sekmesinden görebilirsiniz.")

    elif cp == "📋 Atanan İşler Takip":
        st.header("📋 Tüm Atanan İşler")
        df = pd.read_sql("SELECT assigned_to, title, city, status, created_at FROM tasks WHERE status IN ('Bekliyor', 'Ret Edildi', 'Kabul Yapılabilir')", conn)
        df = advanced_filter(df, "takip")
        st.dataframe(df, use_container_width=True)

    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Onay Bekleyenler")
        df = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        df = advanced_filter(df, "giris_onay")
        for _, r in df.iterrows():
            if st.button(f"✅ Onayla (Kabul Yapılabilir): {r['title']}", key=f"go_{r['id']}"):
                conn.execute("UPDATE tasks SET status='Kabul Yapılabilir' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "📡 TT Onay Bekleyenler":
        st.header("📡 Türk Telekom Onay Listesi")
        df = pd.read_sql("SELECT * FROM tasks WHERE status='Türk Telekom Onayında'", conn)
        df = advanced_filter(df, "tt_onay")
        for _, r in df.iterrows():
            if st.button(f"💰 Hak Edişe Gönder: {r['title']}", key=f"tt_{r['id']}"):
                conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    # --- PERSONEL EKRANLARI (BOŞ GELEN YERLER) ---
    elif cp == "📜 Çalışmalarım":
        st.header("📜 Tüm Çalışmalarım")
        df = pd.read_sql(f"SELECT title, city, status, result_type, updated_at FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type IS NOT NULL", conn)
        if df.empty: st.warning("Henüz tamamlanmış bir çalışmanız bulunmuyor.")
        else: st.dataframe(df, use_container_width=True)

    elif cp == "🎒 Zimmetim":
        st.header("🎒 Üzerimdeki Zimmetli Eşyalar")
        df = pd.read_sql(f"SELECT item_name, quantity, updated_by FROM inventory WHERE assigned_to='{st.session_state.u_email}'", conn)
        if df.empty: st.info("Üzerinizde zimmetli bir eşya bulunmamaktadır.")
        else: st.table(df)

    elif cp == "👤 Profilim":
        st.header("👤 Profil ve Güvenlik")
        with st.form("p_update"):
            u_data = conn.execute("SELECT email, phone FROM users WHERE email=?", (st.session_state.u_email,)).fetchone()
            n_mail = st.text_input("E-posta", value=u_data[0])
            n_phone = st.text_input("Telefon", value=u_data[1] if u_data[1] else "")
            if st.form_submit_button("Güncellemeleri Kaydet"):
                if st.session_state.u_role != 'Müdür':
                    conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (n_mail, n_phone, st.session_state.u_email))
                    conn.commit(); st.success("Bilgiler güncellendi."); st.rerun()
                else: st.error("Müdür yetkisi bilgileri kilitlidir.")
        
        with st.form("pass_update"):
            st.write("🔑 **Şifre Değiştir**")
            p1 = st.text_input("Yeni Şifre", type='password'); p2 = st.text_input("Tekrar", type='password')
            if st.form_submit_button("Şifreyi Güncelle"):
                if p1 == p2 and p1:
                    conn.execute("UPDATE users SET password=? WHERE email=?", (hashlib.sha256(p1.encode()).hexdigest(), st.session_state.u_email))
                    conn.commit(); st.success("Şifre değiştirildi.")

    # --- ORTAK / DİĞER (TASLAK VE ATAMA) ---
    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        plist = pd.read_sql("SELECT email FROM users WHERE role = 'Saha Personeli'", conn)['email'].tolist()
        with st.form("t_add"):
            t1 = st.text_input("İş Başlığı"); t2 = st.selectbox("Personel", plist); t3 = st.selectbox("Şehir", ILLER); t4 = st.text_area("Açıklama")
            if st.form_submit_button("Atama Yap"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city, created_at) VALUES (?,?,?,?,?,?)", (t2, t1, t4, 'Bekliyor', t3, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.success("Atama başarılı."); st.rerun()

    # (Diğer ekran kodları v45 ile aynı mantıkta devam etmektedir...)
