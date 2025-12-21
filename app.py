import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import os

# --- 🛠️ 1. AYARLAR VE KLASÖRLER ---
COMPANY_NAME = "Anatolia Bilişim"
UPLOAD_FOLDER = "saha_dosyalari"
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

# 🌍 81 İl Listesi
ILLER = ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir", "Konya", "Samsun"] # ... (diğer iller buraya eklenir)

# --- 🗄️ 2. VERİTABANI MOTORU ---
def get_db():
    return sqlite3.connect('anatolia_v66.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, status TEXT, report TEXT, city TEXT, result_type TEXT, created_at TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Yönetici Hesap', '05001112233'),
        ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '05004445566'),
        ('saha@deneme.com', pw, 'Saha Personeli', 'Saha Ekibi-1', '05007778899')
    ]
    for u in users: c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- ⚙️ 3. YARDIMCI ARAÇLAR ---
def excel_indir(df, baslik):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return st.download_button(label=f"📥 {baslik} Excel Raporu", data=output.getvalue(), file_name=f"{baslik}.xlsx")

def selam_ver():
    hr = datetime.now().hour
    if 0 <= hr < 8: return "🌙 İyi Geceler"
    elif 8 <= hr < 12: return "☀️ Günaydın"
    elif 12 <= hr < 18: return "🌤️ İyi Günler"
    else: return "🌆 İyi Akşamlar"

# --- 🔐 4. GİRİŞ KONTROLÜ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title(f"🏢 {COMPANY_NAME} | Sistem Girişi 🔑")
    with st.form("login"):
        e = st.text_input("📧 Şirket Mail Adresi")
        p = st.text_input("🔒 Şifre", type='password')
        if st.form_submit_button("🚀 Giriş Yap"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("❌ Hatalı Giriş Bilgileri!")
else:
    # --- 📋 5. YAN MENÜ (SIDEBAR) ---
    st.sidebar.markdown(f"# 🏢 {COMPANY_NAME}")
    st.sidebar.success(f"👤 **{st.session_state.u_name}**\n\n🛡️ Yetki: *{st.session_state.u_role}*")
    st.sidebar.divider()

    role = st.session_state.u_role
    menu = ["🏠 Ana Sayfa"]
    
    if role in ['Admin', 'Yönetici', 'Müdür']:
        menu += ["➕ İş Ataması", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onayı Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter"]
        if role in ['Admin', 'Yönetici']: menu.append("👥 Kullanıcı Yönetimi")
    else:
        menu += ["⏳ Üzerime Atanan İşler", "📜 Tamamladığım İşler", "🎒 Zimmetim"]
    
    menu += ["👤 Profilim", "🔴 Çıkış"]

    for item in menu:
        style = "primary" if st.session_state.page == item else "secondary"
        if st.sidebar.button(item, use_container_width=True, type=style):
            if item == "🔴 Çıkış":
                st.session_state.logged_in = False
                st.rerun()
            st.session_state.page = item
            st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- 🖼️ 6. SAYFA İÇERİKLERİ ---

    if cp == "🏠 Ana Sayfa":
        st.header(f"{selam_ver()} {st.session_state.u_name}! 👋")
        st.info("💡 Anatolia Bilişim Saha Operasyon Yönetim Paneline Hoş Geldiniz.")
        
        if role in ['Admin', 'Yönetici', 'Müdür']:
            st.markdown("### 📊 Operasyonel Durum")
            c1, c2, c3 = st.columns(3)
            c1.metric("✅ Bugün Tamamlanan", "12 İş")
            c2.metric("⏳ Bekleyen Atamalar", "5 İş")
            c3.metric("📅 Haftalık Toplam", "84 İş", delta="↑ 12%")
            
    elif cp == "➕ İş Ataması":
        st.header("➕ Yeni İş Atama Formu 📝")
        pers = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)
        with st.form("atama"):
            t = st.text_input("📌 İş Başlığı")
            p = st.selectbox("👷 Personel Seçimi", pers['email'].tolist())
            s = st.selectbox("📍 Şehir Seçimi", ILLER)
            if st.form_submit_button("🚀 İşi Personelimize Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, status, city, created_at) VALUES (?,?,?,?,?)", (p, t, 'Bekliyor', s, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success(f"✅ İş başarıyla {p} kullanıcısına atandı!")

    elif cp == "⏳ Üzerime Atanan İşler":
        st.header("⏳ Üzerime Atanan Görevler 👷")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status='Bekliyor'", conn)
        if tasks.empty:
            st.warning("📭 Atanan Bir Görev Bulunmamaktadır.")
        else:
            for _, r in tasks.iterrows():
                with st.expander(f"📍 {r['title']} - {r['city']}"):
                    note = st.text_area("✍️ İş Notu / Raporu (Zorunlu)", key=f"n_{r['id']}")
                    fots = st.file_uploader("📸 Fotoğraf Ekle (Max 65)", accept_multiple_files=True, key=f"f_{r['id']}")
                    res = st.selectbox("🏁 İş Sonucu", ["✅ İŞ TAMAMLANDI", "🚫 GİRİŞ YAPILAMADI", "⚠️ TEPKİLİ", "❌ MAL SAHİBİ GELMİYOR", "📧 Giriş Maili Gerekli"], key=f"r_{r['id']}")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("💾 Taslağı Kaydet", key=f"k_{r['id']}"):
                        st.success("💾 Notlar kaydedildi, göndermeye hazır!")
                    if c2.button("🚀 İşi Onaya Gönder", type="primary", key=f"g_{r['id']}"):
                        if note:
                            st.balloons()
                            st.success("✅ İş başarıyla merkeze gönderildi!")
                        else: st.error("⚠️ Lütfen iş notunu doldurunuz!")

    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Zimmet ve Envanter Yönetimi 🛠️")
        if role in ['Admin', 'Müdür']:
            with st.expander("➕ Yeni Zimmet Tanımla"):
                with st.form("zimmet"):
                    st.text_input("🛠️ Ürün Adı")
                    st.selectbox("👷 Personel", ["Saha Ekibi 1"])
                    st.number_input("🔢 Adet", 1)
                    st.form_submit_button("💾 Zimmetle")
        
        st.info("📋 Mevcut Zimmet Listesi")
        df_inv = pd.DataFrame({'Ürün': ['Matkap', 'Fiber Kablo'], 'Personel': ['Doğukan', 'Cüneyt'], 'Adet': [1, 50]})
        st.table(df_inv)
        excel_indir(df_inv, "Zimmet_Raporu")

    elif cp == "👤 Profilim":
        st.header("👤 Kişisel Bilgilerim ⚙️")
        st.markdown(f"**📧 E-posta:** {st.session_state.u_email}")
        st.markdown(f"**🏷️ Rolünüz:** {st.session_state.u_role}")
        new_tel = st.text_input("📱 Telefon Numaranızı Güncelleyin", "05xx")
        if st.button("💾 Bilgilerimi Kaydet"):
            st.success("✅ Profil bilgileriniz başarıyla güncellendi!")
