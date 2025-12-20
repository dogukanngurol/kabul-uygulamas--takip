import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI VE OTOMATİK KULLANICI KURULUMU ---
def init_db():
    conn = sqlite3.connect('saha_final_v25.db', check_same_thread=False)
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
    
    # Otomatik Kullanıcılar
    users = [
        ('admin@sirket.com', h('1234'), 'admin', 'Sistem Yöneticisi', 'Genel Müdür', '0555'),
        ('filiz@deneme.com', h('1234'), 'admin', 'Filiz Hanım', 'Müdür', '0555'),
        ('dogukan@deneme.com', h('1234'), 'worker', 'Doğukan Gürol', 'Saha Çalışanı', '0555'),
        ('doguscan@deneme.com', h('1234'), 'worker', 'Doğuşcan Gürol', 'Saha Çalışanı', '0555'),
        ('cuneyt@deneme.com', h('1234'), 'worker', 'Cüneyt Bey', 'Saha Çalışanı', '0555')
    ]
    c.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", users)
    conn.commit()
    return conn

conn = init_db()

# --- 2. YARDIMCI FONKSİYONLAR ---
def get_welcome():
    h = datetime.now().hour
    u = st.session_state['user_name']
    if 0 <= h < 8: m = "İyi Geceler"
    elif 8 <= h < 12: m = "Günaydın"
    elif 12 <= h < 18: m = "İyi Günler"
    else: m = "İyi Akşamlar"
    return f"✨ {m} **{u}**, İyi Çalışmalar!"

def create_zip(photos_json):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        photos = json.loads(photos_json)
        for i, p_hex in enumerate(photos):
            z.writestr(f"foto_{i+1}.jpg", bytes.fromhex(p_hex))
    return buf.getvalue()

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Gaziantep", "Konya"]

# --- 3. ANA ARAYÜZ ---
st.set_page_config(page_title="Saha Operasyon v25", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Operasyon Giriş")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            u = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4], 'user_phone':u[5], 'page':"🏠 Ana Sayfa"})
                st.rerun()
else:
    # --- YAN MENÜ ---
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    if st.sidebar.button("🏠 Ana Sayfa", use_container_width=True): st.session_state.page = "🏠 Ana Sayfa"
    
    if st.session_state['role'] == 'admin':
        pages = ["➕ İş Atama", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcılar"]
    else:
        pages = ["⏳ Atanan İşler", "📜 İş Geçmişim", "👤 Profilim"]
    
    for p in pages:
        if st.sidebar.button(p, use_container_width=True): st.session_state.page = p
    
    if st.sidebar.button("🔴 Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    cp = st.session_state.page

    # --- SAYFA: ANA SAYFA ---
    if cp == "🏠 Ana Sayfa":
        st.info(get_welcome())
        # Haftalık Sayaç Mantığı
        start_of_week = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%d/%m/%Y')
        
        q_week = f"SELECT COUNT(*) FROM tasks WHERE status IN ('Tamamlandı', 'Hak Edişi Alındı')"
        total_weekly = conn.execute(q_week).fetchone()[0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 Bekleyen İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
        c2.metric("✅ Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Tamamlandı'").fetchone()[0])
        c3.metric("📊 Bu Haftaki Toplam İş", total_weekly, help=f"{start_of_week} tarihinden itibaren")

    # --- SAYFA: İŞ ATAMA ---
    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        workers = pd.read_sql("SELECT email, name FROM users WHERE role='worker'", conn)
        with st.form("task_atama"):
            t = st.text_input("İş Başlığı")
            w = st.selectbox("Personel", workers['email'].tolist())
            city = st.selectbox("Şehir", SEHIRLER)
            desc = st.text_area("Açıklama")
            if st.form_submit_button("Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city, hakedis_durum) VALUES (?,?,?,?,?,?)", 
                             (w, t, desc, 'Bekliyor', city, 'Süreçte'))
                conn.commit(); st.success("İş Atandı!")

    # --- SAYFA: TAMAMLANAN İŞLER ---
    elif cp == "✅ Tamamlanan İşler":
        st.header("📑 İş Takip ve Filtreleme")
        f1, f2, f3, f4 = st.columns(4)
        worker_list = ["Hepsi"] + pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist()
        sel_worker = f1.selectbox("Çalışan", worker_list)
        sel_city = f2.selectbox("Şehir", ["Hepsi"] + SEHIRLER)
        # Özel Durum Filtresi
        sel_type = f3.selectbox("İş Sonucu", ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler", "Türk Telekom Onayında", "Hak Edişi Alındı"])
        
        query = "SELECT * FROM tasks WHERE status != 'Bekliyor'"
        if sel_worker != "Hepsi": query += f" AND assigned_to='{sel_worker}'"
        if sel_city != "Hepsi": query += f" AND city='{sel_city}'"
        
        if sel_type == "Tamamlanan İşler": query += " AND result_type='İŞ TAMAMLANDI'"
        elif sel_type == "Tamamlanamayan İşler": query += " AND result_type IN ('GİRİŞ YAPILAMADI', 'TEPKİLİ', 'MAL SAHİBİ GELMİYOR')"
        elif sel_type == "Türk Telekom Onayında": query += " AND status='Türk Telekom Onayında'"
        elif sel_type == "Hak Edişi Alındı": query += " AND status='Hak Edişi Alındı'"

        df = pd.read_sql(query, conn)
        st.dataframe(df[['id', 'title', 'assigned_to', 'city', 'result_type', 'status']], use_container_width=True)

        for _, r in df.iterrows():
            with st.expander(f"🔍 Detay: {r['title']} ({r['result_type']})"):
                if r['photos_json']:
                    st.download_button("📂 Fotoğrafları İndir (ZIP)", data=create_zip(r['photos_json']), file_name=f"fotos_{r['id']}.zip", key=f"zip_{r['id']}")
                
                if st.session_state['user_title'] == 'Müdür' or st.session_state['user_email'] == 'admin@sirket.com':
                    if r['status'] == 'Onay Bekliyor':
                        if st.button("Türk Telekom Onayına Al", key=f"tt_{r['id']}"):
                            conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],))
                            conn.commit(); st.rerun()
                    if r['status'] == 'Türk Telekom Onayında':
                        if st.button("Filiz Hanım'a (Hak Edişe) Gönder", key=f"flz_{r['id']}"):
                            conn.execute("UPDATE tasks SET status='Tamamlandı', hakedis_durum='Hak Ediş Bekliyor' WHERE id=?", (r['id'],))
                            conn.commit(); st.rerun()

    # --- SAYFA: HAK EDİŞ ---
    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Yönetimi")
        df_h = pd.read_sql("SELECT * FROM tasks WHERE hakedis_durum='Hak Ediş Bekliyor'", conn)
        for _, r in df_h.iterrows():
            with st.expander(f"İş: {r['title']} - {r['assigned_to']}"):
                if st.button("Hak Ediş Alındı", key=f"hk_{r['id']}"):
                    conn.execute("UPDATE tasks SET hakedis_durum='Hak Edişi Alındı', status='Hak Edişi Alındı' WHERE id=?", (r['id'],))
                    conn.commit(); st.rerun()

    # --- SAYFA: ZİMMET ---
    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Zimmet Yönetimi")
        # Filtreleme
        f_z = st.selectbox("Personel Filtrele", ["Hepsi"] + pd.read_sql("SELECT email FROM users", conn)['email'].tolist())
        q_z = "SELECT * FROM inventory"
        if f_z != "Hepsi": q_z += f" WHERE assigned_to='{f_z}'"
        df_z = pd.read_sql(q_z, conn)
        st.dataframe(df_z, use_container_width=True)
        
        col_ex, col_add = st.columns(2)
        # Excel İndir
        buffer = io.BytesIO()
        df_z.to_excel(buffer, index=False)
        col_ex.download_button("📊 Excel Olarak İndir", data=buffer.getvalue(), file_name="zimmet_listesi.xlsx")
        
        with col_add.expander("➕ Yeni Zimmet / Düzenle"):
            with st.form("z_form"):
                it, target, qty = st.text_input("Malzeme"), st.selectbox("Çalışan", pd.read_sql("SELECT email FROM users", conn)['email'].tolist()), st.number_input("Adet", 1)
                if st.form_submit_button("Kaydet"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (it, target, qty, st.session_state['user_name']))
                    conn.commit(); st.rerun()

    # --- SAYFA: KULLANICILAR (EKLE/SİL) ---
    elif cp == "👥 Kullanıcılar":
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("new_u"):
                ne, nn, nt = st.text_input("E-mail"), st.text_input("Ad Soyad"), st.selectbox("Unvan", ["Saha Çalışanı", "Müdür", "Teknisyen"])
                np, nr = st.text_input("Şifre"), st.selectbox("Yetki", ["worker", "admin"])
                if st.form_submit_button("Ekle"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (ne, hashlib.sha256(np.encode()).hexdigest(), nr, nn, nt, ""))
                    conn.commit(); st.rerun()
        
        u_df = pd.read_sql("SELECT email, name, title, role FROM users", conn)
        for _, row in u_df.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{row['name']}** ({row['email']}) - {row['title']}")
            if c2.button("Sil", key=f"del_{row['email']}"):
                conn.execute("DELETE FROM users WHERE email=?", (row['email'],))
                conn.commit(); st.rerun()

    # --- SAYFA: SAHA PERSONELİ - ATANAN İŞLER ---
    elif cp == "⏳ Atanan İşler":
        st.header("⏳ Görevlerim")
        my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        for _, r in my_tasks.iterrows():
            with st.expander(f"📋 {r['title']} - {r['city']}"):
                res = st.selectbox("İş Sonucu", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"], key=f"res_{r['id']}")
                rep = st.text_area("Rapor", value=r['report'] if r['report'] else "", key=f"rep_{r['id']}")
                fots = st.file_uploader("Fotoğraflar", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                if c1.button("💾 Taslak Kaydet", key=f"save_{r['id']}"):
                    p_json = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET report=?, photos_json=?, result_type=? WHERE id=?", (rep, p_json, res, r['id']))
                    conn.commit(); st.toast("Taslak Kaydedildi!")
                
                if c2.button("🚀 İşi Gönder", key=f"send_{r['id']}"):
                    p_json = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET status='Onay Bekliyor', report=?, photos_json=?, result_type=?, updated_at=? WHERE id=?", 
                                 (rep, p_json, res, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                    conn.commit(); st.rerun()

    # --- SAYFA: PROFİL GÜNCELLEME ---
    elif cp == "👤 Profilim":
        st.header("👤 Bilgilerimi Güncelle")
        with st.form("profile_form"):
            new_mail = st.text_input("E-posta", value=st.session_state['user_email'])
            new_phone = st.text_input("Telefon", value=st.session_state['user_phone'])
            if st.form_submit_button("Güncellemeleri Kaydet"):
                conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (new_mail, new_phone, st.session_state['user_email']))
                conn.commit()
                st.success("Bilgiler güncellendi! Lütfen yeni mail ile tekrar giriş yapın.")
