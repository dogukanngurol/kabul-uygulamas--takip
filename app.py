import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- 1. SİSTEM AYARLARI VE HATA KORUMASI ---
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

UPLOAD_DIR = "saha_dosyalari"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir", "Konya", "Samsun"] # 81 il eklenebilir

# --- 2. VERİTABANI VE OTOMATİK TABLO OLUŞTURMA ---
def get_db():
    return sqlite3.connect('saha_v57.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Kullanıcılar
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    # İşler (Hata veren tüm kolonlar eklendi)
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        assigned_to TEXT, title TEXT, description TEXT, status TEXT, 
        report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, 
        result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    # Envanter
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Admin', '0555'),
        ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '0555'),
        ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. EXCEL MOTORU VE FİLTRELEME ALTYAPISI ---
def excel_downloader(df, filename):
    if df is None or df.empty:
        st.warning("⚠️ Gösterilecek Veri Bulunmamaktadır")
        return
    
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Rapor')
        
        st.download_button(
            label="📥 Excel Raporu İndir",
            data=output.getvalue(),
            file_name=f"{filename}_{datetime.now().strftime('%d%m%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except:
        st.error("Excel oluşturulurken bir hata oluştu.")

def universal_filter(df, key):
    st.write("### 🔍 Filtreleme Paneli")
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_tarih = st.date_input("Tarih", [], key=f"t_{key}")
    with c2: f_pers = st.selectbox("Personel", ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"], key=f"p_{key}")
    with c3: f_sehir = st.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"s_{key}")
    with c4: 
        d_opts = ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
        if st.session_state.u_role in ['Admin', 'Müdür']:
            d_opts += ["Türk Telekom Onayında", "Hak Ediş Bekleniyor", "Hak Ediş Alındı"]
        f_durum = st.selectbox("Durum", d_opts, key=f"d_{key}")
    
    filtered = df.copy()
    if not filtered.empty:
        if f_pers != "Hepsi": filtered = filtered[filtered['assigned_to'] == f_pers]
        if f_sehir != "Hepsi": filtered = filtered[filtered['city'] == f_sehir]
        if f_durum != "Hepsi":
            if f_durum in ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]:
                filtered = filtered[filtered['result_type'] == f_durum]
            else:
                filtered = filtered[filtered['status'] == f_durum]
    
    excel_downloader(filtered, key)
    return filtered

# --- 4. ANA DÖNGÜ VE EKRANLAR ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🛡️ Saha Operasyon Sistemi")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı Giriş Bilgileri")
else:
    # Sidebar ve Karşılama
    hr = datetime.now().hour
    msg = "Günaydın" if hr < 12 else "İyi Günler" if hr < 18 else "İyi Akşamlar"
    st.sidebar.markdown(f"#### {msg} {st.session_state.u_name} \n **İyi Çalışmalar**")
    
    menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👤 Profilim"]
    if st.session_state.u_role not in ['Admin', 'Müdür']:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "🎒 Zimmetim", "👤 Profilim"]

    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    if st.sidebar.button("🔴 ÇIKIŞ"): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- EKRAN MANTIKLARI ---
    if cp == "🏠 Ana Sayfa":
        st.header("📊 Genel Durum")
        c1, c2 = st.columns(2)
        if st.session_state.u_role in ['Admin', 'Müdür']:
            c1.metric("Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Hak Ediş Alındı'").fetchone()[0])
            c2.metric("Bekleyen Atamalar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
        else:
            c1.metric("Tamamladığım İşler", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status='Hak Ediş Alındı'").fetchone()[0])

    elif cp == "📋 Atanan İşler":
        st.header("📋 Atanan İşler Takip Paneli")
        df_atanan = pd.read_sql("SELECT assigned_to, title, city, status, created_at FROM tasks WHERE status IN ('Bekliyor', 'Ret Edildi')", conn)
        res = universal_filter(df_atanan, "atanan")
        if not res.empty: st.dataframe(res, use_container_width=True)

    elif cp == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Arşivi")
        df_tamam = pd.read_sql("SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Ret Edildi')", conn)
        res = universal_filter(df_tamam, "arsiv")
        if not res.empty:
            for _, r in res.iterrows():
                with st.expander(f"Detay: {r['title']}"):
                    if r['photos_json']:
                        st.write("📸 Fotoğraflar yüklü.")
                    c1, c2 = st.columns(2)
                    if c1.button("📡 TT Onayına Gönder", key=f"tt_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                    if c2.button("❌ Ret Et", key=f"rt_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Ret Edildi' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        p_list = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist()
        with st.form("atama"):
            t = st.text_input("Başlık"); p = st.selectbox("Personel", p_list); s = st.selectbox("Şehir", ILLER)
            if st.form_submit_button("Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, status, city, created_at) VALUES (?,?,?,?,?)", (p, t, 'Bekliyor', s, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.success("İş Atandı")

    elif cp == "⏳ Atanan İşlerim":
        st.header("⏳ Atanan İşlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor', 'Ret Edildi')", conn)
        if tasks.empty: st.info("Bekleyen işiniz yok.")
        for _, r in tasks.iterrows():
            with st.expander(f"İş: {r['title']}"):
                res = st.selectbox("Durum", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"], key=f"res_{r['id']}")
                if st.button("🚀 İşi Tamamla ve Gönder", key=f"send_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Onay Bekliyor', result_type=?, updated_at=? WHERE id=?", (res, datetime.now().strftime("%Y-%m-%d"), r['id']))
                    conn.commit(); st.rerun()
