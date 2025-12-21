import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- 1. ŞİRKET VE SİSTEM AYARLARI ---
ST_TITLE = "Anatolia Bilişim"
UPLOAD_DIR = "saha_dosyalari"
if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir", "Konya", "Samsun"]

# --- 2. VERİTABANI VE TABLO YAPISI (GÜNCELLENDİ) ---
def get_db():
    return sqlite3.connect('saha_v58.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Kullanıcılar tablosu (phone ve email güncellenebilir yapıda)
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    # Görevler tablosu (Tüm süreç kolonları dahil)
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        assigned_to TEXT, title TEXT, description TEXT, status TEXT, 
        report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, 
        result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    # Envanter tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    # Admin ve Müdür Tanımlama
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", ('admin@sirket.com', pw, 'Admin', 'Admin Kullanıcı', '0555'))
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '0555'))
    conn.commit()

init_db()

# --- 3. ORTAK FONKSİYONLAR (EXCEL & FİLTRE) ---
def excel_indir_ve_goster(df, key):
    """Veri yoksa uyarı verir, varsa indirme butonu koyar."""
    if df is None or df.empty:
        st.warning("⚠️ Gösterilecek Veri Bulunmamaktadır.")
        return False
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    
    st.download_button(
        label=f"📥 {key.replace('_',' ').title()} Excel İndir",
        data=output.getvalue(),
        file_name=f"{key}_{datetime.now().strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"btn_{key}"
    )
    return True

def filtre_paneli(df, key_prefix):
    """Tüm ekranlarda ortak tarih, personel, şehir ve durum filtreleri."""
    st.write("### 🔍 Filtreleme Paneli")
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_tarih = st.date_input("Tarih Aralığı", [], key=f"t_{key_prefix}")
    with c2: f_pers = st.selectbox("Personel", ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"], key=f"p_{key_prefix}")
    with c3: f_sehir = st.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"s_{key_prefix}")
    with c4: 
        d_opts = ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
        if st.session_state.get('u_role') in ['Admin', 'Müdür']:
            d_opts += ["Türk Telekom Onayında", "Hak Ediş Bekleniyor", "Hak Ediş Alındı"]
        f_durum = st.selectbox("Durum", d_opts, key=f"d_{key_prefix}")
    
    filtered = df.copy()
    if not filtered.empty:
        if f_pers != "Hepsi": filtered = filtered[filtered['assigned_to'] == f_pers]
        if f_sehir != "Hepsi": filtered = filtered[filtered['city'] == f_sehir]
        if f_durum != "Hepsi":
            if f_durum in ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]:
                filtered = filtered[filtered['result_type'] == f_durum]
            else:
                filtered = filtered[filtered['status'] == f_durum]
    
    excel_indir_ve_goster(filtered, key_prefix)
    return filtered

# --- 4. ANA DÖNGÜ VE LOGIN ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title(f"🛡️ {ST_TITLE} Operasyon Sistemi")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("E-posta veya Şifre Hatalı!")
else:
    # --- SOL ÜST: ŞİRKET ADI, KULLANICI ADI VE YETKİ ---
    st.sidebar.markdown(f"## 🏢 {ST_TITLE}")
    st.sidebar.markdown(f"👤 **{st.session_state.u_name}** \n 🛡️ *{st.session_state.u_role}*")
    st.sidebar.divider()

    menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👤 Profilim"]
    if st.session_state.u_role not in ['Admin', 'Müdür']:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "🎒 Zimmetim", "👤 Profilim"]

    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    if st.sidebar.button("🔴 ÇIKIŞ"): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- EKRANLAR ---
    if cp == "🏠 Ana Sayfa":
        st.header(f"📊 {ST_TITLE} - Genel Durum")
        # 11. ADMIN ANASAYFASI (MADDE 11 GÜNCELLEMESİ)
        c1, c2, c3 = st.columns(3)
        if st.session_state.u_role in ['Admin', 'Müdür']:
            c1.metric("Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Hak Ediş Alındı'").fetchone()[0])
            c2.metric("Bekleyen Atamalar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            c3.metric("Haftalık Toplam İş", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", ((datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d"),)).fetchone()[0])

    elif cp == "📋 Atanan İşler":
        st.header("📋 Atanan İşler Takip")
        df = pd.read_sql("SELECT assigned_to, title, city, status, created_at FROM tasks WHERE status IN ('Bekliyor', 'Ret Edildi')", conn)
        res = filtre_paneli(df, "atanan_isler")
        if not res.empty: st.dataframe(res, use_container_width=True)

    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Onayı Bekleyenler")
        df = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Onayı Bekliyor'", conn)
        res = filtre_paneli(df, "giris_onaylari")
        if not res.empty:
            for _, r in res.iterrows():
                with st.expander(f"📌 {r['title']} ({r['assigned_to']})"):
                    if st.button("Onayla ve Başlat", key=f"on_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Bekliyor' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "📡 TT Onay Bekleyenler":
        st.header("📡 Türk Telekom Onay Bekleyenler")
        df = pd.read_sql("SELECT * FROM tasks WHERE status='Türk Telekom Onayında'", conn)
        res = filtre_paneli(df, "tt_onay_bekleyenler")
        if not res.empty: st.dataframe(res, use_container_width=True)

    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Yönetimi")
        df = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleyen', 'Hak Ediş Alındı')", conn)
        res = filtre_paneli(df, "hak_edis_ekrani")
        if not res.empty: st.dataframe(res, use_container_width=True)

    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Zimmet ve Envanter Yönetimi")
        df = pd.read_sql("SELECT * FROM inventory", conn)
        res = filtre_paneli(df, "envanter_rapor")
        if not res.empty: st.dataframe(res, use_container_width=True)

    elif cp == "👤 Profilim":
        st.header("👤 Kullanıcı Profili ve Güncelleme")
        # TÜM KULLANICILAR İÇİN PROFİL GÜNCELLEME (MADDE 1 VE YENİ İSTEK)
        u_data = conn.execute("SELECT email, phone, name FROM users WHERE email=?", (st.session_state.u_email,)).fetchone()
        
        with st.form("profil_form"):
            new_mail = st.text_input("E-posta Adresi", value=u_data[0])
            new_phone = st.text_input("Telefon Numarası", value=u_data[1])
            new_name = st.text_input("Ad Soyad", value=u_data[2])
            new_pass = st.text_input("Yeni Şifre (Boş bırakılırsa değişmez)", type='password')
            
            if st.form_submit_button("💾 Güncellemeleri Kaydet"):
                try:
                    if new_pass:
                        hashed_pw = hashlib.sha256(new_pass.encode()).hexdigest()
                        conn.execute("UPDATE users SET email=?, phone=?, name=?, password=? WHERE email=?", (new_mail, new_phone, new_name, hashed_pw, st.session_state.u_email))
                    else:
                        conn.execute("UPDATE users SET email=?, phone=?, name=? WHERE email=?", (new_mail, new_phone, new_name, st.session_state.u_email))
                    conn.commit()
                    st.success("Profil başarıyla güncellendi! Lütfen sayfayı yenileyin.")
                except Exception as e:
                    st.error(f"Hata: {e}")

    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        p_list = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist()
        with st.form("atama"):
            t = st.text_input("İş Başlığı"); p = st.selectbox("Atanacak Personel", p_list); s = st.selectbox("Şehir", ILLER)
            d = st.text_area("İş Açıklaması")
            if st.form_submit_button("Görevi Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city, created_at) VALUES (?,?,?,?,?,?)", (p, t, d, 'Bekliyor', s, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.success("İş Atandı!")
