import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import hashlib
import io

# --- ⚙️ 1. KONFİGÜRASYON VE VERİTABANI ---
st.set_page_config(page_title="Anatolia Bilişim | Operasyon Merkezi", layout="wide")

def init_db():
    conn = sqlite3.connect('anatolia_v75.db')
    c = conn.cursor()
    # Tablo yapıları (Madde 1, 4, 10, 11)
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, assigned_to TEXT, city TEXT, status TEXT, note TEXT, created_at TEXT, updated_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, owner_email TEXT)''')
    
    # Demo Kullanıcılar (Madde 1)
    pw = hashlib.sha256("1234".encode()).hexdigest()
    demo_users = [
        (1, 'Doğukan Gürol', 'admin@anatolia.com', '05001112233', pw, 'Admin'),
        (2, 'Yönetici Panel', 'yonetici@anatolia.com', '05001112234', pw, 'Yönetici'),
        (3, 'Müdür Panel', 'mudur@anatolia.com', '05001112235', pw, 'Müdür'),
        (4, 'Saha Ekibi', 'saha@anatolia.com', '05001112236', pw, 'Saha Personeli')
    ]
    c.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", demo_users)
    conn.commit()
    conn.close()

init_db()

# --- 🛠️ 2. YARDIMCI ARAÇLAR ---
def get_greeting(): # Madde 3 & 14
    hr = datetime.now().hour
    u = st.session_state.user['name']
    if 8 <= hr < 12: return f"☀️ Günaydın {u}, İyi Çalışmalar"
    elif 12 <= hr < 18: return f"🌤️ İyi Günler {u}, İyi Çalışmalar"
    elif 18 <= hr < 24: return f"🌆 İyi Akşamlar {u}, İyi Çalışmalar"
    else: return f"🌙 İyi Geceler {u}, İyi Çalışmalar"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 🔐 3. GİRİŞ KONTROLÜ ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏢 Anatolia Bilişim Sistem Girişi")
    with st.container(border=True):
        email_input = st.text_input("📧 E-Posta Adresi (admin@anatolia.com)")
        pass_input = st.text_input("🔑 Şifre (1234)", type="password")
        if st.button("Sisteme Giriş Yap", use_container_width=True, type="primary"):
            hpw = hashlib.sha256(pass_input.encode()).hexdigest()
            conn = sqlite3.connect('anatolia_v75.db')
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email_input, hpw)).fetchone()
            conn.close()
            if u:
                st.session_state.update({'logged_in': True, 'user': {'id':u[0],'name':u[1],'email':u[2],'phone':u[3],'role':u[5]}, 'page': "🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("❌ E-posta veya şifre hatalı!")

else:
    # --- 📋 4. SOL MENÜ (Madde 2) ---
    u_role = st.session_state.user['role']
    u_mail = st.session_state.user['email']
    
    with st.sidebar:
        st.markdown(f"## Anatolia Bilişim")
        st.caption(f"👤 {st.session_state.user['name']} | 🛡️ {u_role}")
        st.divider()
        
        # Rol Bazlı Menü Yapılandırması
        if u_role == "Saha Personeli":
            menu = ["🏠 Ana Sayfa", "⏳ Üzerime Atanan İşler", "📜 Tamamladığım İşler", "🎒 Zimmetim", "👤 Profilim", "🚪 Çıkış"]
        else:
            menu = ["🏠 Ana Sayfa", "➕ İş Ataması", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onayı Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi", "👤 Profilim", "🚪 Çıkış"]
        
        for item in menu:
            btn_type = "primary" if st.session_state.page == item else "secondary"
            if st.sidebar.button(item, use_container_width=True, type=btn_type):
                if item == "🚪 Çıkış": 
                    st.session_state.logged_in = False
                    st.rerun()
                st.session_state.page = item
                st.rerun()

    # --- 🖼️ 5. SAYFA İÇERİKLERİ ---
    conn = sqlite3.connect('anatolia_v75.db')
    cp = st.session_state.page

    if cp == "🏠 Ana Sayfa":
        st.header(get_greeting())
        if u_role != "Saha Personeli":
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("✅ Günlük Tamamlanan", "0", delta="Günlük")
            c2.metric("⏳ Bekleyen Atamalar", "0")
            c3.metric("📅 Haftalık Toplam", "0")
            c4.metric("📊 Aylık Toplam", "0")
        else:
            st.info("💡 Atanan işlerinizi yönetmek için yan menüden 'Üzerime Atanan İşler'e gidin.")

    elif cp == "➕ İş Ataması":
        st.header("➕ Yeni İş Ataması")
        pers = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)
        with st.form("task_form"):
            t = st.text_input("📌 İş Başlığı")
            w = st.selectbox("👷 Personel", pers['email'] if not pers.empty else ["Personel Yok"])
            c = st.selectbox("📍 Şehir", ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir"]) # 81 il eklenebilir
            if st.form_submit_button("🚀 İşi Ata"):
                conn.execute("INSERT INTO tasks (title, assigned_to, city, status, created_at) VALUES (?,?,?,?,?)", (t, w, c, 'Atandı', datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success("✅ İş başarıyla atandı!")

    elif cp == "⏳ Üzerime Atanan İşler":
        st.header("⏳ Üzerime Atanan Görevler")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{u_mail}' AND status IN ('Atandı', 'Taslak')", conn)
        if tasks.empty:
            st.warning("Atanan Bir Görev Bulunmamaktadır")
        else:
            for i, r in tasks.iterrows():
                with st.expander(f"📍 {r['title']} - {r['city']}"):
                    note = st.text_area("📝 İş Detayı (ZORUNLU)", value=r['note'] if r['note'] else "", key=f"n_{r['id']}")
                    st.file_uploader("📸 Fotoğraflar (Maks 65)", accept_multiple_files=True, key=f"f_{r['id']}")
                    c1, c2, c3 = st.columns(3)
                    if c1.button("💾 Kaydet (Taslak)", key=f"s_{r['id']}"):
                        conn.execute("UPDATE tasks SET note=?, status='Taslak' WHERE id=?", (note, r['id']))
                        conn.commit()
                        st.toast("Taslak Kaydedildi!")
                    if c2.button("📨 Giriş Maili Gerekli", key=f"m_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Giriş Maili Bekler' WHERE id=?", (r['id'],))
                        conn.commit()
                        st.rerun()
                    if c3.button("🚀 İşi Gönder", type="primary", disabled=not note, key=f"g_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Kabul Alındı', note=?, updated_at=? WHERE id=?", (note, datetime.now().strftime("%Y-%m-%d"), r['id']))
                        conn.commit()
                        st.success("İş başarıyla gönderildi!")
                        st.rerun()

    elif cp == "👤 Profilim":
        st.header("👤 Profil Bilgileri")
        is_p_admin = u_role in ["Admin", "Yönetici"]
        with st.form("profile_form"):
            st.text_input("Kullanıcı Adı", value=st.session_state.user['name'], disabled=not is_p_admin)
            st.text_input("Şirket Maili", value=st.session_state.user['email'], disabled=not is_p_admin)
            new_phone = st.text_input("Telefon Numarası", value=st.session_state.user['phone'])
            if st.form_submit_button("💾 Güncelle"):
                conn.execute("UPDATE users SET phone=? WHERE id=?", (new_phone, st.session_state.user['id']))
                conn.commit()
                st.success("Telefon numaranız güncellendi!")

    conn.close()
