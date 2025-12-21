import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import os
import zipfile

# --- 1. KURUMSAL AYARLAR ---
COMPANY_NAME = "Anatolia Bilişim"
UPLOAD_FOLDER = "saha_dosyalari"
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]

# --- 2. VERİTABANI MOTORU ---
def get_db():
    return sqlite3.connect('anatolia_v65.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Admin Ana Hesap', '05001112233'),
        ('filiz@deneme.com', pw, 'Müdür', 'Filiz Müdür', '05004445566'),
        ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', '05007778899')
    ]
    for u in users: c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. YARDIMCI FONKSİYONLAR ---
def excel_download(df, name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return st.download_button(label=f"📥 {name} Excel İndir", data=output.getvalue(), file_name=f"{name}.xlsx")

def get_greet():
    hr = datetime.now().hour
    if 0 <= hr < 8: return "İyi Geceler"
    elif 8 <= hr < 12: return "Günaydın"
    elif 12 <= hr < 18: return "İyi Günler"
    else: return "İyi Akşamlar"

# --- 4. LOGIN SİSTEMİ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title(f"🏢 {COMPANY_NAME} Giriş")
    with st.form("login"):
        e = st.text_input("Şirket Mail Adresi")
        p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş Yap"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı Mail veya Şifre")
else:
    # --- 5. SIDEBAR (Madde 2) ---
    st.sidebar.markdown(f"### 🏢 {COMPANY_NAME}")
    st.sidebar.markdown(f"**{st.session_state.u_name}**\n*{st.session_state.u_role}*")
    st.sidebar.divider()

    role = st.session_state.u_role
    menu = ["Ana Sayfa"]
    if role in ['Admin', 'Yönetici', 'Müdür']:
        menu += ["İş Ataması", "Atanan İşler", "Giriş Onayları", "TT Onayı Bekleyenler", "Tamamlanan İşler", "Hak Ediş", "Zimmet & Envanter"]
        if role in ['Admin', 'Yönetici']: menu.append("Kullanıcı Yönetimi")
    else:
        menu += ["Üzerime Atanan İşler", "Tamamladığım İşler", "Zimmet & Envanter"]
    
    menu += ["Profilim", "Çıkış"]

    for item in menu:
        # Aktif sayfa vurgusu
        style = "primary" if st.session_state.page == item else "secondary"
        if st.sidebar.button(item, use_container_width=True, type=style):
            if item == "Çıkış":
                st.session_state.logged_in = False
                st.rerun()
            st.session_state.page = item
            st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- 6. SAYFA İÇERİKLERİ ---
    if cp == "Ana Sayfa":
        st.header(f"✨ {get_greet()} {st.session_state.u_name}, İyi Çalışmalar")
        if role in ['Admin', 'Yönetici', 'Müdür']:
            c1, c2, c3, c4 = st.columns(4)
            today = datetime.now().strftime("%Y-%m-%d")
            c1.metric("Günlük Tamamlanan", conn.execute("SELECT COUNT(*) FROM tasks WHERE updated_at=? AND result_type='İŞ TAMAMLANDI'", (today,)).fetchone()[0])
            c2.metric("Bekleyen Atamalar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            c3.metric("Haftalık Toplam", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", ((datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d"),)).fetchone()[0])
            c4.metric("Aylık Toplam", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", ((datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d"),)).fetchone()[0])

    elif cp == "İş Ataması":
        st.header("➕ Yeni İş Ataması")
        pers = pd.read_sql("SELECT email, name FROM users WHERE role='Saha Personeli'", conn)
        with st.form("atama_form"):
            t = st.text_input("İş Başlığı")
            p = st.selectbox("Personel Seçimi", pers['email'].tolist())
            s = st.selectbox("Şehir Seçimi", ILLER)
            if st.form_submit_button("İşi Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, status, city, created_at) VALUES (?,?,?,?,?)", (p, t, 'Bekliyor', s, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success(f"İş {p} personeline başarıyla atandı.")

    elif cp == "Üzerime Atanan İşler":
        st.header("⏳ Atanan Görevlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor', 'Kabul Yapılabilir')", conn)
        if tasks.empty: st.info("Atanan Bir Görev Bulunmamaktadır")
        for _, r in tasks.iterrows():
            with st.expander(f"📌 {r['title']} - {r['city']}"):
                note = st.text_area("İşin Detayı (Zorunlu)", value=r['report'] if r['report'] else "", key=f"n_{r['id']}")
                fots = st.file_uploader("Fotoğraflar (Max 65)", accept_multiple_files=True, key=f"f_{r['id']}")
                res = st.selectbox("Durum", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Maili Gerekli"], key=f"r_{r['id']}")
                
                c1, c2 = st.columns(2)
                if c1.button("💾 Kaydet", key=f"k_{r['id']}"):
                    conn.execute("UPDATE tasks SET report=? WHERE id=?", (note, r['id']))
                    conn.commit(); st.success("Taslak Kaydedildi.")
                
                btn_state = False if note else True
                if c2.button("🚀 İşi Gönder", type="primary", disabled=btn_state, key=f"g_{r['id']}"):
                    new_status = "Giriş Maili Bekler" if res == "Giriş Maili Gerekli" else "Tamamlandı"
                    conn.execute("UPDATE tasks SET status=?, report=?, result_type=?, updated_at=? WHERE id=?", (new_status, note, res, datetime.now().strftime("%Y-%m-%d"), r['id']))
                    conn.commit(); st.rerun()

    elif cp == "Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("user_add"):
                n = st.text_input("İsim Soyisim")
                m = st.text_input("Mail Adresi")
                ph = st.text_input("Telefon")
                rl = st.selectbox("Yetki", ["Saha Personeli", "Müdür", "Yönetici", "Admin"])
                ps = st.text_input("Geçici Şifre")
                if st.form_submit_button("Kullanıcı Oluştur"):
                    hp = hashlib.sha256(ps.encode()).hexdigest()
                    conn.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?,?)", (m, hp, rl, n, ph))
                    conn.commit(); st.rerun()
        
        users_df = pd.read_sql("SELECT name, email, role, phone FROM users", conn)
        st.dataframe(users_df, use_container_width=True)
        excel_download(users_df, "Kullanici_Listesi")

    elif cp == "Profilim":
        st.header("👤 Profil Bilgilerim")
        u = conn.execute("SELECT * FROM users WHERE email=?", (st.session_state.u_email,)).fetchone()
        st.text(f"İsim: {u[3]}")
        st.text(f"Mail: {u[0]}")
        new_phone = st.text_input("Telefon Numarası", value=u[4])
        if st.button("Güncelle"):
            conn.execute("UPDATE users SET phone=? WHERE email=?", (new_phone, st.session_state.u_email))
            conn.commit(); st.success("Telefon güncellendi.")

    # Diğer Onay Ekranları (TT, Hak Ediş vb.) benzer filtreleme yapısıyla eklenir...
    elif cp in ["Atanan İşler", "Tamamlanan İşler", "Hak Ediş"]:
        st.header(cp)
        df = pd.read_sql("SELECT * FROM tasks", conn) # Örnek genel çekim
        if df.empty: st.warning("Gösterilecek Veri Bulunmamaktadır")
        else:
            st.dataframe(df, use_container_width=True)
            excel_download(df, cp)
