import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI ---
def init_db():
    conn = sqlite3.connect('saha_final_v26.db', check_same_thread=False)
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

# --- 2. FONKSİYONLAR ---
def get_welcome():
    h = datetime.now().hour
    u = st.session_state['user_name']
    if 0 <= h < 8: m = "İyi Geceler"
    elif 8 <= h < 12: m = "Günaydın"
    elif 12 <= h < 18: m = "İyi Günler"
    else: m = "İyi Akşamlar"
    return f"✨ {m} **{u}**, İyi Çalışmalar!"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Gaziantep", "Konya"]

# --- 3. ANA ARAYÜZ ---
st.set_page_config(page_title="Saha Operasyon v26", layout="wide")

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
        c1, c2, c3 = st.columns(3)
        c1.metric("📌 Bekleyen İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
        c2.metric("✅ Onayda/Biten", conn.execute("SELECT COUNT(*) FROM tasks WHERE status!='Bekliyor'").fetchone()[0])
        # Haftalık sayaç
        week_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('Tamamlandı', 'Hak Edişi Alındı')").fetchone()[0]
        c3.metric("📊 Haftalık Başarı", week_count)

    # --- SAYFA: TAMAMLANAN İŞLER (FİLTRELİ EXCEL DAHİL) ---
    elif cp == "✅ Tamamlanan İşler":
        st.header("📑 İş Takip Arşivi")
        
        with st.container():
            f1, f2, f3 = st.columns(3)
            sel_worker = f1.selectbox("Çalışan", ["Hepsi"] + pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist())
            sel_city = f2.selectbox("Şehir", ["Hepsi"] + SEHIRLER)
            sel_type = f3.selectbox("İş Sonucu", ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler", "Türk Telekom Onayında", "Hak Edişi Alındı"])
            
            query = "SELECT id, title, assigned_to, city, result_type, status, updated_at FROM tasks WHERE status != 'Bekliyor'"
            if sel_worker != "Hepsi": query += f" AND assigned_to='{sel_worker}'"
            if sel_city != "Hepsi": query += f" AND city='{sel_city}'"
            if sel_type == "Tamamlanan İşler": query += " AND result_type='İŞ TAMAMLANDI'"
            elif sel_type == "Tamamlanamayan İşler": query += " AND result_type IN ('GİRİŞ YAPILAMADI', 'TEPKİLİ', 'MAL SAHİBİ GELMİYOR')"
            elif sel_type == "Türk Telekom Onayında": query += " AND status='Türk Telekom Onayında'"
            elif sel_type == "Hak Edişi Alındı": query += " AND status='Hak Edişi Alındı'"

            df_filtered = pd.read_sql(query, conn)
            st.dataframe(df_filtered, use_container_width=True)
            
            # --- FİLTREYE GÖRE EXCEL İNDİR ---
            if not df_filtered.empty:
                st.download_button("📊 Seçili Filtreleri Excel Olarak İndir", data=to_excel(df_filtered), file_name=f"Saha_Rapor_{datetime.now().strftime('%d_%m')}.xlsx")

    # --- SAYFA: HAK EDİŞ (ONAYLANANLARIN GÖRÜNMESİ VE EXCEL) ---
    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Yönetimi")
        
        tab1, tab2 = st.tabs(["⏳ Bekleyen Hak Edişler", "✅ Alınan Hak Edişler (Arşiv)"])
        
        with tab1:
            df_bekleyen = pd.read_sql("SELECT id, title, assigned_to, city, result_type, updated_at FROM tasks WHERE hakedis_durum='Hak Ediş Bekliyor'", conn)
            if df_bekleyen.empty:
                st.info("Bekleyen hak ediş bulunmuyor.")
            else:
                st.dataframe(df_bekleyen, use_container_width=True)
                for _, r in df_bekleyen.iterrows():
                    if st.button(f"Onayla: {r['title']}", key=f"h_{r['id']}"):
                        conn.execute("UPDATE tasks SET hakedis_durum='Hak Edişi Alındı', status='Hak Edişi Alındı' WHERE id=?", (r['id'],))
                        conn.commit(); st.rerun()

        with tab2:
            df_alinan = pd.read_sql("SELECT id, title, assigned_to, city, result_type, updated_at FROM tasks WHERE hakedis_durum='Hak Edişi Alındı'", conn)
            st.success(f"Toplam {len(df_alinan)} adet hak ediş başarıyla tamamlandı.")
            st.dataframe(df_alinan, use_container_width=True)
            if not df_alinan.empty:
                st.download_button("📈 Hak Ediş Arşivini Excel İndir", data=to_excel(df_alinan), file_name="Hakedis_Arsiv.xlsx")

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

    # --- DİĞER SAYFALAR (Zimmet, İş Atama vb. v25 ile aynı yapıda devam eder) ---
    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        workers = pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)
        with st.form("task_atama"):
            t, w, city = st.text_input("İş Başlığı"), st.selectbox("Personel", workers['email'].tolist()), st.selectbox("Şehir", SEHIRLER)
            if st.form_submit_button("Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, status, city, hakedis_durum) VALUES (?,?,?,?,?)", (w, t, 'Bekliyor', city, 'Süreçte'))
                conn.commit(); st.success("İş Atandı!")

    elif cp == "⏳ Atanan İşler":
        st.header("⏳ Görevlerim")
        my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        for _, r in my_tasks.iterrows():
            with st.expander(f"📋 {r['title']}"):
                res = st.selectbox("İş Sonucu", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"], key=f"res_{r['id']}")
                if st.button("İşi Gönder", key=f"send_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Onay Bekliyor', result_type=?, updated_at=? WHERE id=?", (res, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                    conn.commit(); st.rerun()
