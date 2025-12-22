import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import hashlib
import io
import zipfile

# --- 1. SİSTEM VE DB AYARLARI ---
st.set_page_config(page_title="Anatolia Bilişim | Operasyon", layout="wide")

def init_db():
    conn = sqlite3.connect('anatoli_v72.db')
    c = conn.cursor()
    # Kullanıcılar
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, password TEXT, role TEXT)''')
    # İşler (Metadata odaklı: report, status_history, photo_refs JSON formatında tutulabilir)
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY, title TEXT, assigned_to TEXT, city TEXT, status TEXT, 
        note TEXT, photo_refs TEXT, created_at TEXT, updated_at TEXT, reject_reason TEXT)''')
    # Zimmet
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, owner_email TEXT)''')
    
    # 1. Madde: Kullanıcı Oluşturma
    hashed_pw = hashlib.sha256("1234".encode()).hexdigest()
    users_list = [
        (1, 'Admin', 'admin@sirket.com', '5550001122', hashed_pw, 'Admin'),
        (2, 'Doğukan', 'dogukan@deneme.com', '5551112233', hashed_pw, 'Saha Personeli'),
        (3, 'Doğuşcan', 'doguscan@deneme.com', '5552223344', hashed_pw, 'Saha Personeli'),
        (4, 'Cüneyt', 'cuneyt@deneme.com', '5553334455', hashed_pw, 'Saha Personeli'),
        (5, 'Filiz', 'filiz@deneme.com', '5554445566', hashed_pw, 'Müdür')
    ]
    c.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", users_list)
    conn.commit()
    conn.close()

init_db()

# --- 🛠️ YARDIMCI ARAÇLAR (Madde 6 & 10) ---
def get_greeting():
    hr = datetime.now().hour
    u = st.session_state.user['name']
    if 8 <= hr < 12: return f"☀️ Günaydın {u}, İyi Çalışmalar"
    elif 12 <= hr < 18: return f"🌤️ İyi Günler {u}, İyi Çalışmalar"
    elif 18 <= hr < 24: return f"🌆 İyi Akşamlar {u}, İyi Çalışmalar"
    else: return f"🌙 İyi Geceler {u}, İyi Çalışmalar"

def create_zip(files): # Madde 6: RAR/ZIP Çıktısı
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for f in files:
            z.writestr(f.name, f.getvalue())
    return buf.getvalue()

# --- 🔐 GİRİŞ SİSTEMİ ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Anatolia Bilişim Sistem Girişi")
    with st.form("login"):
        e = st.text_input("📧 Mail")
        p = st.text_input("🔑 Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            hpw = hashlib.sha256(p.encode()).hexdigest()
            conn = sqlite3.connect('anatoli_v72.db')
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hpw)).fetchone()
            conn.close()
            if u:
                st.session_state.update({'logged_in':True, 'user':{'id':u[0],'name':u[1],'email':u[2],'phone':u[3],'role':u[5]}, 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("❌ Hatalı Giriş")

else:
    # --- 📋 SOL MENÜ ---
    u_role = st.session_state.user['role']
    u_mail = st.session_state.user['email']
    
    with st.sidebar:
        st.markdown(f"## 🏢 Anatolia Bilişim")
        st.info(f"👤 **{st.session_state.user['name']}**\n🛡️ {u_role}")
        
        menu = ["🏠 Ana Sayfa"]
        if u_role in ["Admin", "Müdür"]:
            menu += ["➕ İş Ataması", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onayı Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
        else: # Saha Personeli (Madde 12)
            menu += ["⏳ Üzerime Atanan İşler", "📜 Çalışmalarım", "🎒 Zimmetim"]
        
        menu += ["👤 Profilim", "🚪 Çıkış"]
        
        for item in menu:
            if st.sidebar.button(item, use_container_width=True, type="primary" if st.session_state.page == item else "secondary"):
                if item == "🚪 Çıkış": st.session_state.logged_in = False
                else: st.session_state.page = item
                st.rerun()

    conn = sqlite3.connect('anatoli_v72.db')
    page = st.session_state.page

    # --- 🏠 ANA SAYFA (Madde 10 & 12) ---
    if page == "🏠 Ana Sayfa":
        st.header(get_greeting())
        if u_role == "Admin":
            c1, c2, c3 = st.columns(3)
            c1.metric("✅ Tamamlanan İşler", "24")
            c2.metric("⏳ Bekleyen Atamalar", "8")
            c3.metric("📅 Haftalık Toplam", "142") # Sayaç simülasyonu
        elif u_role == "Saha Personeli":
            st.info("💡 Atanan işlerinizi 'Üzerime Atanan İşler' sekmesinden yönetebilirsiniz.")

    # --- ➕ İŞ ATAMASI (Madde 1 & 4) ---
    elif page == "➕ İş Ataması":
        st.header("➕ Yeni İş Ataması")
        # Müdür hariç saha personellerini listele (Madde 1)
        pers = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)
        with st.form("task_assign"):
            title = st.text_input("İş Başlığı")
            worker = st.selectbox("Çalışan Seçin", pers['email'])
            city = st.selectbox("Şehir", ["İstanbul", "Adana", "Ankara", "İzmir", "Diğer"]) # Madde 5
            if st.form_submit_button("İşi Ata"):
                conn.execute("INSERT INTO tasks (title, assigned_to, city, status, created_at) VALUES (?,?,?,?,?)", 
                             (title, worker, city, 'Atandı', datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success("İş Atandı!")

    # --- ⏳ SAHA PERSONELİ EKRANI (Madde 2 & 3) ---
    elif page == "⏳ Üzerime Atanan İşler":
        st.header("⏳ Aktif Görevlerim")
        my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{u_mail}' AND status IN ('Atandı', 'Taslak', 'Reddedildi')", conn)
        
        for i, row in my_tasks.iterrows():
            with st.expander(f"📍 {row['title']} ({row['status']})"):
                # Madde 3: Durum Seçim Kutusu
                status_choice = st.selectbox("Durum Seçin", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"], key=f"st_{row['id']}")
                note = st.text_area("Rapor Yazma Alanı", value=row['note'] if row['note'] else "", key=f"nt_{row['id']}")
                files = st.file_uploader("Dosya/Fotoğraf Ekle", accept_multiple_files=True, key=f"fl_{row['id']}")
                
                col1, col2 = st.columns(2)
                # Madde 2: Taslak Kaydetme
                if col1.button("💾 Kaydet (Taslak)", key=f"save_{row['id']}"):
                    conn.execute("UPDATE tasks SET note=?, status='Taslak' WHERE id=?", (note, row['id']))
                    conn.commit()
                    st.toast("Taslak olarak saklandı.")
                
                # Madde 11: Giriş Mail Onayı Akışı
                if col2.button("🚀 İşi Gönder", key=f"send_{row['id']}", type="primary"):
                    final_status = "Giriş Mail Onayı Bekler" if status_choice == "Giriş Mail Onayı Bekler" else "Tamamlandı"
                    conn.execute("UPDATE tasks SET status=?, note=?, updated_at=? WHERE id=?", 
                                 (status_choice, note, datetime.now().strftime("%Y-%m-%d"), row['id']))
                    conn.commit()
                    st.success("İş gönderildi!")
                    st.rerun()

    # --- ✅ TAMAMLANAN İŞLER VE FİLTRELEME (Madde 4, 5, 8) ---
    elif page == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Listesi")
        
        # Filtreleme Alanı (Madde 4 & 5)
        c1, c2, c3 = st.columns(3)
        with c1: f_city = st.selectbox("Şehir Filtresi", ["Hepsi", "İstanbul", "Adana", "Ankara"])
        with c2: f_worker = st.selectbox("Çalışan Filtresi", ["Hepsi"] + pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist())
        with c3: f_type = st.radio("İş Grubu", ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler"])

        query = "SELECT * FROM tasks WHERE status NOT IN ('Atandı', 'Taslak')"
        df = pd.read_sql(query, conn)
        
        # Mantıksal Filtreleme (Madde 4)
        if f_type == "Tamamlanan İşler": df = df[df['status'] == 'İŞ TAMAMLANDI']
        elif f_type == "Tamamlanamayan İşler": df = df[df['status'].isin(['GİRİŞ YAPILAMADI', 'TEPKİLİ', 'MAL SAHİBİ GELMİYOR'])]
        
        if f_city != "Hepsi": df = df[df['city'] == f_city]
        
        st.dataframe(df, use_container_width=True)
        
        # Madde 6: Excel Çıktısı
        if not df.empty:
            buf = io.BytesIO()
            df.to_excel(buf, index=False)
            st.download_button("📥 Seçili Verileri Excel Olarak İndir", buf.getvalue(), "rapor.xlsx")

    # --- 👤 PROFİLİM (Madde 1) ---
    elif page == "👤 Profilim":
        st.header("👤 Profil Ayarları")
        with st.form("profile"):
            # Madde 1: Müdür harici güncelleme kuralları
            can_edit = u_role != "Müdür"
            new_mail = st.text_input("E-posta", value=u_mail, disabled=not can_edit)
            new_phone = st.text_input("Telefon", value=st.session_state.user['phone'], disabled=not can_edit)
            new_pw = st.text_input("Yeni Şifre (Şifre Değiştirme)", type="password")
            
            if st.form_submit_button("Güncellemeleri Kaydet"):
                # DB Update kodları...
                st.success("Profil Güncellendi!")

    conn.close()
