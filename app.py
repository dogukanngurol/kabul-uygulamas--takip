import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import hashlib
import io

# --- ⚙️ 1. SİSTEM VE VERİTABANI AYARLARI ---
st.set_page_config(page_title="Anatolia Bilişim | V71", layout="wide")

def init_db():
    conn = sqlite3.connect('anatoli_v71.db')
    c = conn.cursor()
    # Kullanıcılar, İşler ve Zimmet Tabloları
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, assigned_to TEXT, city TEXT, status TEXT, note TEXT, created_at TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, owner_email TEXT)''')
    
    # Varsayılan Hesaplar
    hashed_pw = hashlib.sha256("1234".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (id, name, email, phone, password, role) VALUES (1, 'Doğukan Gürol', 'admin@anatoli.com', '5550001122', ?, 'Admin')", (hashed_pw,))
    c.execute("INSERT OR IGNORE INTO users (id, name, email, phone, password, role) VALUES (2, 'Saha Ekibi', 'saha@anatoli.com', '5559998877', ?, 'Saha Personeli')", (hashed_pw,))
    conn.commit()
    conn.close()

init_db()

# --- 🛠️ 2. YARDIMCI ARAÇLAR ---
def get_greeting():
    hr = datetime.now().hour
    if 8 <= hr < 12: return "☀️ Günaydın"
    elif 12 <= hr < 18: return "🌤️ İyi Günler"
    elif 18 <= hr < 24: return "🌆 İyi Akşamlar"
    else: return "🌙 İyi Geceler"

def export_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 🔐 3. OTURUM VE GİRİŞ ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Anatolia Bilişim Giriş")
    with st.form("login"):
        e = st.text_input("📧 Mail")
        p = st.text_input("🔑 Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            hpw = hashlib.sha256(p.encode()).hexdigest()
            conn = sqlite3.connect('anatoli_v71.db')
            user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hpw)).fetchone()
            conn.close()
            if user:
                st.session_state.update({'logged_in':True, 'user':{'id':user[0],'name':user[1],'email':user[2],'phone':user[3],'role':user[5]}, 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("❌ Hatalı bilgiler!")
else:
    # --- 📋 4. SOL MENÜ (Madde 2) ---
    with st.sidebar:
        st.markdown(f"## 🏢 Anatolia Bilişim")
        st.info(f"👤 **{st.session_state.user['name']}**\n🛡️ {st.session_state.user['role']}")
        st.divider()
        
        role = st.session_state.user['role']
        if role == "Saha Personeli":
            menu = ["🏠 Ana Sayfa", "⏳ Üzerime Atanan İşler", "📜 Tamamladığım İşler", "🎒 Zimmetim", "👤 Profilim", "🚪 Çıkış"]
        else:
            menu = ["🏠 Ana Sayfa", "➕ İş Ataması", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onayı Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi", "👤 Profilim", "🚪 Çıkış"]
        
        for item in menu:
            style = "primary" if st.session_state.page == item else "secondary"
            if st.sidebar.button(item, use_container_width=True, type=style):
                if item == "🚪 Çıkış":
                    st.session_state.logged_in = False
                    st.rerun()
                st.session_state.page = item
                st.rerun()

    # --- 🖼️ 5. SAYFA İÇERİKLERİ ---
    cp = st.session_state.page
    conn = sqlite3.connect('anatoli_v71.db')

    if cp == "🏠 Ana Sayfa":
        st.header(f"{get_greeting()} {st.session_state.user['name']}, İyi Çalışmalar! 🚀")
        if role != "Saha Personeli":
            c1, c2, c3 = st.columns(3)
            c1.metric("✅ Tamamlanan", "0") # Dinamik sayaçlar buraya bağlanabilir
            c2.metric("⏳ Bekleyen", "0")
            c3.metric("📅 Haftalık", "0")

    elif cp == "➕ İş Ataması":
        st.header("➕ Yeni İş Atama")
        pers_df = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)
        with st.form("task_add"):
            t = st.text_input("📌 İş Başlığı")
            p = st.selectbox("👷 Personel", pers_df['email'] if not pers_df.empty else ["Personel Yok"])
            c = st.selectbox("📍 Şehir", ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"])
            if st.form_submit_button("🚀 Ata"):
                conn.execute("INSERT INTO tasks (title, assigned_to, city, status, created_at) VALUES (?,?,?,?,?)", (t, p, c, 'Atandı', datetime.now().strftime("%d-%m-%Y")))
                conn.commit()
                st.success("✅ İş başarıyla atandı!")

    elif cp == "⏳ Üzerime Atanan İşler":
        st.header("⏳ Üzerime Atanan Görevler")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.user['email']}' AND status='Atandı'", conn)
        if tasks.empty:
            st.info("📭 Üzerinize atanmış aktif bir iş bulunmamaktadır.")
        else:
            for i, r in tasks.iterrows():
                with st.expander(f"📍 {r['title']} - {r['city']}"):
                    note = st.text_area("📝 İş Notu (Zorunlu)", key=f"n_{r['id']}")
                    st.file_uploader("📸 Fotoğraf Ekle (Maks 65)", accept_multiple_files=True, key=f"f_{r['id']}")
                    if st.button("🚀 İşi Gönder", key=f"s_{r['id']}", disabled=not note):
                        conn.execute("UPDATE tasks SET status='Kabul Alındı', note=? WHERE id=?", (note, r['id']))
                        conn.commit()
                        st.rerun()

    elif cp == "📜 Tamamladığım İşler":
        st.header("📜 Tamamladığım İşler")
        done = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.user['email']}' AND status='Kabul Alındı'", conn)
        if done.empty:
            st.warning("🔎 Henüz tamamlanmış bir iş kaydınız bulunmuyor.")
        else:
            st.dataframe(done, use_container_width=True)

    elif cp in ["🎒 Zimmetim", "📦 Zimmet & Envanter"]:
        st.header("📦 Zimmet Bilgileri")
        inv = pd.read_sql(f"SELECT * FROM inventory WHERE owner_email='{st.session_state.user['email']}'", conn)
        if inv.empty:
            st.error("⚠️ Üzerinize tanımlanmış herhangi bir zimmet eşyası bulunmamaktadır.")
        else:
            st.table(inv)

    elif cp == "📋 Atanan İşler":
        st.header("📋 Sistemdeki Atanan İşler")
        all_t = pd.read_sql("SELECT * FROM tasks WHERE status='Atandı'", conn)
        if all_t.empty:
            st.info("✨ Şu anda saha personellerine atanmış aktif bir iş bulunmamaktadır.")
        else:
            st.dataframe(all_t, use_container_width=True)
            st.download_button("📥 Excel İndir", export_excel(all_t), "atananlar.xlsx")

    elif cp == "👤 Profilim":
        st.header("👤 Profil Bilgilerim")
        is_admin = st.session_state.user['role'] == "Admin"
        with st.form("prof_form"):
            # Mail ve Ad Admin harici kilitli
            u_name = st.text_input("👤 Kullanıcı Adı", value=st.session_state.user['name'], disabled=not is_admin)
            u_mail = st.text_input("📧 Mail Adresi", value=st.session_state.user['email'], disabled=not is_admin)
            u_phone = st.text_input("📱 Telefon Numarası", value=st.session_state.user['phone'])
            u_pw = st.text_input("🔑 Yeni Şifre (Boş bırakılırsa değişmez)", type="password")
            
            if st.form_submit_button("💾 Güncelle"):
                if u_pw:
                    hp = hashlib.sha256(u_pw.encode()).hexdigest()
                    conn.execute("UPDATE users SET name=?, email=?, phone=?, password=? WHERE id=?", (u_name, u_mail, u_phone, hp, st.session_state.user['id']))
                else:
                    conn.execute("UPDATE users SET name=?, email=?, phone=? WHERE id=?", (u_name, u_mail, u_phone, st.session_state.user['id']))
                conn.commit()
                st.success("✅ Bilgiler güncellendi!")

    conn.close()
