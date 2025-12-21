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

# 81 İl Tanımı
ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]

# --- 2. VERİTABANI VE YETKİ ---
def get_db():
    return sqlite3.connect('operasyon_v45.db', check_same_thread=False)

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

# --- 3. FONKSİYONLAR ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

def save_photos(uploaded_files, task_id):
    file_names = []
    for i, file in enumerate(uploaded_files):
        fname = f"task_{task_id}_{datetime.now().strftime('%H%M%S')}_{i}.jpg"
        with open(os.path.join(UPLOAD_DIR, fname), "wb") as f: f.write(file.getbuffer())
        file_names.append(fname)
    return json.dumps(file_names)

def advanced_filter(df, key_suffix):
    st.write("### 🔍 Filtreleme")
    c1, c2, c3, c4 = st.columns(4)
    p_filter = c1.selectbox("Personel", ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()), key=f"p_{key_suffix}")
    c_filter = c2.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"c_{key_suffix}")
    d_filter = c3.selectbox("Durum", ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler", "Giriş Mail Onayı Bekler", "Türk Telekom Onayında", "Hak Ediş Bekleyen", "Hak Ediş Alındı"], key=f"d_{key_suffix}")
    t_filter = c4.date_input("Tarih Aralığı", [], key=f"t_{key_suffix}")
    
    if p_filter != "Hepsi": df = df[df['assigned_to'] == p_filter]
    if c_filter != "Hepsi": df = df[df['city'] == c_filter]
    if d_filter == "Tamamlanan İşler": df = df[df['result_type'] == "İŞ TAMAMLANDI"]
    elif d_filter == "Tamamlanamayan İşler": df = df[df['result_type'].isin(["GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"])]
    elif d_filter != "Hepsi": df = df[df['status'] == d_filter]
    return df

# --- 4. ARAYÜZ MANTIĞI ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🛡️ Saha Operasyon v45")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
else:
    # Sidebar Karşılama ve Menü
    hr = datetime.now().hour
    msg = "Günaydın" if 8<=hr<12 else "İyi Günler" if 12<=hr<18 else "İyi Akşamlar" if 18<=hr<24 else "İyi Geceler"
    st.sidebar.markdown(f"### {msg} \n**{st.session_state.u_name}**")
    
    menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler Takip", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    if st.session_state.u_role == 'Saha Personeli':
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    
    # --- SAHA PERSONELİ: ATANAN İŞLERİM (TASLAK MANTIĞI) ---
    if st.session_state.page == "⏳ Atanan İşlerim":
        st.header("⏳ Üzerimdeki İşler")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor', 'Kabul Yapılabilir', 'Ret Edildi')", conn)
        
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']} - {r['city']}", expanded=False):
                # Veritabanından mevcut taslak verileri çekiyoruz
                current_report = r['report'] if r['report'] else ""
                current_result = r['result_type'] if r['result_type'] else "Seçiniz"
                
                res_idx = ["Seçiniz", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"].index(current_result) if current_result in ["Seçiniz", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"] else 0
                
                res = st.selectbox("Durum", ["Seçiniz", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"], index=res_idx, key=f"res_{r['id']}")
                rep = st.text_area("Rapor / Notlar", value=current_report, key=f"rep_{r['id']}")
                
                # Mevcut Taslak Fotoğrafları Göster
                if r['photos_json']:
                    st.markdown("**📂 Kayıtlı Taslak Fotoğraflar:**")
                    f_cols = st.columns(5)
                    for i, fn in enumerate(json.loads(r['photos_json'])):
                        f_cols[i%5].image(os.path.join(UPLOAD_DIR, fn), use_container_width=True)
                
                fots = st.file_uploader("Yeni Fotoğraf Ekle", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                if c1.button("💾 Kaydet (Taslak)", key=f"ts_{r['id']}"):
                    p_json = save_photos(fots, r['id']) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET report=?, result_type=?, photos_json=? WHERE id=?", (rep, res, p_json, r['id']))
                    conn.commit(); st.success("Taslak veritabanına kaydedildi."); st.rerun()
                
                if c2.button("🚀 İşi Gönder", type="primary", key=f"send_{r['id']}"):
                    p_json = save_photos(fots, r['id']) if fots else r['photos_json']
                    new_status = "Giriş Mail Onayı Bekler" if res == "Giriş Mail Onayı Bekler" else "Onay Bekliyor"
                    conn.execute("UPDATE tasks SET status=?, report=?, result_type=?, photos_json=?, updated_at=? WHERE id=?", 
                                (new_status, rep, res, p_json, datetime.now().strftime("%Y-%m-%d %H:%M"), r['id']))
                    conn.commit(); st.success("İş başarıyla gönderildi."); st.rerun()

    # --- YÖNETİM: TAMAMLANAN İŞLER VE EXCEL ---
    elif st.session_state.page == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Arşivi")
        df = pd.read_sql("SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Mail Onayı Bekler', 'Onay Bekliyor')", conn)
        df = advanced_filter(df, "arsiv")
        st.dataframe(df, use_container_width=True)
        
        # Güvenli Excel İndirme
        st.download_button("📊 Seçili Filtrelerle Excel İndir", to_excel(df), f"Rapor_{datetime.now().strftime('%Y%m%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        # Onay/Ret Süreci
        for _, r in df.iterrows():
            with st.expander(f"🔍 İş Detayı: {r['title']}"):
                if r['photos_json']:
                    cols = st.columns(4)
                    for i, fn in enumerate(json.loads(r['photos_json'])): cols[i%4].image(os.path.join(UPLOAD_DIR, fn))
                
                c1, c2, c3 = st.columns(3)
                if c1.button("📡 TT Onay Bekler", key=f"tt_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                
                ret_msg = st.text_input("Ret Sebebi (Ret edilecekse)", key=f"ret_msg_{r['id']}")
                if c2.button("✅ Kabul / Hak Edişe Gönder", key=f"ok_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                if c3.button("❌ Ret Et", key=f"no_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Ret Edildi', ret_sebebi=? WHERE id=?", (ret_msg, r['id'])); conn.commit(); st.rerun()

    # --- DİĞER EKRANLAR (FİLTRE VE EXCEL ENTEGRELİ) ---
    elif st.session_state.page == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Yönetimi")
        df = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleyen', 'Hak Edişi Alındı')", conn)
        df = advanced_filter(df, "he")
        st.dataframe(df)
        st.download_button("📥 Hak Ediş Excel", to_excel(df), "Hakedis.xlsx")
        for _, r in df.iterrows():
            if r['status'] == 'Hak Ediş Bekleyen' and st.button(f"Alındı İşaretle: {r['id']}"):
                conn.execute("UPDATE tasks SET status='Hak Edişi Alındı' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    # --- KULLANICI YÖNETİMİ ---
    elif st.session_state.page == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        u_df = pd.read_sql("SELECT name, email, role, phone FROM users", conn)
        st.table(u_df)
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("new_user"):
                n_e = st.text_input("E-posta"); n_n = st.text_input("Ad Soyad"); n_p = st.text_input("Şifre"); n_r = st.selectbox("Yetki", ["Saha Personeli", "Müdür", "Admin"])
                if st.form_submit_button("Kaydet"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (n_e, hashlib.sha256(n_p.encode()).hexdigest(), n_r, n_n, ""))
                    conn.commit(); st.rerun()

    # --- ANA SAYFA (SAYAÇLAR) ---
    elif st.session_state.page == "🏠 Ana Sayfa":
        st.write(f"## Hoş Geldiniz, {st.session_state.u_name}")
        if st.session_state.u_role in ['Admin', 'Müdür']:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Atanmış Bekleyen", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            # Haftalık sayaç
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            c3.metric("Haftalık Toplam İş", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", (week_ago,)).fetchone()[0])
