import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI VE KURULUM ---
def get_db():
    conn = sqlite3.connect('operasyon_v39.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, result_type TEXT, hakedis_durum TEXT, ret_sebebi TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Sistem Yöneticisi', 'Admin', '0555'),
        ('müdür@deneme.com', pw, 'Müdür', 'Müdür Bey', 'Müdür', '0555'),
        ('filiz@deneme.com', pw, 'Yönetici', 'Filiz Hanım', 'Yönetici', '0555'),
        ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', 'Saha Personeli', '0555'),
        ('doguscan@deneme.com', pw, 'Saha Personeli', 'Doğuşcan Gürol', 'Saha Personeli', '0555'),
        ('cuneyt@deneme.com', pw, 'Saha Personeli', 'Cüneyt Bey', 'Saha Personeli', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 2. YARDIMCI ARAÇLAR ---
def get_welcome_msg(name):
    hr = datetime.now().hour
    if 8 <= hr < 12: m = f"Günaydın {name} İyi Çalışmalar"
    elif 12 <= hr < 18: m = f"İyi Günler {name} İyi Çalışmalar"
    elif 18 <= hr < 24: m = f"İyi Akşamlar {name} İyi Çalışmalar"
    else: m = f"İyi Geceler {name} İyi Çalışmalar"
    return f"✨ **{m}**"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def create_zip(photos_json):
    if not photos_json: return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        photos = json.loads(photos_json)
        for i, p_hex in enumerate(photos):
            z.writestr(f"foto_{i+1}.jpg", bytes.fromhex(p_hex))
    return buf.getvalue()

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Gaziantep", "Konya", "Mersin", "Samsun"]

# --- 3. GİRİŞ VE OTURUM ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Saha Operasyon v39")
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
    # MENÜ YAPILANDIRMASI
    st.sidebar.title(f"👤 {st.session_state['u_name']}")
    st.sidebar.caption(f"🛡️ {st.session_state['u_role']}")
    
    if st.session_state['u_role'] in ['Admin', 'Müdür', 'Yönetici']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşler", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    cp = st.session_state.page
    conn = get_db()

    # --- 4. EKRANLAR ---

    if cp == "🏠 Ana Sayfa":
        st.subheader(get_welcome_msg(st.session_state['u_name']))
        c1, c2, c3 = st.columns(3)
        if st.session_state['u_role'] == 'Admin':
            c1.metric("✅ Tamamlanan", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("📌 Bekleyen Atamalar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            last_week = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
            c3.metric("📊 Haftalık İş", conn.execute("SELECT COUNT(*) FROM tasks WHERE updated_at >= ?", (last_week,)).fetchone()[0])
        else:
            c1.metric("✅ Tamamladığım", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state['u_email']}' AND result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("⏳ Atanan İşlerim", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state['u_email']}' AND status='Bekliyor'").fetchone()[0])

    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        # Müdür listede görünmez
        plist = pd.read_sql("SELECT email FROM users WHERE role NOT IN ('Müdür')", conn)['email'].tolist()
        with st.form("task_add"):
            t1 = st.text_input("İş Başlığı"); t2 = st.selectbox("Saha Personeli", plist); t3 = st.selectbox("Şehir", SEHIRLER); t4 = st.text_area("Açıklama")
            if st.form_submit_button("Atama Yap"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city) VALUES (?,?,?,?,?)", (t2, t1, t4, 'Bekliyor', t3))
                conn.commit(); st.success("İş atandı."); st.rerun()

    elif cp == "⏳ Atanan İşler":
        st.header("⏳ Atanan İşlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['u_email']}' AND status IN ('Bekliyor', 'Kabul Yapılabilir', 'Ret Edildi')", conn)
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']} {'(🔴 RET)' if r['status'] == 'Ret Edildi' else ''}"):
                if r['ret_sebebi']: st.error(f"Ret Sebebi: {r['ret_sebebi']}")
                res = st.selectbox("Durum", ["Seçiniz", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"], key=f"r_{r['id']}")
                rep = st.text_area("Rapor", value=r['report'] if r['report'] else "", key=f"n_{r['id']}")
                fots = st.file_uploader("Fotoğraf/Dosya", accept_multiple_files=True, key=f"f_{r['id']}")
                c1, c2 = st.columns(2)
                if c1.button("💾 Kaydet (Taslak)", key=f"ts_{r['id']}"):
                    p_hex = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET report=?, photos_json=?, result_type=? WHERE id=?", (rep, p_hex, res, r['id']))
                    conn.commit(); st.toast("Kaydedildi.")
                if c2.button("🚀 İşi Gönder", key=f"g_{r['id']}", type="primary"):
                    p_hex = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    status = 'Giriş Mail Onayı Bekler' if res == 'Giriş Mail Onayı Bekler' else 'Onay Bekliyor'
                    conn.execute("UPDATE tasks SET status=?, result_type=?, report=?, photos_json=?, updated_at=? WHERE id=?", (status, res, rep, p_hex, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                    conn.commit(); st.rerun()

    elif cp == "✅ Tamamlanan İşler":
        st.header("📑 İş Arşivi")
        f1, f2, f3, f4 = st.columns(4)
        workers = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist()
        s_date = f1.date_input("Tarih", value=None)
        s_worker = f2.selectbox("Çalışan", ["Hepsi"] + workers)
        s_city = f3.selectbox("Şehir", ["Hepsi"] + SEHIRLER)
        s_type = f4.selectbox("Durum", ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler", "Türk Telekom Onayında", "Hak Edişi Alındı"])
        
        query = "SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Mail Onayı Bekler')"
        if s_worker != "Hepsi": query += f" AND assigned_to='{s_worker}'"
        if s_city != "Hepsi": query += f" AND city='{s_city}'"
        if s_type == "Tamamlanan İşler": query += " AND result_type='İŞ TAMAMLANDI'"
        elif s_type == "Tamamlanamayan İşler": query += " AND result_type IN ('GİRİŞ YAPILAMADI', 'TEPKİLİ', 'MAL SAHİBİ GELMİYOR')"
        
        df = pd.read_sql(query, conn)
        st.dataframe(df, use_container_width=True)
        st.download_button("📊 Excel Çıktısı", to_excel(df), "Saha_Rapor.xlsx")

        for _, r in df.iterrows():
            with st.expander(f"🔍 Detay: {r['title']}"):
                if r['photos_json']:
                    st.download_button("📦 Fotoğrafları İndir (ZIP/RAR)", create_zip(r['photos_json']), f"is_{r['id']}.zip", key=f"z_{r['id']}")
                c1, c2, c3 = st.columns(3)
                if c1.button("📡 TT Onay Bekleniyor", key=f"ttb_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                
                ret_sebep = st.text_input("Ret Sebebi", key=f"ret_s_{r['id']}")
                if c2.button("✅ Kabul", key=f"ok_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                if c3.button("❌ Ret", key=f"no_{r['id']}"):
                    if ret_sebep:
                        conn.execute("UPDATE tasks SET status='Ret Edildi', ret_sebebi=? WHERE id=?", (ret_sebep, r['id']))
                        conn.commit(); st.rerun()
                    else: st.warning("Ret için sebep giriniz.")

    elif cp == "📡 TT Onay Bekleyenler":
        st.header("📡 TT Onay Listesi")
        df_tt = pd.read_sql("SELECT * FROM tasks WHERE status='Türk Telekom Onayında'", conn)
        if df_tt.empty: st.info("Bekleyen iş yok.")
        else:
            st.dataframe(df_tt)
            for _, r in df_tt.iterrows():
                if st.button(f"💰 Hak Edişe Gönder ({r['title']})", key=f"heg_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Paneli")
        # filiz@deneme.com için özel görünüm
        h_df = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleyen', 'Hak Edişi Alındı')", conn)
        if h_df.empty: st.info("✅ Hak Ediş Bekleyen Atama Yok")
        else:
            st.dataframe(h_df)
            st.download_button("📊 Excel İndir", to_excel(h_df), "Hakedis.xlsx")
            if st.session_state['u_email'] == 'filiz@deneme.com' or st.session_state['u_role'] == 'Admin':
                for _, r in h_df.iterrows():
                    if r['status'] == 'Hak Ediş Bekleyen':
                        if st.button(f"✅ Hak Ediş Alındı İşaretle ({r['title']})"):
                            conn.execute("UPDATE tasks SET status='Hak Edişi Alındı' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "👥 Kullanıcı Yönetimi":
        if st.session_state['u_role'] in ['Admin', 'Müdür']:
            st.header("👥 Kullanıcı Yönetimi")
            u_df = pd.read_sql("SELECT name, email, role, title, phone FROM users", conn)
            st.dataframe(u_df)
            c1, c2 = st.columns(2)
            with c1.expander("➕ Ekle"):
                with st.form("u_add"):
                    ne = st.text_input("E-posta"); nn = st.text_input("Ad"); nt = st.text_input("Ünvan"); np = st.text_input("Şifre")
                    nr = st.selectbox("Yetki", ["Saha Personeli", "Admin", "Müdür", "Yönetici"])
                    if st.form_submit_button("Ekle"):
                        conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (ne, hashlib.sha256(np.encode()).hexdigest(), nr, nn, nt, ""))
                        conn.commit(); st.rerun()
            with c2.expander("❌ Sil"):
                se = st.selectbox("Silinecek", u_df['email'].tolist())
                if st.button("Kullanıcıyı Sil"): conn.execute("DELETE FROM users WHERE email=?", (se,)); conn.commit(); st.rerun()

    elif cp == "👤 Profilim":
        st.header("👤 Profil Güncelle")
        with st.form("prof"):
            nm = st.text_input("E-posta", value=st.session_state['u_email'])
            np = st.text_input("Telefon", value=st.session_state['u_phone'])
            if st.form_submit_button("Güncellemeleri Kaydet"):
                conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (nm, np, st.session_state['u_email']))
                conn.commit(); st.success("Bilgiler güncellendi."); st.rerun()

    elif cp == "🎒 Zimmetim":
        st.header("🎒 Zimmetli Eşyalarım")
        inv = pd.read_sql(f"SELECT item_name, quantity, updated_by FROM inventory WHERE assigned_to='{st.session_state['u_email']}'", conn)
        st.table(inv)

    elif cp == "📜 Çalışmalarım":
        st.header("📜 Tüm Çalışmalarım")
        df_hist = pd.read_sql(f"SELECT title, city, result_type, updated_at FROM tasks WHERE assigned_to='{st.session_state['u_email']}' AND result_type IS NOT NULL", conn)
        st.dataframe(df_hist, use_container_width=True)

    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Onay Paneli")
        go_df = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        if go_df.empty: st.info("✅ Onay Bekleyen Atama Yok")
        else:
            for _, r in go_df.iterrows():
                with st.expander(f"İş: {r['title']}"):
                    if st.button(f"✅ Kabul Yapılabilir Olarak Gönder ({r['id']})"):
                        conn.execute("UPDATE tasks SET status='Kabul Yapılabilir' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Zimmet & Envanter")
        f_user = st.selectbox("Personel", ["Hepsi"] + pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist())
        q = "SELECT * FROM inventory"
        if f_user != "Hepsi": q += f" WHERE assigned_to='{f_user}'"
        inv_df = pd.read_sql(q, conn)
        st.table(inv_df)
        if st.session_state['u_role'] == 'Admin':
            st.download_button("📥 Excel İndir", to_excel(inv_df), "Envanter.xlsx")
        
        if st.session_state['u_role'] in ['Admin', 'Müdür']:
            with st.expander("➕ Zimmet Düzenle/Ekle"):
                with st.form("inv_form"):
                    m1 = st.text_input("Malzeme"); m2 = st.selectbox("Personel", pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist())
                    m3 = st.number_input("Adet", 1)
                    if st.form_submit_button("Zimmetle"):
                        conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (m1, m2, m3, st.session_state['u_name']))
                        conn.commit(); st.rerun()
