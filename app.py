import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import os
import zipfile

# --- 1. KURUMSAL AYARLAR VE KLASÖRLER ---
COMPANY_NAME = "Anatolia Bilişim"
UPLOAD_FOLDER = "saha_personeli_dosyalari"
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]

# --- 2. VERİTABANI MOTORU ---
def get_db():
    return sqlite3.connect('anatolia_v63.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_paths TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    # Tanımlı Kullanıcılar (Madde 3, 4, 41)
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Admin Ana Hesap', '05001112233'),
        ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '05004445566'),
        ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', '05007778899'),
        ('doguscan@deneme.com', pw, 'Saha Personeli', 'Doğuşcan Gürol', '05002223344'),
        ('cuneyt@deneme.com', pw, 'Saha Personeli', 'Cüneyt Bey', '05006667788')
    ]
    for u in users: c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. FONKSİYONLAR (EXCEL, ZIP, SELAMLAMA) ---
def excel_indir(df, key):
    if df.empty: return None
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

def zip_dosyasi_yap(filepaths):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for f in filepaths.split(','):
            if os.path.exists(f): z.write(f, os.path.basename(f))
    return buf.getvalue()

def get_greeting(name):
    hr = datetime.now().hour
    msg = "Günaydın" if 0 <= hr < 12 else "İyi Günler" if 12 <= hr < 18 else "İyi Akşamlar" if 18 <= hr < 0 else "İyi Geceler"
    return f"✨ {msg} **{name}**, İyi Çalışmalar!"

# --- 4. ORTAK FİLTRELEME (Madde 30, 31, 32, 33, 34, 35) ---
def apply_filters(df, page_key):
    st.write("### 🔍 Filtreleme")
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_tarih = st.date_input("Tarih", [], key=f"t_{page_key}")
    with c2: 
        p_list = ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"]
        f_pers = st.selectbox("Personel", p_list, key=f"p_{page_key}")
    with c3: f_sehir = st.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"s_{page_key}")
    
    d_opts = ["Hepsi", "Tamamlanan İşler", "Tamamlanmayan İşler", "Giriş Mail Onayı Bekler"]
    if st.session_state.u_role in ['Admin', 'Müdür']:
        d_opts += ["Türk Telekom Onayında", "Hak Ediş Bekleniyor", "Hak Ediş Alındı"]
    with c4: f_durum = st.selectbox("Durum", d_opts, key=f"d_{page_key}")
    
    filtered = df.copy()
    if not filtered.empty:
        if f_pers != "Hepsi": filtered = filtered[filtered['assigned_to'] == f_pers]
        if f_sehir != "Hepsi": filtered = filtered[filtered['city'] == f_sehir]
        if f_durum == "Tamamlanan İşler": filtered = filtered[filtered['result_type'] == 'İŞ TAMAMLANDI']
        elif f_durum == "Tamamlanmayan İşler": filtered = filtered[filtered['result_type'].isin(['GİRİŞ YAPILAMADI', 'TEPKİLİ', 'MAL SAHİBİ GELMİYOR'])]
        elif f_durum != "Hepsi": filtered = filtered[filtered['status'] == f_durum]

    ex_data = excel_indir(filtered, page_key)
    if ex_data: st.download_button("📥 Excel İndir", ex_data, f"{page_key}.xlsx", key=f"btn_{page_key}")
    
    if filtered.empty:
        st.warning(f"Gösterilecek {page_key.replace('_',' ')} Bulunmamaktadır")
        return pd.DataFrame()
    return filtered

# --- 5. ANA DÖNGÜ VE LOGIN ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title(f"🏢 {COMPANY_NAME}")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı Giriş")
else:
    # --- SIDEBAR (Madde 39, 42, 43) ---
    st.sidebar.markdown(f"# 🏢 {COMPANY_NAME}")
    st.sidebar.info(f"👤 {st.session_state.u_name} \n 🛡️ {st.session_state.u_role}")
    st.sidebar.divider()

    role = st.session_state.u_role
    if role == 'Admin':
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi", "👤 Profilim"]
    elif role == 'Müdür':
        menu = ["🏠 Ana Sayfa", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi", "👤 Profilim"]
    else: # Saha Personeli
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]

    for m in menu:
        btn_type = "primary" if st.session_state.page == m else "secondary"
        if st.sidebar.button(m, use_container_width=True, type=btn_type):
            st.session_state.page = m; st.rerun()
    
    if st.sidebar.button("🔴 Çıkış"): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- EKRAN MANTIKLARI ---
    
    if cp == "🏠 Ana Sayfa":
        st.subheader(get_greeting(st.session_state.u_name))
        # Madde 15, 27
        if role in ['Admin', 'Müdür']:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Bekleyen Atamalar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            c3.metric("Haftalık Toplam İş", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", ((datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d"),)).fetchone()[0])
        else:
            c1, c2 = st.columns(2)
            c1.metric("Tamamladığım", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Atanan İşlerim", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status='Bekliyor'").fetchone()[0])

    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        pers_df = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)
        with st.form("atama"):
            t = st.text_input("Başlık"); p = st.selectbox("Personel (Müdür Görünmez)", pers_df['email'].tolist()); s = st.selectbox("Şehir", ILLER)
            opt = st.checkbox("Giriş Mail Onayı Beklensin mi?")
            if st.form_submit_button("Ata"):
                stt = "Giriş Mail Onayı Bekler" if opt else "Bekliyor"
                conn.execute("INSERT INTO tasks (assigned_to, title, status, city, created_at) VALUES (?,?,?,?,?)", (p, t, stt, s, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.success("İş Atandı")

    elif cp == "⏳ Atanan İşlerim": # SAHA PERSONELİ (Madde 2, 5, 21, 28)
        st.header("⏳ Üzerimdeki İşler")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor', 'Ret Edildi', 'Kabul Yapılabilir')", conn)
        if tasks.empty: st.info("Gösterilecek Atanmış İş Bulunmamaktadır")
        for _, r in tasks.iterrows():
            with st.expander(f"📌 {r['title']} ({r['city']})"):
                # Madde 5
                res = st.selectbox("İş Sonucu", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"], key=f"res_{r['id']}")
                report = st.text_area("Rapor / Not", value=r['report'] if r['report'] else "", key=f"rep_{r['id']}")
                fots = st.file_uploader("Fotoğraf/Dosya Ekle", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                if c1.button("💾 Kaydet (Taslak)", key=f"save_{r['id']}"):
                    conn.execute("UPDATE tasks SET report=?, result_type=? WHERE id=?", (report, res, r['id']))
                    conn.commit(); st.success("Taslak Kaydedildi")
                
                if c2.button("🚀 İşi Onaya Gönder", type="primary", key=f"send_{r['id']}"):
                    paths = []
                    if fots:
                        for f in fots:
                            path = os.path.join(UPLOAD_FOLDER, f"{r['id']}_{f.name}")
                            with open(path, "wb") as file: file.write(f.getvalue())
                            paths.append(path)
                    
                    conn.execute("UPDATE tasks SET status='Onay Bekliyor', report=?, result_type=?, photos_paths=?, updated_at=? WHERE id=?", 
                                (report, res, ",".join(paths), datetime.now().strftime("%Y-%m-%d"), r['id']))
                    conn.commit(); st.success("İş Gönderildi!"); st.rerun()

    elif cp == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İşler")
        raw = pd.read_sql("SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Mail Onayı Bekler')", conn)
        df = apply_filters(raw, "tamamlanan_isler")
        if not df.empty:
            for _, r in df.iterrows():
                with st.expander(f"🔍 Detay: {r['title']} - {r['assigned_to']}"):
                    st.write(f"**Sonuç:** {r['result_type']} | **Not:** {r['report']}")
                    if r['photos_paths']:
                        st.image([p for p in r['photos_paths'].split(',')], width=150)
                        # Madde 16: RAR (ZIP) İndirme
                        zip_data = zip_dosyasi_yap(r['photos_paths'])
                        st.download_button("🗂️ Fotoğrafları İndir (ZIP)", zip_data, f"is_{r['id']}_fotolar.zip")
                    
                    # Madde 22: Onay Akışı
                    if role in ['Admin', 'Müdür']:
                        cc1, cc2, cc3 = st.columns(3)
                        if cc1.button("📡 TT Onayına Gönder", key=f"tt_{r['id']}"):
                            conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                        if cc2.button("✅ Kabul", key=f"kab_{r['id']}"):
                            conn.execute("UPDATE tasks SET status='Hak Ediş Bekleniyor' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                        if cc3.button("❌ Ret Et", key=f"ret_{r['id']}"):
                            sebep = st.text_input("Ret Sebebi", key=f"seb_{r['id']}")
                            if sebep:
                                conn.execute("UPDATE tasks SET status='Ret Edildi', ret_sebebi=? WHERE id=?", (sebep, r['id'])); conn.commit(); st.rerun()

    elif cp == "📡 TT Onay Bekleyenler":
        st.header("📡 TT Onay Paneli")
        raw = pd.read_sql("SELECT * FROM tasks WHERE status='Türk Telekom Onayında'", conn)
        df = apply_filters(raw, "tt_onay")
        if not df.empty:
            for _, r in df.iterrows():
                if st.button(f"💰 {r['title']} -> Hak Edişe Gönder", key=f"he_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Bekleniyor' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Paneli")
        raw = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleniyor', 'Hak Ediş Alındı')", conn)
        df = apply_filters(raw, "hakedis_ekrani")
        if not df.empty:
            for _, r in df.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"**{r['title']}** - {r['assigned_to']} - {r['status']}")
                if r['status'] == 'Hak Ediş Bekleniyor' and role in ['Admin', 'Müdür']:
                    if col2.button("✔️ Alındı", key=f"al_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Hak Ediş Alındı' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "📦 Zimmet & Envanter": # Madde 17
        st.header("📦 Zimmet & Envanter")
        if role in ['Admin', 'Müdür']:
            with st.form("zimmet_ekle"):
                it = st.text_input("Ürün"); pers = st.selectbox("Personel", ILLER); qt = st.number_input("Adet", 1)
                if st.form_submit_button("Zimmetle"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity) VALUES (?,?,?)", (it, pers, qt))
                    conn.commit(); st.rerun()
        
        raw_inv = pd.read_sql("SELECT * FROM inventory", conn)
        # Madde 17 Filtreleme
        f_df = apply_filters(raw_inv.rename(columns={'assigned_to':'assigned_to'}), "zimmet")
        if not f_df.empty: st.table(f_df)

    elif cp == "👥 Kullanıcı Yönetimi": # Madde 18, 38
        st.header("👥 Kullanıcı Yönetimi")
        with st.form("yeni_kullanici"):
            c1, c2 = st.columns(2)
            ne = c1.text_input("E-posta"); nn = c2.text_input("Ad Soyad")
            nr = c1.selectbox("Rol", ["Admin", "Müdür", "Saha Personeli"]); np = c2.text_input("Şifre", type="password")
            nt = c1.text_input("Telefon")
            if st.form_submit_button("Ekle/Güncelle"):
                conn.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?,?)", (ne, hashlib.sha256(np.encode()).hexdigest(), nr, nn, nt))
                conn.commit(); st.success("İşlem Başarılı"); st.rerun()
        
        u_list = pd.read_sql("SELECT email, name, role, phone FROM users", conn)
        st.dataframe(u_list)
        d_email = st.selectbox("Silinecek Kullanıcı", u_list['email'].tolist())
        if st.button("❌ Kullanıcıyı Sil"):
            conn.execute("DELETE FROM users WHERE email=?", (d_email,))
            conn.commit(); st.rerun()

    elif cp == "👤 Profilim": # Madde 19, 28, 40
        st.header("👤 Profil Ayarlarım")
        u = conn.execute("SELECT email, phone, name FROM users WHERE email=?", (st.session_state.u_email,)).fetchone()
        with st.form("profil_update"):
            new_mail = st.text_input("Mail Adresi", u[0], disabled=(role=='Müdür'))
            new_phone = st.text_input("Telefon", u[1], disabled=(role=='Müdür'))
            new_pass = st.text_input("Yeni Şifre (Boş bırakırsanız değişmez)", type="password")
            if st.form_submit_button("💾 Güncellemeleri Kaydet"):
                if new_pass:
                    hp = hashlib.sha256(new_pass.encode()).hexdigest()
                    conn.execute("UPDATE users SET email=?, phone=?, password=? WHERE email=?", (new_mail, new_phone, hp, st.session_state.u_email))
                else:
                    conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (new_mail, new_phone, st.session_state.u_email))
                conn.commit(); st.success("Güncellendi!")

    elif cp == "📨 Giriş Onayları": # Madde 20
        st.header("📨 Giriş Onayları Bekleyen")
        raw = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        df = apply_filters(raw, "giris_onay")
        if not df.empty:
            for _, r in df.iterrows():
                if st.button(f"✅ {r['title']} -> Kabul Yapılabilir Olarak Gönder", key=f"gok_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Kabul Yapılabilir' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "📜 Çalışmalarım": # Madde 25
        st.header("📜 Tüm Geçmiş Çalışmalarım")
        raw = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}'", conn)
        df = apply_filters(raw, "calismalarim")
        if not df.empty: st.dataframe(df)

    elif cp == "🎒 Zimmetim": # Madde 26
        st.header("🎒 Üzerime Zimmetli Eşyalar")
        zimmet = pd.read_sql(f"SELECT item_name, quantity FROM inventory WHERE assigned_to='{st.session_state.u_email}'", conn)
        if zimmet.empty: st.info("Zimmetli eşyanız bulunmamaktadır.")
        else: st.table(zimmet)
