import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import os

# --- 1. AYARLAR ---
ST_TITLE = "Anatolia Bilişim"
DB_NAME = 'saha_v59.db'

# --- 2. VERİTABANI MOTORU ---
def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", ('admin@sirket.com', pw, 'Admin', 'Admin Kullanıcı', '0555'))
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '0555'))
    conn.commit()

init_db()

# --- 3. EXCEL VE FİLTRE MOTORU ---
def excel_indir_ve_goster(df, key):
    if df is None or df.empty:
        st.warning("⚠️ Gösterilecek Veri Bulunmamaktadır. (Filtreleri Kontrol Edin)")
        return
    
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Rapor')
        st.download_button(label=f"📥 {key.replace('_',' ').title()} Excel", data=output.getvalue(),
                         file_name=f"{key}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Excel Hatası: {e}")

# --- 4. LOGIN SİSTEMİ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title(f"🏢 {ST_TITLE} Giriş")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş Yap"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı Giriş")
else:
    # --- SIDEBAR (SAYFA RENGİ VE VURGU AYARI) ---
    st.sidebar.markdown(f"## 🏢 {ST_TITLE}")
    st.sidebar.markdown(f"👤 **{st.session_state.u_name}** \n 🛡️ *{st.session_state.u_role}*")
    st.sidebar.divider()

    # Sayfa Listesi ve Aktif Sayfa Rengi (Primary Buton)
    if st.session_state.u_role in ['Admin', 'Müdür']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👤 Profilim"]
        if st.session_state.u_role == 'Admin':
            menu.append("👥 Kullanıcı Yönetimi")
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "🎒 Zimmetim", "👤 Profilim"]

    for m in menu:
        # Hangi sayfadaysak o butonu 'primary' yaparak açık renkte/vurgulu gösterir
        is_active = "primary" if st.session_state.page == m else "secondary"
        if st.sidebar.button(m, use_container_width=True, type=is_active):
            st.session_state.page = m
            st.rerun()
    
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- 👥 KULLANICI YÖNETİMİ (ADMIN ÖZEL) ---
    if cp == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Oluşturma ve Yönetim")
        
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("new_user"):
                n_email = st.text_input("E-posta")
                n_name = st.text_input("Ad Soyad")
                n_phone = st.text_input("Telefon")
                n_role = st.selectbox("Yetki", ["Saha Personeli", "Müdür", "Admin"])
                n_pass = st.text_input("Şifre", type="password")
                if st.form_submit_button("Kaydet"):
                    hashed = hashlib.sha256(n_pass.encode()).hexdigest()
                    conn.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?,?)", (n_email, hashed, n_role, n_name, n_phone))
                    conn.commit(); st.success("Kullanıcı Oluşturuldu"); st.rerun()

        st.subheader("📋 Mevcut Kullanıcılar")
        u_df = pd.read_sql("SELECT email, name, role, phone FROM users", conn)
        st.dataframe(u_df, use_container_width=True)
        
        del_mail = st.selectbox("Silinecek Kullanıcıyı Seçin", u_df['email'].tolist())
        if st.button("❌ Seçili Kullanıcıyı Sil", type="primary"):
            if del_mail != "admin@sirket.com":
                conn.execute("DELETE FROM users WHERE email=?", (del_mail,))
                conn.commit(); st.success("Silindi"); st.rerun()
            else: st.error("Ana Admin silinemez!")

    # --- 👤 PROFİLİM (GÜNCELLEME YETKİSİ) ---
    elif cp == "👤 Profilim":
        st.header("👤 Profil Bilgilerimi Güncelle")
        u = conn.execute("SELECT email, phone, name FROM users WHERE email=?", (st.session_state.u_email,)).fetchone()
        with st.form("prof"):
            e_up = st.text_input("E-posta", value=u[0])
            n_up = st.text_input("Ad Soyad", value=u[2])
            p_up = st.text_input("Telefon", value=u[1])
            pass_up = st.text_input("Yeni Şifre (Değişmeyecekse boş bırakın)", type="password")
            if st.form_submit_button("Güncellemeleri Kaydet"):
                if pass_up:
                    hp = hashlib.sha256(pass_up.encode()).hexdigest()
                    conn.execute("UPDATE users SET email=?, phone=?, name=?, password=? WHERE email=?", (e_up, p_up, n_up, hp, st.session_state.u_email))
                else:
                    conn.execute("UPDATE users SET email=?, phone=?, name=? WHERE email=?", (e_up, p_up, n_up, st.session_state.u_email))
                conn.commit(); st.success("Profil Güncellendi"); st.rerun()

    # --- 🏠 ANA SAYFA ---
    elif cp == "🏠 Ana Sayfa":
        st.header(f"📊 {ST_TITLE} Anasayfa")
        # Dinamik Karşılama
        hr = datetime.now().hour
        greet = "Günaydın" if hr < 12 else "İyi Günler" if hr < 18 else "İyi Akşamlar"
        st.subheader(f"{greet}, {st.session_state.u_name}")
        
        # Admin İstatistikleri
        if st.session_state.u_role in ['Admin', 'Müdür']:
            c1, c2 = st.columns(2)
            c1.metric("Toplam İş Sayısı", conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])
            c2.metric("Aktif Personel", conn.execute("SELECT COUNT(*) FROM users WHERE role='Saha Personeli'").fetchone()[0])

    # --- 📋 ATANAN İŞLER ---
    elif cp == "📋 Atanan İşler":
        st.header("📋 Atanan İşler Takip")
        df = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Bekliyor', 'Ret Edildi')", conn)
        excel_indir_ve_goster(df, "atanan_isler")
        if not df.empty: st.dataframe(df)

    # --- DİĞER EKRANLAR İÇİN TASLAK ---
    else:
        st.info(f"{cp} ekranı üzerinde çalışılıyor veya veri bulunmamaktadır.")
