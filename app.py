import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- 1. SİSTEM AYARLARI ---
COMPANY_NAME = "Anatolia Bilişim"
ILLER = ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir", "Konya", "Samsun"] # 81 ile tamamlanabilir

def get_db():
    return sqlite3.connect('anatolia_v62.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    # Tanımlı Kullanıcılar
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Admin Kullanıcı', '0555'),
        ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '0555'),
        ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', '0555'),
        ('doguscan@deneme.com', pw, 'Saha Personeli', 'Doğuşcan Gürol', '0555'),
        ('cuneyt@deneme.com', pw, 'Saha Personeli', 'Cüneyt Bey', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 2. YARDIMCI FONKSİYONLAR ---
def excel_export(df, key):
    if df is None or df.empty:
        st.warning("⚠️ Gösterilecek Tamamlanmış İş Bulunmamaktadır")
        return
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    st.download_button(label="📥 Excel Raporu Al", data=output.getvalue(), file_name=f"{key}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def universal_filter(df, key_prefix):
    st.write("### 🔍 Filtreleme Paneli")
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_tarih = st.date_input("Tarih Aralığı", [], key=f"t_{key_prefix}")
    with c2: f_pers = st.selectbox("Personel", ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"], key=f"p_{key_prefix}")
    with c3: f_sehir = st.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"s_{key_prefix}")
    
    d_opts = ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
    if st.session_state.u_role in ['Admin', 'Yönetici', 'Müdür']:
        d_opts += ["Türk Telekom Onayında", "Hak Ediş Bekleniyor", "Hak Ediş Alındı"]
    with c4: f_durum = st.selectbox("Durum", d_opts, key=f"d_{key_prefix}")
    
    res_df = df.copy()
    if not res_df.empty:
        if f_pers != "Hepsi": res_df = res_df[res_df['assigned_to'] == f_pers]
        if f_sehir != "Hepsi": res_df = res_df[res_df['city'] == f_sehir]
        if f_durum != "Hepsi":
            if f_durum in ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]:
                res_df = res_df[res_df['result_type'] == f_durum]
            else: res_df = res_df[res_df['status'] == f_durum]
    
    excel_export(res_df, key_prefix)
    return res_df

# --- 3. ANA DÖNGÜ VE YETKİLER ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title(f"🏢 {COMPANY_NAME} Sistem Girişi")
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
    # Sidebar Tasarımı (Madde 9)
    st.sidebar.markdown(f"## 🏢 {COMPANY_NAME}")
    st.sidebar.markdown(f"👤 **{st.session_state.u_name}**\n⭐ *{st.session_state.u_role}*")
    st.sidebar.divider()

    # Rol Bazlı Ekran Listesi (Madde 2, 3, 4, 5)
    role = st.session_state.u_role
    if role == 'Admin':
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi", "👤 Profilim"]
    elif role == 'Yönetici':
        menu = ["🏠 Ana Sayfa", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👤 Profilim"]
    elif role == 'Müdür':
        menu = ["🏠 Ana Sayfa", "📡 TT Onay Bekleyenler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👤 Profilim"]
    else: # Saha Personeli
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]

    for m in menu:
        is_active = "primary" if st.session_state.page == m else "secondary"
        if st.sidebar.button(m, use_container_width=True, type=is_active):
            st.session_state.page = m; st.rerun()
    
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True):
        st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- 🏠 ANA SAYFA (Madde 8) ---
    if cp == "🏠 Ana Sayfa":
        hr = datetime.now().hour
        greet = "Günaydın" if 8<=hr<12 else "İyi Günler" if 12<=hr<18 else "İyi Akşamlar" if 18<=hr<24 else "İyi Geceler"
        st.header(f"📊 {greet}, {st.session_state.u_name}")
        
        if role in ['Admin', 'Yönetici']:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Bekleyen Atamalar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            c3.metric("Haftalık İş", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", ((datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d"),)).fetchone()[0])
        else:
            c1, c2 = st.columns(2)
            c1.metric("Tamamladığım İşler", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Atanan İşlerim", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status='Bekliyor'").fetchone()[0])

    # --- ➕ İŞ ATAMA (Madde 1 & 2) ---
    elif cp == "➕ İş Atama" and role == 'Admin':
        st.header("➕ Yeni İş Atama")
        pers_df = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)
        with st.form("atama"):
            t = st.text_input("Başlık"); p = st.selectbox("Personel", pers_df['email'].tolist()); s = st.selectbox("Şehir", ILLER)
            d = st.text_area("Açıklama")
            if st.form_submit_button("İşi Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city, created_at) VALUES (?,?,?,?,?,?)", (p, t, d, 'Bekliyor', s, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.success("İş Atandı")

    # --- ⏳ SAHA PERSONELİ EKRANI (Madde 5) ---
    elif cp == "⏳ Atanan İşlerim":
        st.header("⏳ Üzerimdeki İşler")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor', 'Ret Edildi')", conn)
        if tasks.empty: st.info("Gösterilecek Atanmış İş Bulunmamaktadır")
        else:
            for _, r in tasks.iterrows():
                with st.expander(f"📌 {r['title']} ({r['city']})"):
                    st.write(f"Açıklama: {r['description']}")
                    res = st.selectbox("Durum", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"], key=f"res_{r['id']}")
                    report = st.text_area("Rapor Notu", value=r['report'] if r['report'] else "", key=f"not_{r['id']}")
                    fots = st.file_uploader("Fotoğraflar", accept_multiple_files=True, key=f"f_{r['id']}")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("💾 Kaydet (Taslak)", key=f"tas_{r['id']}"):
                        conn.execute("UPDATE tasks SET report=?, result_type=? WHERE id=?", (report, res, r['id']))
                        conn.commit(); st.success("Taslak Kaydedildi")
                    if c2.button("🚀 İşi Gönder", type="primary", key=f"send_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Giriş Onayında', report=?, result_type=?, updated_at=? WHERE id=?", (report, res, datetime.now().strftime("%Y-%m-%d"), r['id']))
                        conn.commit(); st.success("İş Gönderildi"); st.rerun()

    # --- 👥 KULLANICI YÖNETİMİ (Madde 2) ---
    elif cp == "👥 Kullanıcı Yönetimi" and role == 'Admin':
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("new_u"):
                ne = st.text_input("E-posta"); nn = st.text_input("Ad Soyad"); nr = st.selectbox("Rol", ["Admin", "Yönetici", "Müdür", "Saha Personeli"])
                np = st.text_input("Şifre", type='password')
                if st.form_submit_button("Kaydet"):
                    hp = hashlib.sha256(np.encode()).hexdigest()
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ne, hp, nr, nn, "05xx"))
                    conn.commit(); st.rerun()
        
        udf = pd.read_sql("SELECT email, name, role, phone FROM users", conn)
        st.dataframe(udf, use_container_width=True)

    # --- 📋 OPERASYONEL EKRANLAR (Filtreli & Excel'li) ---
    elif cp in ["📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş"]:
        st.header(cp)
        # Dinamik statü belirleme
        status_map = {
            "📋 Atanan İşler": "('Bekliyor', 'Ret Edildi')",
            "📨 Giriş Onayları": "('Giriş Onayında')",
            "📡 TT Onay Bekleyenler": "('Türk Telekom Onayında')",
            "✅ Tamamlanan İşler": "('Hak Ediş Bekleyen', 'Hak Ediş Alındı', 'Onay Bekliyor')",
            "💰 Hak Ediş": "('Hak Ediş Bekleyen', 'Hak Ediş Alındı')"
        }
        raw_df = pd.read_sql(f"SELECT * FROM tasks WHERE status IN {status_map[cp]}", conn)
        res_df = universal_filter(raw_df, cp.lower().replace(" ","_"))
        
        if res_df.empty:
            st.warning("Gösterilecek Veri Bulunmamaktadır")
        else:
            st.dataframe(res_df, use_container_width=True)

    # --- 👤 PROFİLİM (Madde 9) ---
    elif cp == "👤 Profilim":
        st.header("👤 Profil Ayarları")
        u = conn.execute("SELECT email, phone, name FROM users WHERE email=?", (st.session_state.u_email,)).fetchone()
        with st.form("prof_up"):
            e = st.text_input("E-posta", u[0]); t = st.text_input("Telefon", u[1]); n = st.text_input("Ad Soyad", u[2])
            p = st.text_input("Yeni Şifre (Değişmeyecekse boş bırakın)", type='password')
            if st.form_submit_button("💾 Güncelle"):
                if p:
                    hp = hashlib.sha256(p.encode()).hexdigest()
                    conn.execute("UPDATE users SET email=?, phone=?, name=?, password=? WHERE email=?", (e, t, n, hp, st.session_state.u_email))
                else:
                    conn.execute("UPDATE users SET email=?, phone=?, name=? WHERE email=?", (e, t, n, st.session_state.u_email))
                conn.commit(); st.success("Profil Güncellendi")
