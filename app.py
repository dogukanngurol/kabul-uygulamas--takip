import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI VE ÜNVAN YAPILANDIRMASI ---
UNVANLAR = ["Saha Personeli", "Yönetici", "Müdür", "Admin"]

def get_db():
    conn = sqlite3.connect('operasyon_v38.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, result_type TEXT, ret_reason TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'admin', 'Ahmet Salça', 'Admin', '0555'),
        ('filiz@deneme.com', pw, 'admin', 'Filiz Hanım', 'Müdür', '0555'),
        ('dogukan@deneme.com', pw, 'worker', 'Doğukan Gürol', 'Saha Personeli', '0555'),
        ('doguscan@deneme.com', pw, 'worker', 'Doğuşcan Gürol', 'Saha Personeli', '0555'),
        ('cuneyt@deneme.com', pw, 'worker', 'Cüneyt Bey', 'Saha Personeli', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 2. YARDIMCI ARAÇLAR ---
def get_welcome_msg(name):
    hr = datetime.now().hour
    if 8 <= hr < 12: msg = f"Günaydın {name} İyi Çalışmalar"
    elif 12 <= hr < 18: msg = f"İyi Günler {name} İyi Çalışmalar"
    elif 18 <= hr < 24: msg = f"İyi Akşamlar {name} İyi Çalışmalar"
    else: msg = f"İyi Geceler {name} İyi Çalışmalar"
    return f"✨ **{msg}**"

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

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Erzurum", "Gaziantep", "Konya", "Mersin", "Samsun"]

# --- 3. OTURUM VE GİRİŞ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Operasyon v38")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'u_title':u[4], 'u_phone':u[5], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı giriş.")
else:
    # MENÜ YETKİLERİ
    st.sidebar.title(f"👤 {st.session_state['u_name']}")
    st.sidebar.caption(f"🆔 {st.session_state['u_title']}")
    
    # Ünvana göre menü
    if st.session_state['u_title'] in ['Admin', 'Müdür']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşler", "📜 İş Geçmişim", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    
    if st.sidebar.button("🔴 ÇIKIŞ"): st.session_state.logged_in = False; st.rerun()

    cp = st.session_state.page
    conn = get_db()

    # --- 4. SAYFA İÇERİKLERİ ---

    if cp == "🏠 Ana Sayfa":
        st.subheader(get_welcome_msg(st.session_state['u_name']))
        if st.session_state['u_title'] == 'Admin':
            c1, c2, c3 = st.columns(3)
            c1.metric("✅ Biten İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("📌 Bekleyenler", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            last_week = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
            c3.metric("📊 Haftalık İş", conn.execute("SELECT COUNT(*) FROM tasks WHERE updated_at >= ?", (last_week,)).fetchone()[0])

    elif cp == "⏳ Atanan İşler":
        st.header("⏳ Atanan İşlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['u_email']}' AND status IN ('Bekliyor', 'Kabul Yapılabilir', 'Ret Edildi')", conn)
        for _, r in tasks.iterrows():
            with st.expander(f"📍 {r['title']} {'(🔴 RET)' if r['status'] == 'Ret Edildi' else ''}"):
                if r['ret_reason']: st.error(f"Ret Sebebi: {r['ret_reason']}")
                st.write(f"Açıklama: {r['description']}")
                res = st.selectbox("İşlem Durumu", ["Seçiniz", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"], key=f"res_{r['id']}")
                rep = st.text_area("Rapor Notu", value=r['report'] if r['report'] else "", key=f"rep_{r['id']}")
                fots = st.file_uploader("Dosyalar", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                if c1.button("💾 Kaydet (Taslak)", key=f"ts_{r['id']}"):
                    p_hex = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET report=?, photos_json=?, result_type=? WHERE id=?", (rep, p_hex, res, r['id']))
                    conn.commit(); st.toast("Kaydedildi.")
                if c2.button("🚀 İşi Gönder", key=f"g_{r['id']}", type="primary"):
                    p_hex = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    status = 'Giriş Mail Onayı Bekler' if res == 'Giriş Mail Onayı Bekler' else 'Onay Bekliyor'
                    conn.execute("UPDATE tasks SET status=?, result_type=?, report=?, photos_json=?, updated_at=?, ret_reason=NULL WHERE id=?", (status, res, rep, p_hex, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                    conn.commit(); st.rerun()

    elif cp == "✅ Tamamlanan İşler":
        st.header("📑 Tamamlanan İşler")
        f1, f2, f3, f4 = st.columns(4)
        workers = pd.read_sql("SELECT email FROM users WHERE title='Saha Personeli'", conn)['email'].tolist()
        s_date = f1.date_input("Tarih", value=None)
        s_user = f2.selectbox("Personel", ["Hepsi"] + workers)
        s_city = f3.selectbox("Şehir", ["Hepsi"] + SEHIRLER)
        
        st_opts = ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler"]
        if st.session_state['u_title'] == 'Müdür': st_opts += ["Türk Telekom Onayında", "Hak Edişi Alındı"]
        s_st = f4.selectbox("Filtre", st_opts)

        query = "SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Mail Onayı Bekler')"
        if s_user != "Hepsi": query += f" AND assigned_to='{s_user}'"
        if s_city != "Hepsi": query += f" AND city='{s_city}'"
        if s_st == "Tamamlanan İşler": query += " AND result_type='İŞ TAMAMLANDI'"
        elif s_st == "Tamamlanamayan İşler": query += " AND result_type IN ('GİRİŞ YAPILAMADI', 'TEPKİLİ', 'MAL SAHİBİ GELMİYOR')"
        
        df = pd.read_sql(query, conn)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Excel İndir", to_excel(df), "Rapor.xlsx")

        for _, r in df.iterrows():
            with st.expander(f"🔍 Detay: {r['title']}"):
                if r['photos_json']:
                    st.download_button("📦 Fotoğrafları İndir (ZIP)", create_zip(r['photos_json']), f"is_{r['id']}.zip", key=f"zip_{r['id']}")
                
                c1, c2, c3 = st.columns(3)
                if c1.button("📡 TT Onay Bekleniyor", key=f"tt_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                
                ret_reason = st.text_input("Ret Sebebi", key=f"rr_{r['id']}")
                if c2.button("✅ Kabul", key=f"ok_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                if c3.button("❌ Ret", key=f"no_{r['id']}"):
                    if ret_reason:
                        conn.execute("UPDATE tasks SET status='Ret Edildi', ret_reason=? WHERE id=?", (ret_reason, r['id']))
                        conn.commit(); st.rerun()
                    else: st.warning("Lütfen ret sebebi girin.")

    elif cp == "📡 TT Onay Bekleyenler":
        st.header("📡 TT Onay Listesi")
        df_tt = pd.read_sql("SELECT * FROM tasks WHERE status='Türk Telekom Onayında'", conn)
        if df_tt.empty: st.info("Onay bekleyen iş yok.")
        else:
            st.dataframe(df_tt)
            for _, r in df_tt.iterrows():
                if st.button(f"💰 Hak Edişe Gönder ({r['title']})", key=f"he_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş")
        df_he = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleyen', 'Hak Edişi Alındı')", conn)
        if df_he.empty: st.info("Onay bekleyen hak ediş yok.")
        else:
            st.dataframe(df_he)
            st.download_button("📊 Excel Al", to_excel(df_he), "Hakedis.xlsx")
            if st.session_state['u_email'] == 'filiz@deneme.com':
                for _, r in df_he.iterrows():
                    if r['status'] == 'Hak Ediş Bekleyen':
                        if st.button(f"✅ Hak Ediş Alındı İşaretle ({r['title']})"):
                            conn.execute("UPDATE tasks SET status='Hak Edişi Alındı' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        u_df = pd.read_sql("SELECT name, email, title, phone FROM users", conn)
        st.dataframe(u_df)
        c1, c2 = st.columns(2)
        with c1.expander("➕ Kullanıcı Ekle"):
            with st.form("add_u"):
                ne = st.text_input("E-posta"); nn = st.text_input("Ad"); np = st.text_input("Şifre")
                nt = st.selectbox("Ünvan", UNVANLAR)
                if st.form_submit_button("Ekle"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (ne, hashlib.sha256(np.encode()).hexdigest(), 'admin' if nt=='Admin' else 'worker', nn, nt, ""))
                    conn.commit(); st.rerun()
        with c2.expander("❌ Sil"):
            se = st.selectbox("Silinecek", u_df['email'].tolist())
            if st.button("Sil"): conn.execute("DELETE FROM users WHERE email=?", (se,)); conn.commit(); st.rerun()

    elif cp == "👤 Profilim":
        st.header("👤 Profil Güncelle")
        if st.session_state['u_title'] in ["Saha Personeli", "Yönetici"]:
            with st.form("prof"):
                nm = st.text_input("E-posta", value=st.session_state['u_email'])
                np = st.text_input("Telefon", value=st.session_state['u_phone'])
                if st.form_submit_button("Güncellemeleri Kaydet"):
                    conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (nm, np, st.session_state['u_email']))
                    conn.commit(); st.success("Kaydedildi."); st.rerun()
        else: st.info("Sadece Saha Personeli ve Yöneticiler bu alanı düzenleyebilir.")

    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş")
        # Müdür görünmez
        plist = pd.read_sql("SELECT email FROM users WHERE title != 'Müdür'", conn)['email'].tolist()
        with st.form("atama"):
            t1 = st.text_input("İş Başlığı"); t2 = st.selectbox("Personel", plist); t3 = st.selectbox("Şehir", SEHIRLER); t4 = st.text_area("Açıklama")
            if st.form_submit_button("Atama Yap"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city) VALUES (?,?,?,?,?)", (t2, t1, t4, 'Bekliyor', t3))
                conn.commit(); st.success("Atandı."); st.rerun()

    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Mail Onayları")
        df_g = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        if df_g.empty: st.info("✅ Onay Bekleyen Atama Yok")
        else:
            for _, r in df_g.iterrows():
                with st.expander(f"İş: {r['title']}"):
                    if st.button(f"✅ Kabul Yapılabilir Olarak Gönder ({r['id']})"):
                        conn.execute("UPDATE tasks SET status='Kabul Yapılabilir' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Zimmet & Envanter")
        f_user = st.selectbox("Filtre", ["Hepsi"] + pd.read_sql("SELECT email FROM users WHERE title='Saha Personeli'", conn)['email'].tolist())
        q_inv = "SELECT * FROM inventory"
        if f_user != "Hepsi": q_inv += f" WHERE assigned_to='{f_user}'"
        df_inv = pd.read_sql(q_inv, conn)
        st.table(df_inv)
        if st.session_state['u_title'] == 'Admin':
            st.download_button("📥 Excel", to_excel(df_inv), "Envanter.xlsx")
        
        if st.session_state['u_title'] == 'Müdür':
            with st.expander("➕ Zimmet Düzenle"):
                with st.form("inv_add"):
                    m1 = st.text_input("Malzeme"); m2 = st.selectbox("Personel", workers); m3 = st.number_input("Adet", 1)
                    if st.form_submit_button("Kaydet"):
                        conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (m1, m2, m3, st.session_state['u_name']))
                        conn.commit(); st.rerun()
