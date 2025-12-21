import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
import zipfile
import os

# --- 1. DOSYA SİSTEMİ VE DİZİN AYARLARI ---
UPLOAD_DIR = "uploaded_photos"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- 2. VERİTABANI VE KURULUM ---
def get_db():
    conn = sqlite3.connect('operasyon_v40.db', check_same_thread=False)
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
    
    # Varsayılan Admin Şifresi: 1234
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Sistem Yöneticisi', 'Admin', '0555'),
        ('müdür@deneme.com', pw, 'Müdür', 'Müdür Bey', 'Müdür', '0555'),
        ('filiz@deneme.com', pw, 'Yönetici', 'Filiz Hanım', 'Yönetici', '0555'),
        ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', 'Saha Personeli', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. YARDIMCI FONKSİYONLAR ---
def get_welcome_msg(name):
    hr = datetime.now().hour
    if 8 <= hr < 12: return f"✨ **Günaydın {name}, İyi Çalışmalar**"
    elif 12 <= hr < 18: return f"✨ **İyi Günler {name}, İyi Çalışmalar**"
    else: return f"✨ **İyi Akşamlar {name}, İyi Çalışmalar**"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def save_photos(uploaded_files, task_id):
    """Dosyaları diske kaydeder ve isim listesini JSON döner."""
    file_names = []
    for i, file in enumerate(uploaded_files):
        ext = file.name.split('.')[-1]
        fname = f"task_{task_id}_{i}_{datetime.now().strftime('%H%M%S')}.{ext}"
        fpath = os.path.join(UPLOAD_DIR, fname)
        with open(fpath, "wb") as f:
            f.write(file.getbuffer())
        file_names.append(fname)
    return json.dumps(file_names)

def create_zip(photos_json):
    """Diskteki dosyaları bulup ZIP oluşturur."""
    if not photos_json: return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        try:
            filenames = json.loads(photos_json)
            for fname in filenames:
                fpath = os.path.join(UPLOAD_DIR, fname)
                if os.path.exists(fpath):
                    z.write(fpath, fname)
        except: return None
    return buf.getvalue()

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Gaziantep", "Konya", "Mersin", "Samsun"]

# --- 4. GİRİŞ VE OTURUM ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Saha Operasyon v40")
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
    # MENÜ SİSTEMİ
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

    # --- 5. EKRANLAR ---

    if cp == "🏠 Ana Sayfa":
        st.subheader(get_welcome_msg(st.session_state['u_name']))
        c1, c2 = st.columns(2)
        if st.session_state['u_role'] == 'Admin':
            c1.metric("✅ Tamamlanan", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("📌 Bekleyen Atamalar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
        else:
            c1.metric("✅ Tamamladığım", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state['u_email']}' AND result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("⏳ Atanan İşlerim", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state['u_email']}' AND status='Bekliyor'").fetchone()[0])

    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
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
                fots = st.file_uploader("Fotoğraf Ekle", accept_multiple_files=True, key=f"f_{r['id']}")
                
                if st.button("🚀 İşi Gönder", key=f"g_{r['id']}", type="primary"):
                    p_json = save_photos(fots, r['id']) if fots else r['photos_json']
                    status = 'Giriş Mail Onayı Bekler' if res == 'Giriş Mail Onayı Bekler' else 'Onay Bekliyor'
                    conn.execute("UPDATE tasks SET status=?, result_type=?, report=?, photos_json=?, updated_at=? WHERE id=?", 
                                (status, res, rep, p_json, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                    conn.commit(); st.success("İş gönderildi."); st.rerun()

    elif cp == "✅ Tamamlanan İşler":
        st.header("📑 İş Arşivi")
        df = pd.read_sql("SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Mail Onayı Bekler')", conn)
        st.dataframe(df, use_container_width=True)
        
        for _, r in df.iterrows():
            with st.expander(f"🔍 Detay: {r['title']}"):
                if r['photos_json']:
                    fnames = json.loads(r['photos_json'])
                    cols = st.columns(4)
                    for i, fn in enumerate(fnames):
                        fpath = os.path.join(UPLOAD_DIR, fn)
                        if os.path.exists(fpath):
                            cols[i % 4].image(fpath, use_container_width=True)
                    
                    z_data = create_zip(r['photos_json'])
                    if z_data:
                        st.download_button("📦 Fotoğrafları İndir (ZIP)", z_data, f"is_{r['id']}.zip", key=f"z_{r['id']}")
                
                c1, c2, c3 = st.columns(3)
                if c1.button("📡 TT Onayına Gönder", key=f"tt_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                
                ret_s = st.text_input("Ret Sebebi", key=f"ret_s_{r['id']}")
                if c2.button("✅ Kabul", key=f"ok_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                if c3.button("❌ Ret", key=f"no_{r['id']}"):
                    if ret_s:
                        conn.execute("UPDATE tasks SET status='Ret Edildi', ret_sebebi=? WHERE id=?", (ret_s, r['id']))
                        conn.commit(); st.rerun()
                    else: st.warning("Sebep giriniz.")

    elif cp == "👤 Profilim":
        st.header("👤 Profil ve Güvenlik")
        user_data = conn.execute("SELECT phone, title FROM users WHERE email=?", (st.session_state['u_email'],)).fetchone()
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("İletişim")
            with st.form("prof_up"):
                new_p = st.text_input("Telefon", value=user_data[0] if user_data[0] else "")
                if st.form_submit_button("Güncelle"):
                    conn.execute("UPDATE users SET phone=? WHERE email=?", (new_p, st.session_state['u_email']))
                    conn.commit(); st.success("Güncellendi.")

        with col2:
            st.subheader("Şifre Değiştir")
            with st.form("pass_up"):
                old_p = st.text_input("Eski Şifre", type="password")
                new_p1 = st.text_input("Yeni Şifre", type="password")
                new_p2 = st.text_input("Yeni Şifre (Onay)", type="password")
                if st.form_submit_button("Değiştir"):
                    h_old = hashlib.sha256(old_p.encode()).hexdigest()
                    if conn.execute("SELECT 1 FROM users WHERE email=? AND password=?", (st.session_state['u_email'], h_old)).fetchone():
                        if new_p1 == new_p2 and len(new_p1) >= 4:
                            h_new = hashlib.sha256(new_p1.encode()).hexdigest()
                            conn.execute("UPDATE users SET password=? WHERE email=?", (h_new, st.session_state['u_email']))
                            conn.commit(); st.success("Şifre güncellendi.")
                        else: st.error("Şifreler uyuşmuyor veya çok kısa.")
                    else: st.error("Eski şifre yanlış.")

    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Zimmet & Envanter")
        inv_df = pd.read_sql("SELECT * FROM inventory", conn)
        st.table(inv_df)
        if st.session_state['u_role'] in ['Admin', 'Müdür']:
            with st.expander("➕ Yeni Zimmet"):
                with st.form("inv_add"):
                    i1 = st.text_input("Malzeme"); i2 = st.selectbox("Personel", pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist()); i3 = st.number_input("Adet", 1)
                    if st.form_submit_button("Ekle"):
                        conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (i1, i2, i3, st.session_state['u_name']))
                        conn.commit(); st.rerun()

    # Uygulamanın diğer sayfaları (Hak Ediş, Kullanıcı Yönetimi vb.) önceki mantıkla aynı şekilde devam eder...
