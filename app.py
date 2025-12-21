import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import zipfile
import os

# --- 1. AYARLAR VE STORAGE ---
UPLOAD_DIR = "uploaded_photos"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ILLER = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"
]

# --- 2. VERİTABANI YÖNETİMİ ---
def get_db():
    conn = sqlite3.connect('operasyon_v44.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Admin', 'Sistem Yöneticisi', '0555'),
        ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', 'Müdür', '0555'),
        ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', 'Saha Personeli', '0555'),
        ('doguscan@deneme.com', pw, 'Saha Personeli', 'Doğuşcan Gürol', 'Saha Personeli', '0555'),
        ('cuneyt@deneme.com', pw, 'Saha Personeli', 'Cüneyt Bey', 'Saha Personeli', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. YARDIMCI FONKSİYONLAR (HATA GİDERİLEN KISIMLAR) ---
def get_welcome_msg(name):
    hr = datetime.now().hour
    if 8 <= hr < 12: m = "Günaydın"
    elif 12 <= hr < 18: m = "İyi Günler"
    elif 18 <= hr < 24: m = "İyi Akşamlar"
    else: m = "İyi Geceler"
    return f"✨ **{m} {name}, İyi Çalışmalar**"

def to_excel(df):
    """Görseldeki AttributeError hatasını gideren güvenli Excel dönüştürücü."""
    output = io.BytesIO()
    if df.empty:
        # Boş dataframe durumunda hata almamak için örnek bir yapı oluştur
        df = pd.DataFrame([["Veri Bulunamadı"]], columns=["Mesaj"])
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

def save_photos(uploaded_files, task_id):
    file_names = []
    for i, file in enumerate(uploaded_files):
        ext = file.name.split('.')[-1]
        fname = f"task_{task_id}_{i}_{datetime.now().strftime('%H%M%S')}.{ext}"
        with open(os.path.join(UPLOAD_DIR, fname), "wb") as f:
            f.write(file.getbuffer())
        file_names.append(fname)
    return json.dumps(file_names)

def create_zip(photos_json):
    if not photos_json: return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        try:
            fnames = json.loads(photos_json)
            for fname in fnames:
                fpath = os.path.join(UPLOAD_DIR, fname)
                if os.path.exists(fpath): z.write(fpath, fname)
        except: return None
    return buf.getvalue()

def advanced_filter(df, key_suffix):
    """Tüm ekranlar için standart filtreleme paneli."""
    with st.expander("🔍 Filtreleme Paneli", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        
        # Personel Filtresi
        plist = ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if 'assigned_to' in df.columns else ["Hepsi"]
        person_filter = c1.selectbox("Personel", plist, key=f"pers_{key_suffix}")
        
        # Şehir Filtresi
        city_filter = c2.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"city_{key_suffix}")
        
        # Durum Filtresi
        dlist = ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler"]
        if st.session_state.u_role in ['Admin', 'Müdür']:
            dlist += ["Türk Telekom Onayında", "Hak Ediş Bekleyen", "Hak Ediş Alındı"]
        status_filter = c3.selectbox("Durum", dlist, key=f"stat_{key_suffix}")
        
        # Tarih Filtresi (Opsiyonel)
        date_filter = c4.date_input("Tarih Aralığı", [], key=f"date_{key_suffix}")

        if person_filter != "Hepsi": df = df[df['assigned_to'] == person_filter]
        if city_filter != "Hepsi": df = df[df['city'] == city_filter]
        
        if status_filter == "Tamamlanan İşler":
            df = df[df['result_type'] == "İŞ TAMAMLANDI"]
        elif status_filter == "Tamamlanamayan İşler":
            df = df[df['result_type'].isin(["GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"])]
        elif status_filter != "Hepsi":
            df = df[df['status'] == status_filter]
            
    return df

# --- 4. ANA DÖNGÜ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🛡️ Saha Operasyon Sistemi")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'u_title':u[4], 'u_phone':u[5], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı bilgiler.")
else:
    st.sidebar.title(f"👤 {st.session_state['u_name']}")
    if st.session_state.u_role in ['Admin', 'Müdür']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşler", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    cp = st.session_state.page
    conn = get_db()

    # --- EKRANLAR ---

    if cp == "🏠 Ana Sayfa":
        st.subheader(get_welcome_msg(st.session_state['u_name']))
        c1, c2, c3 = st.columns(3)
        if st.session_state.u_role in ['Admin', 'Müdür']:
            c1.metric("✅ Tamamlanan", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("⏳ Atanan Bekleyen", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            start_week = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
            c3.metric("📊 Haftalık Toplam", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", (start_week,)).fetchone()[0])
        else:
            c1.metric("✅ Tamamladığım", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("⏳ Üzerimdeki İşler", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor','Kabul Yapılabilir','Ret Edildi')").fetchone()[0])

    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        plist = pd.read_sql("SELECT email FROM users WHERE role = 'Saha Personeli'", conn)['email'].tolist()
        with st.form("task_add"):
            t1 = st.text_input("İş Başlığı"); t2 = st.selectbox("Saha Personeli", plist); t3 = st.selectbox("Şehir", ILLER); t4 = st.text_area("Açıklama")
            if st.form_submit_button("Atama Yap"):
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city, created_at) VALUES (?,?,?,?,?,?)", (t2, t1, t4, 'Bekliyor', t3, now))
                conn.commit(); st.success("İş atandı."); st.rerun()

    elif cp == "⏳ Atanan İşler":
        st.header("⏳ Atanan İşlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor', 'Kabul Yapılabilir', 'Ret Edildi')", conn)
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']} {'(🔴 RET)' if r['status'] == 'Ret Edildi' else ''}"):
                if r['ret_sebebi']: st.error(f"Ret Sebebi: {r['ret_sebebi']}")
                res = st.selectbox("Durum Seçin", ["Seçiniz", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"], key=f"r_{r['id']}")
                rep = st.text_area("Notlar", value=r['report'] if r['report'] else "", key=f"n_{r['id']}")
                fots = st.file_uploader("Dosya Ekle", accept_multiple_files=True, key=f"f_{r['id']}")
                c1, c2 = st.columns(2)
                if c1.button("💾 Kaydet (Taslak)", key=f"ts_{r['id']}"):
                    p_json = save_photos(fots, r['id']) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET report=?, photos_json=?, result_type=? WHERE id=?", (rep, p_json, res, r['id']))
                    conn.commit(); st.toast("Taslak kaydedildi.")
                if c2.button("🚀 İşi Gönder", key=f"g_{r['id']}", type="primary"):
                    p_json = save_photos(fots, r['id']) if fots else r['photos_json']
                    stt = 'Giriş Mail Onayı Bekler' if res == 'Giriş Mail Onayı Bekler' else 'Onay Bekliyor'
                    conn.execute("UPDATE tasks SET status=?, result_type=?, report=?, photos_json=?, updated_at=? WHERE id=?", 
                                (stt, res, rep, p_json, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                    conn.commit(); st.rerun()

    elif cp == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Arşivi")
        df = pd.read_sql("SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Mail Onayı Bekler')", conn)
        df = advanced_filter(df, "arsiv")
        st.dataframe(df, use_container_width=True)
        
        # EXCEL BUTONU (HATA GİDERİLEN NOKTA)
        st.download_button(
            label="📊 Excel İndir",
            data=to_excel(df),
            file_name=f"Arsiv_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_arsiv_btn"
        )

        for _, r in df.iterrows():
            with st.expander(f"🔍 Detay: {r['title']}"):
                if r['photos_json']:
                    fnames = json.loads(r['photos_json'])
                    cols = st.columns(4)
                    for i, fn in enumerate(fnames):
                        fpath = os.path.join(UPLOAD_DIR, fn)
                        if os.path.exists(fpath): cols[i%4].image(fpath, use_container_width=True)
                    st.download_button("📦 Fotoğrafları İndir (ZIP)", create_zip(r['photos_json']), f"is_{r['id']}.zip", key=f"z_{r['id']}")
                
                c1, c2, c3 = st.columns(3)
                if c1.button("📡 TT Onay Bekleniyor", key=f"ttb_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                ret_tx = st.text_input("Ret Sebebi", key=f"ret_tx_{r['id']}")
                if c2.button("✅ Kabul", key=f"ok_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                if c3.button("❌ Ret", key=f"no_{r['id']}"):
                    if ret_tx:
                        conn.execute("UPDATE tasks SET status='Ret Edildi', ret_sebebi=? WHERE id=?", (ret_tx, r['id']))
                        conn.commit(); st.rerun()
                    else: st.warning("Sebep girin.")

    elif cp == "📡 TT Onay Bekleyenler":
        st.header("📡 Türk Telekom Onay Listesi")
        tt_df = pd.read_sql("SELECT * FROM tasks WHERE status='Türk Telekom Onayında'", conn)
        tt_df = advanced_filter(tt_df, "tt")
        st.dataframe(tt_df)
        st.download_button("📊 Excel İndir", to_excel(tt_df), "TT_Rapor.xlsx", key="dl_tt_btn")
        for _, r in tt_df.iterrows():
            if st.button(f"💰 Hak Edişe Gönder ({r['title']})", key=f"he_{r['id']}"):
                conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Paneli")
        h_df = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleyen', 'Hak Edişi Alındı')", conn)
        h_df = advanced_filter(h_df, "he")
        st.dataframe(h_df)
        st.download_button("📊 Excel İndir", to_excel(h_df), "Hakedis.xlsx", key="dl_he_btn")
        if st.session_state.u_email == 'filiz@deneme.com' or st.session_state.u_role == 'Admin':
            for _, r in h_df.iterrows():
                if r['status'] == 'Hak Ediş Bekleyen':
                    if st.button(f"✅ Hak Ediş Alındı İşaretle ({r['id']})"):
                        conn.execute("UPDATE tasks SET status='Hak Edişi Alındı' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Onay Bekleyenler")
        go_df = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        go_df = advanced_filter(go_df, "go")
        st.download_button("📊 Excel İndir", to_excel(go_df), "Giris_Onay.xlsx", key="dl_go_btn")
        for _, r in go_df.iterrows():
            if st.button(f"✅ Kabul Yapılabilir ({r['id']})"):
                conn.execute("UPDATE tasks SET status='Kabul Yapılabilir' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "👤 Profilim":
        st.header("👤 Profil Ayarları")
        with st.form("prof"):
            new_mail = st.text_input("E-posta", value=st.session_state.u_email)
            new_phone = st.text_input("Telefon", value=st.session_state.u_phone)
            if st.form_submit_button("Güncellemeleri Kaydet"):
                if st.session_state.u_role != 'Müdür':
                    conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (new_mail, new_phone, st.session_state.u_email))
                    conn.commit(); st.success("Bilgiler güncellendi."); st.rerun()
                else: st.warning("Müdür yetkilisi bilgileri kilitlidir.")
        with st.form("pass"):
            p1 = st.text_input("Yeni Şifre", type='password')
            p2 = st.text_input("Tekrar", type='password')
            if st.form_submit_button("Şifre Güncelle"):
                if p1 == p2 and p1:
                    conn.execute("UPDATE users SET password=? WHERE email=?", (hashlib.sha256(p1.encode()).hexdigest(), st.session_state.u_email))
                    conn.commit(); st.success("Şifre değişti.")

    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Envanter Yönetimi")
        inv_df = pd.read_sql("SELECT * FROM inventory", conn)
        inv_df = advanced_filter(inv_df, "inv")
        st.table(inv_df)
        if st.session_state.u_role == 'Admin':
            st.download_button("📥 Excel İndir", to_excel(inv_df), "Envanter.xlsx", key="dl_inv_btn")
        if st.session_state.u_role in ['Admin', 'Müdür']:
            with st.expander("➕ Zimmet Ekle"):
                with st.form("iz"):
                    m1 = st.text_input("Malzeme"); m2 = st.selectbox("Personel", pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist()); m3 = st.number_input("Adet", 1)
                    if st.form_submit_button("Zimmetle"):
                        conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (m1, m2, m3, st.session_state.u_name))
                        conn.commit(); st.rerun()

    elif cp == "👥 Kullanıcı Yönetimi":
        if st.session_state.u_role in ['Admin', 'Müdür']:
            st.header("👥 Kullanıcı Yönetimi")
            u_df = pd.read_sql("SELECT name, email, role, title, phone FROM users", conn)
            st.dataframe(u_df)
            c1, c2 = st.columns(2)
            with c1.expander("➕ Ekle"):
                with st.form("ua"):
                    ne = st.text_input("E-posta"); nn = st.text_input("Ad"); nt = st.text_input("Ünvan"); np = st.text_input("Şifre")
                    nr = st.selectbox("Yetki", ["Saha Personeli", "Admin", "Müdür"])
                    if st.form_submit_button("Ekle"):
                        conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (ne, hashlib.sha256(np.encode()).hexdigest(), nr, nn, nt, ""))
                        conn.commit(); st.rerun()
            with c2.expander("❌ Sil"):
                se = st.selectbox("Sil", u_df['email'].tolist())
                if st.button("Kullanıcıyı Sil"): conn.execute("DELETE FROM users WHERE email=?", (se,)); conn.commit(); st.rerun()

    elif cp == "📜 Çalışmalarım":
        st.header("📜 Tüm Çalışmalarım")
        st.dataframe(pd.read_sql(f"SELECT title, city, result_type, updated_at, status FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type IS NOT NULL", conn), use_container_width=True)

    elif cp == "🎒 Zimmetim":
        st.header("🎒 Üzerimdeki Zimmet")
        st.table(pd.read_sql(f"SELECT item_name, quantity, updated_by FROM inventory WHERE assigned_to='{st.session_state.u_email}'", conn))
