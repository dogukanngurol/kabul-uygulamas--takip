import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI SABİTLEME ---
def init_db():
    # Veritabanı ismini sabitliyoruz ki her reboot'ta kullanıcılar kaybolmasın
    conn = sqlite3.connect('operasyon_merkezi.db', check_same_thread=False)
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
    
    # Kullanıcı Listesini Güncelliyoruz
    admin_pass = h('1234')
    users = [
        ('admin@sirket.com', admin_pass, 'admin', 'Sistem Yöneticisi', 'Genel Müdür', '0555'),
        ('filiz@deneme.com', admin_pass, 'admin', 'Filiz Hanım', 'Müdür', '0555'),
        ('dogukan@deneme.com', admin_pass, 'worker', 'Doğukan Gürol', 'Saha Çalışanı', '0555'),
        ('doguscan@deneme.com', admin_pass, 'worker', 'Doğuşcan Gürol', 'Saha Çalışanı', '0555'),
        ('cuneyt@deneme.com', admin_pass, 'worker', 'Cüneyt Bey', 'Saha Çalışanı', '0555')
    ]
    
    # Mevcut kullanıcıların şifrelerini güncelle veya yenilerini ekle
    for user in users:
        c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?)", user)
    
    conn.commit()
    return conn

conn = init_db()

# --- 2. GİRİŞ KONTROLÜ ---
st.set_page_config(page_title="Saha Yönetim Paneli", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Giriş Ekranı
if not st.session_state['logged_in']:
    st.title("🔐 Operasyon Merkezi Giriş")
    
    with st.container():
        email = st.text_input("E-posta Adresi (Örn: admin@sirket.com)")
        password = st.text_input("Şifre", type='password')
        
        if st.button("Sisteme Giriş Yap"):
            if email and password:
                hashed_pw = hashlib.sha256(password.encode()).hexdigest()
                user = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (email, hashed_pw)).fetchone()
                
                if user:
                    st.session_state.update({
                        'logged_in': True,
                        'user_email': user[0],
                        'role': user[2],
                        'user_name': user[3],
                        'user_title': user[4],
                        'user_phone': user[5],
                        'page': "🏠 Ana Sayfa"
                    })
                    st.success("Giriş Başarılı! Yönlendiriliyorsunuz...")
                    st.rerun()
                else:
                    st.error("❌ E-posta veya şifre hatalı. Lütfen kontrol edin.")
            else:
                st.warning("⚠️ Lütfen tüm alanları doldurun.")

# --- 3. ANA UYGULAMA ---
else:
    # Yan Menü Tasarımı
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.info(f"Yetki: {st.session_state['user_title']}")
    
    # Dinamik Menü Oluşturma
    if st.session_state['user_title'] in ['Müdür', 'Genel Müdür', 'Sistem Yöneticisi']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama & Takip", "📨 Giriş Onayları", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşler", "📜 Çalışma Geçmişim", "🎒 Zimmetim", "👤 Profilim"]
    
    for item in menu:
        if st.sidebar.button(item, use_container_width=True):
            st.session_state.page = item
            st.rerun()
    
    if st.sidebar.button("🔴 GÜVENLİ ÇIKIŞ", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    # Sayfa Yönlendirmeleri
    cp = st.session_state.page

    # --- ANA SAYFA (SAYAÇLAR) ---
    if cp == "🏠 Ana Sayfa":
        st.header(f"Merhaba, {st.session_state['user_name']}")
        c1, c2, c3 = st.columns(3)
        with c1:
            bekleyen = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0]
            st.metric("Atanmış Bekleyen İşler", bekleyen)
        with c2:
            onayda = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Onay Bekliyor'").fetchone()[0]
            st.metric("Onay Bekleyen İşler", onayda)
        with c3:
            biten = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Hak Edişi Alındı'").fetchone()[0]
            st.metric("Tamamlanan Hak Edişler", biten)

    # --- SAHA ÇALIŞANI: ATANAN İŞLER ---
    elif cp == "⏳ Atanan İşler":
        st.header("📋 Görev Listem")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status IN ('Bekliyor', 'Kabul Yapılabilir')", conn)
        
        if tasks.empty:
            st.info("Şu an üzerinizde aktif bir iş bulunmuyor.")
        else:
            for _, r in tasks.iterrows():
                with st.expander(f"📍 {r['title']} - {r['city']}"):
                    st.write(f"**Talimat:** {r['description']}")
                    # Form Alanları (Taslak özellikli)
                    res = st.selectbox("İş Sonucu", ["Seçiniz", "Giriş Mail Onayı Bekler", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"], key=f"r_{r['id']}")
                    rep = st.text_area("Rapor Notu", value=r['report'] if r['report'] else "", key=f"t_{r['id']}")
                    
                    if st.button("🚀 Gönder", key=f"b_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Onay Bekliyor', result_type=?, report=? WHERE id=?", (res, rep, r['id']))
                        conn.commit()
                        st.rerun()

    # --- PROFİL GÜNCELLEME (MAİL/TEL) ---
    elif cp == "👤 Profilim":
        st.header("Profil Bilgilerini Güncelle")
        with st.form("p_form"):
            new_mail = st.text_input("E-posta", value=st.session_state['user_email'])
            new_phone = st.text_input("Telefon", value=st.session_state['user_phone'])
            if st.form_submit_button("Bilgileri Kaydet"):
                conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (new_mail, new_phone, st.session_state['user_email']))
                conn.commit()
                st.success("Profil güncellendi. Lütfen tekrar giriş yapın.")
                st.session_state.logged_in = False
                st.rerun()
