import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI BAĞLANTISI VE TABLO YAPILANDIRMASI ---
def get_db():
    conn = sqlite3.connect('operasyon_v36.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Kullanıcılar, İşler ve Envanter tabloları
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, result_type TEXT, hakedis_durum TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    # Varsayılan kullanıcılar (İstediğiniz liste)
    def h(p): return hashlib.sha256(p.encode()).hexdigest()
    pw = h('1234')
    users = [
        ('admin@sirket.com', pw, 'admin', 'Ahmet Salça', 'Genel Müdür', '0555'),
        ('filiz@deneme.com', pw, 'admin', 'Filiz Hanım', 'Müdür', '0555'),
        ('dogukan@deneme.com', pw, 'worker', 'Doğukan Gürol', 'Saha Çalışanı', '0555'),
        ('doguscan@deneme.com', pw, 'worker', 'Doğuşcan Gürol', 'Saha Çalışanı', '0555'),
        ('cuneyt@deneme.com', pw, 'worker', 'Cüneyt Bey', 'Saha Çalışanı', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 2. YARDIMCI ARAÇLAR (EXCEL, ZIP, SELAMLAMA) ---
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

TUM_SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Erzurum", "Gaziantep", "Konya", "Mersin", "Samsun"]

# --- 3. OTURUM YÖNETİMİ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Saha Operasyon Giriş")
    with st.form("login_form"):
        u_email = st.text_input("E-posta")
        u_pass = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş Yap"):
            conn = get_db()
            hp = hashlib.sha256(u_pass.encode()).hexdigest()
            user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (u_email, hp)).fetchone()
            if user:
                st.session_state.update({'logged_in': True, 'u_email': user[0], 'u_role': user[2], 'u_name': user[3], 'u_title': user[4], 'u_phone': user[5], 'page': "🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı giriş!")
else:
    # MENÜ YAPISI
    st.sidebar.title(f"👤 {st.session_state['u_name']}")
    st.sidebar.caption(f"🛡️ {st.session_state['u_title']}")
    
    if st.session_state['u_title'] in ['Müdür', 'Genel Müdür']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama & Takip", "📨 Giriş Onayları", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşler", "📜 İş Geçmişim", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    
    if st.sidebar.button("🔴 GÜVENLİ ÇIKIŞ", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    cp = st.session_state.page
    conn = get_db()

    # --- 4. SAYFA FONKSİYONLARI ---

    if cp == "🏠 Ana Sayfa":
        st.subheader(get_welcome_msg(st.session_state['u_name']))
        if st.session_state['u_role'] == 'admin':
            c1, c2, c3 = st.columns(3)
            c1.metric("✅ Tamamlanan", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("📌 Bekleyen", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            # Haftalık sayaç
            last_week = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
            c3.metric("📊 Haftalık Toplam", conn.execute("SELECT COUNT(*) FROM tasks WHERE updated_at >= ?", (last_week,)).fetchone()[0])

    elif cp == "➕ İş Atama & Takip":
        st.header("➕ Yeni İş Atama")
        # Müdür atama ekranında görünmez
        workers = pd.read_sql("SELECT email, name FROM users WHERE title != 'Müdür' AND role='worker'", conn)
        with st.form("task_form"):
            t_title = st.text_input("İş Başlığı / ID")
            t_worker = st.selectbox("Personel", workers['email'].tolist())
            t_city = st.selectbox("Şehir", TUM_SEHIRLER)
            t_desc = st.text_area("İş Açıklaması")
            if st.form_submit_button("Atama Yap"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city) VALUES (?,?,?,?,?)",
                             (t_worker, t_title, t_desc, 'Bekliyor', t_city))
                conn.commit(); st.success("İş atandı!"); st.rerun()

    elif cp == "⏳ Atanan İşler":
        st.header("⏳ Üzerimdeki İşler")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['u_email']}' AND status IN ('Bekliyor', 'Kabul Yapılabilir')", conn)
        if tasks.empty: st.info("Şu an bekleyen işiniz yok.")
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']} - {r['city']}"):
                res_box = st.selectbox("İşlem Durumu", ["Seçiniz", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"], key=f"res_{r['id']}")
                rep_box = st.text_area("Rapor ve Notlar", value=r['report'] if r['report'] else "", key=f"rep_{r['id']}")
                files = st.file_uploader("Fotoğraf/Dosya", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                if c1.button("💾 Kaydet (Taslak)", key=f"ts_{r['id']}"):
                    p_hex = json.dumps([f.read().hex() for f in files]) if files else r['photos_json']
                    conn.execute("UPDATE tasks SET report=?, photos_json=?, result_type=? WHERE id=?", (rep_box, p_hex, res_box, r['id']))
                    conn.commit(); st.toast("Taslak kaydedildi!")
                
                if c2.button("🚀 İşi Gönder", key=f"sg_{r['id']}", type="primary"):
                    p_hex = json.dumps([f.read().hex() for f in files]) if files else r['photos_json']
                    new_status = 'Giriş Mail Onayı Bekler' if res_box == 'Giriş Mail Onayı Bekler' else 'Onay Bekliyor'
                    conn.execute("UPDATE tasks SET status=?, result_type=?, report=?, photos_json=?, updated_at=? WHERE id=?", 
                                 (new_status, res_box, rep_box, p_hex, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                    conn.commit(); st.rerun()

    elif cp == "✅ Tamamlanan İşler":
        st.header("📑 İş Arşivi ve Filtreleme")
        f1, f2, f3 = st.columns(3)
        workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist()
        sel_worker = f1.selectbox("Çalışan", ["Hepsi"] + workers)
        sel_city = f2.selectbox("Şehir", ["Hepsi"] + TUM_SEHIRLER)
        
        status_opts = ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler"]
        if st.session_state['u_title'] == 'Müdür' or st.session_state['u_role'] == 'admin':
            status_opts += ["Türk Telekom Onayında", "Hak Edişi Alındı"]
        sel_status = f3.selectbox("Durum Filtresi", status_opts)
        
        query = "SELECT * FROM tasks WHERE status NOT IN ('Bekliyor')"
        if sel_worker != "Hepsi": query += f" AND assigned_to='{sel_worker}'"
        if sel_city != "Hepsi": query += f" AND city='{sel_city}'"
        
        if sel_status == "Tamamlanan İşler": query += " AND result_type='İŞ TAMAMLANDI'"
        elif sel_status == "Tamamlanamayan İşler": query += " AND result_type IN ('GİRİŞ YAPILAMADI', 'TEPKİLİ', 'MAL SAHİBİ GELMİYOR')"
        elif sel_status == "Türk Telekom Onayında": query += " AND status='Türk Telekom Onayında'"
        
        df = pd.read_sql(query, conn)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Excel Olarak İndir", to_excel(df), "Rapor.xlsx")

        for _, r in df.iterrows():
            with st.expander(f"🔍 Detay: {r['title']}"):
                if r['photos_json']:
                    st.download_button("📦 Fotoğrafları İndir (ZIP)", create_zip(r['photos_json']), f"fotos_{r['id']}.zip", key=f"z_{r['id']}")
                if st.session_state['u_title'] == 'Müdür':
                    if st.button("🔵 TT Onayına Al", key=f"tt_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Paneli")
        # filiz@deneme.com için özel görünüm
        h_df = pd.read_sql("SELECT * FROM tasks WHERE status='Türk Telekom Onayında' OR hakedis_durum='Hak Ediş Bekliyor'", conn)
        if h_df.empty: st.info("✅ Hak Ediş Bekleyen Atama Yok")
        else:
            st.dataframe(h_df)
            st.download_button("Excel Raporu Al", to_excel(h_df), "Hakedis_Rapor.xlsx")
            for _, r in h_df.iterrows():
                if st.button(f"Hak Ediş Alındı İşaretle ({r['title']})", key=f"h_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Edişi Alındı', hakedis_durum='Tamamlandı' WHERE id=?", (r['id'],))
                    conn.commit(); st.rerun()

    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Zimmet ve Envanter Yönetimi")
        f_inv = st.selectbox("Personel Filtrele", ["Hepsi"] + pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist())
        q_inv = "SELECT * FROM inventory"
        if f_inv != "Hepsi": q_inv += f" WHERE assigned_to='{f_inv}'"
        inv_df = pd.read_sql(q_inv, conn)
        st.table(inv_df)
        
        if st.session_state['u_role'] == 'admin':
            st.download_button("📥 Envanter Excel İndir", to_excel(inv_df), "Envanter.xlsx")
            
        with st.expander("➕ Yeni Zimmet/Düzenleme"):
            with st.form("inv_form"):
                i_name = st.text_input("Malzeme")
                i_user = st.selectbox("Personel", pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist())
                i_qty = st.number_input("Adet", 1)
                if st.form_submit_button("Zimmetle"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)",
                                 (i_name, i_user, i_qty, st.session_state['u_name']))
                    conn.commit(); st.rerun()

    elif cp == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        u_df = pd.read_sql("SELECT name, email, role, title, phone FROM users", conn)
        st.dataframe(u_df)
        
        c1, c2 = st.columns(2)
        with c1.expander("➕ Kullanıcı Ekle"):
            with st.form("add_user"):
                n_e = st.text_input("E-posta")
                n_n = st.text_input("Ad Soyad")
                n_t = st.text_input("Unvan")
                n_p = st.text_input("Şifre")
                n_r = st.selectbox("Rol", ["worker", "admin"])
                if st.form_submit_button("Ekle"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (n_e, h(n_p), n_r, n_n, n_t, ""))
                    conn.commit(); st.rerun()
        with c2.expander("❌ Kullanıcı Sil"):
            s_e = st.selectbox("Silinecek E-posta", u_df['email'].tolist())
            if st.button("Kullanıcıyı Kalıcı Olarak Sil"):
                conn.execute("DELETE FROM users WHERE email=?", (s_e,))
                conn.commit(); st.rerun()

    elif cp == "👤 Profilim":
        st.header("👤 Profil Bilgilerimi Güncelle")
        with st.form("profile_form"):
            new_mail = st.text_input("E-posta Adresi", value=st.session_state['u_email'])
            new_phone = st.text_input("Telefon Numarası", value=st.session_state['u_phone'])
            if st.form_submit_button("Güncellemeleri Kaydet"):
                conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (new_mail, new_phone, st.session_state['u_email']))
                conn.commit()
                st.session_state.u_email = new_mail
                st.session_state.u_phone = new_phone
                st.success("Bilgiler güncellendi!")

    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Onay Paneli")
        tasks = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        if tasks.empty: st.info("✅ Onay Bekleyen Atama Yok")
        else:
            for _, r in tasks.iterrows():
                with st.expander(f"Onay Bekleyen: {r['title']}"):
                    if st.button(f"✅ Kabul Yapılabilir Olarak Gönder ({r['id']})"):
                        conn.execute("UPDATE tasks SET status='Kabul Yapılabilir' WHERE id=?", (r['id'],))
                        conn.commit(); st.rerun()
