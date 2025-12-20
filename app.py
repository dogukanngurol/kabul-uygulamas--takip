import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI VE KURULUM ---
def init_db():
    conn = sqlite3.connect('saha_operasyon_v29.db', check_same_thread=False)
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
    
    # Otomatik Kullanıcı Tanımlamaları
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
        df.to_excel(writer, index=False, sheet_name='Saha_Rapor')
    return output.getvalue()

def create_zip(photos_json):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        photos = json.loads(photos_json)
        for i, p_hex in enumerate(photos):
            z.writestr(f"saha_foto_{i+1}.jpg", bytes.fromhex(p_hex))
    return buf.getvalue()

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Erzurum", "Gaziantep", "Konya", "Samsun", "Trabzon"]

# --- 3. ANA UYGULAMA MANTIĞI ---
st.set_page_config(page_title="Saha Operasyon v29", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Şirket Operasyon Paneli")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş Yap"):
            u = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4], 'user_phone':u[5], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı bilgiler.")
else:
    # --- YAN MENÜ ---
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.caption(f"🏷️ {st.session_state['user_title']}")
    
    if st.session_state['role'] == 'admin':
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📨 Giriş Onayları", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcılar"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşler", "📜 İş Geçmişim", "🎒 Zimmetim", "👤 Profilim"]

    for item in menu:
        if st.sidebar.button(item, use_container_width=True): st.session_state.page = item
    
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    cp = st.session_state.page

    # --- SAYFA: ANA SAYFA ---
    if cp == "🏠 Ana Sayfa":
        st.info(get_welcome_msg(st.session_state['user_name']))
        
        # Haftalık Sayaç Hesaplama
        now = datetime.now()
        start_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 Bekleyen İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
        c2.metric("✅ Tamamlananlar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Hak Edişi Alındı'").fetchone()[0])
        
        # Basit Haftalık Sayaç
        weekly_q = conn.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('Tamamlandı', 'Hak Edişi Alındı')").fetchone()[0]
        c3.metric("📊 Bu Haftaki Toplam İş", weekly_q)

    # --- SAYFA: İŞ ATAMA ---
    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        # Müdür (Filiz Hanım) hariç çalışanları listele
        workers = pd.read_sql("SELECT email, name FROM users WHERE role='worker'", conn)
        with st.form("atama_form"):
            t = st.text_input("İş Başlığı")
            w = st.selectbox("Saha Personeli", workers['email'].tolist())
            city = st.selectbox("Şehir", SEHIRLER)
            desc = st.text_area("İş Açıklaması")
            if st.form_submit_button("Görevi Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city, hakedis_durum) VALUES (?,?,?,?,?,?)", 
                             (w, t, desc, 'Bekliyor', city, 'Süreçte'))
                conn.commit(); st.success("İş başarıyla atandı.")

    # --- SAYFA: SAHA PERSONELİ - ATANAN İŞLER (TASLAK VE ONAYLI) ---
    elif cp == "⏳ Atanan İşler":
        st.header("⏳ Üstüme Atanan İşler")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status IN ('Bekliyor', 'Kabul Yapılabilir')", conn)
        
        if tasks.empty: st.info("Şu an bekleyen bir göreviniz yok.")
        
        for _, r in tasks.iterrows():
            label = "✅ KABUL YAPILABİLİR" if r['status'] == 'Kabul Yapılabilir' else "⏳ BEKLİYOR"
            with st.expander(f"📋 {r['title']} - {r['city']} [{label}]"):
                st.write(f"**Açıklama:** {r['description']}")
                st.divider()
                
                # Seçenek Kutusu
                opts = ["Seçiniz", "Giriş Mail Onayı Bekler", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
                res = st.selectbox("İşlem Sonucu", opts, key=f"res_{r['id']}")
                
                # Rapor Notları
                rep = st.text_area("İşte Yapılan Notlar", value=r['report'] if r['report'] else "", key=f"rep_{r['id']}")
                
                # Dosya/Fotoğraf Yükleme
                fots = st.file_uploader("Fotoğraf/Dosya Ekle", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                # TASLAK KAYDET
                if c1.button("💾 Taslağı Kaydet", key=f"s_{r['id']}", use_container_width=True):
                    p_hex = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET report=?, photos_json=?, result_type=? WHERE id=?", (rep, p_hex, res, r['id']))
                    conn.commit(); st.toast("Taslak kaydedildi!")

                # GÖNDER
                if c2.button("🚀 İşi Gönder", key=f"b_{r['id']}", use_container_width=True, type="primary"):
                    if res == "Seçiniz": st.error("Sonuç seçiniz!")
                    elif res == "Giriş Mail Onayı Bekler":
                        conn.execute("UPDATE tasks SET status='Giriş Mail Onayı Bekler', report=?, updated_at=? WHERE id=?", 
                                     (rep, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                        conn.commit(); st.warning("Müdür onayı bekleniyor."); st.rerun()
                    else:
                        p_hex = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                        conn.execute("UPDATE tasks SET status='Onay Bekliyor', result_type=?, report=?, photos_json=?, updated_at=? WHERE id=?", 
                                     (res, rep, p_hex, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                        conn.commit(); st.success("İş gönderildi!"); st.rerun()

    # --- SAYFA: GİRİŞ ONAYLARI (MÜDÜR İÇİN) ---
    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Mail Onayı Bekleyen İşler")
        onaylar = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        for _, r in onaylar.iterrows():
            with st.expander(f"📍 {r['title']} - {r['assigned_to']}"):
                st.write(f"Not: {r['report']}")
                if st.button("Kabul Yapılabilir Olarak Geri Gönder", key=f"ok_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Kabul Yapılabilir' WHERE id=?", (r['id'],))
                    conn.commit(); st.success("İş çalışana geri gönderildi."); st.rerun()

    # --- SAYFA: TAMAMLANAN İŞLER (FİLTRE + EXCEL + RAR) ---
    elif cp == "✅ Tamamlanan İşler":
        st.header("📑 İş Takip ve Arşiv")
        f1, f2, f3, f4 = st.columns(4)
        f_user = f1.selectbox("Çalışan", ["Hepsi"] + pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist())
        f_city = f2.selectbox("Şehir", ["Hepsi"] + SEHIRLER)
        f_type = f3.selectbox("Filtre Tipi", ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler", "Türk Telekom Onayında", "Hak Edişi Alındı"])
        
        q = "SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Mail Onayı Bekler', 'Kabul Yapılabilir')"
        if f_user != "Hepsi": q += f" AND assigned_to='{f_user}'"
        if f_city != "Hepsi": q += f" AND city='{f_city}'"
        
        if f_type == "Tamamlanan İşler": q += " AND result_type='İŞ TAMAMLANDI'"
        elif f_type == "Tamamlanamayan İşler": q += " AND result_type IN ('GİRİŞ YAPILAMADI', 'TEPKİLİ', 'MAL SAHİBİ GELMİYOR')"
        elif f_type == "Türk Telekom Onayında": q += " AND status='Türk Telekom Onayında'"
        elif f_type == "Hak Edişi Alındı": q += " AND status='Hak Edişi Alındı'"

        df = pd.read_sql(q, conn)
        st.dataframe(df[['id', 'title', 'assigned_to', 'city', 'result_type', 'status', 'updated_at']], use_container_width=True)
        
        if not df.empty:
            st.download_button("📊 Filtrelenmiş Excel İndir", data=to_excel(df), file_name="Saha_Rapor.xlsx")

        for _, r in df.iterrows():
            with st.expander(f"🔍 Detay: {r['title']} - {r['result_type']}"):
                st.write(f"**Rapor Notu:** {r['report']}")
                if r['photos_json']:
                    st.download_button("📂 Fotoğrafları İndir (ZIP)", data=create_zip(r['photos_json']), file_name=f"fotolar_{r['id']}.zip", key=f"z_{r['id']}")
                
                if st.session_state['user_title'] == 'Müdür':
                    if r['status'] == 'Onay Bekliyor':
                        if st.button("Türk Telekom Onayına Al", key=f"tt_{r['id']}"):
                            conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],))
                            conn.commit(); st.rerun()
                    if r['status'] == 'Türk Telekom Onayında':
                        if st.button("Onaylandı - Filiz Hanım'a (Hak Edişe) Gönder", key=f"flz_{r['id']}"):
                            conn.execute("UPDATE tasks SET status='Tamamlandı', hakedis_durum='Hak Ediş Bekliyor' WHERE id=?", (r['id'],))
                            conn.commit(); st.rerun()

    # --- SAYFA: HAK EDİŞ (FİLİZ HANIM) ---
    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Yönetimi")
        tab1, tab2 = st.tabs(["Bekleyenler", "Tamamlananlar"])
        with tab1:
            h_df = pd.read_sql("SELECT * FROM tasks WHERE hakedis_durum='Hak Ediş Bekliyor'", conn)
            st.dataframe(h_df[['id', 'title', 'assigned_to', 'updated_at']], use_container_width=True)
            for _, r in h_df.iterrows():
                if st.button(f"Hak Ediş Alındı İşaretle: {r['title']}", key=f"h_{r['id']}"):
                    conn.execute("UPDATE tasks SET hakedis_durum='Hak Edişi Alındı', status='Hak Edişi Alındı' WHERE id=?", (r['id'],))
                    conn.commit(); st.rerun()
        with tab2:
            done_h = pd.read_sql("SELECT * FROM tasks WHERE hakedis_durum='Hak Edişi Alındı'", conn)
            st.dataframe(done_h, use_container_width=True)
            if not done_h.empty:
                st.download_button("📈 Hak Ediş Excel İndir", data=to_excel(done_h), file_name="Hakedis_Rapor.xlsx")

    # --- SAYFA: KULLANICILAR (EKLE/SİL) ---
    elif cp == "👥 Kullanıcılar":
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı"):
            with st.form("u_add"):
                ne, nn, nt = st.text_input("E-mail"), st.text_input("Ad Soyad"), st.selectbox("Unvan", ["Saha Çalışanı", "Müdür", "Teknisyen"])
                np, nr = st.text_input("Şifre"), st.selectbox("Yetki", ["worker", "admin"])
                if st.form_submit_button("Ekle"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?)", (ne, hashlib.sha256(np.encode()).hexdigest(), nr, nn, nt, ""))
                    conn.commit(); st.rerun()
        
        udf = pd.read_sql("SELECT email, name, title, role FROM users", conn)
        for _, row in udf.iterrows():
            c1, c2 = st.columns([4,1])
            c1.write(f"**{row['name']}** - {row['title']} ({row['email']})")
            if c2.button("❌ SİL", key=f"del_{row['email']}"):
                conn.execute("DELETE FROM users WHERE email=?", (row['email'],))
                conn.commit(); st.rerun()

    # --- SAYFA: PROFİL (TELEFON/MAİL GÜNCELLEME) ---
    elif cp == "👤 Profilim":
        st.header("👤 Profil Bilgilerimi Güncelle")
        with st.form("prof"):
            nm = st.text_input("Yeni E-posta", value=st.session_state['user_email'])
            np = st.text_input("Yeni Telefon", value=st.session_state['user_phone'])
            if st.form_submit_button("Güncellemeleri Kaydet"):
                conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (nm, np, st.session_state['user_email']))
                conn.commit(); st.success("Bilgiler güncellendi. Yeniden giriş yapmanız gerekebilir.")
