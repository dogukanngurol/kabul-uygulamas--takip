import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib

# --- ⚙️ 5. VERİ MODELİ (MOCK DB) ---
def init_mock_db():
    conn = sqlite3.connect('anatolia_demo.db')
    c = conn.cursor()
    # Users & Roles (Madde 2)
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, role TEXT, password TEXT)''')
    # Jobs & Status (Madde 3, 4, 5)
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        title TEXT, 
        assigned_to TEXT, 
        status TEXT, 
        photos_count INTEGER DEFAULT 0,
        payment_status BOOLEAN DEFAULT 0)''')
    # Logs (Madde 7)
    c.execute('''CREATE TABLE IF NOT EXISTS logs (action TEXT, timestamp TEXT)''')
    
    # Demo Verileri Ekleme
    admin_pw = hashlib.sha256('1234'.encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users VALUES ('Mudur_Ali', 'Müdür', ?)", (admin_pw,))
    c.execute("INSERT OR IGNORE INTO users VALUES ('Saha_Can', 'Saha Personeli', ?)", (admin_pw,))
    c.execute("INSERT OR IGNORE INTO users VALUES ('Yonetici_Ayşe', 'Yönetici', ?)", (admin_pw,))
    conn.commit()
    conn.close()

init_mock_db()

# --- 🚀 4. İŞ DURUMLARI (ENUMS) ---
class Status:
    ATANDI = "🎯 ATANDI"
    SAHADA = "🏗️ SAHADA_YAPILIYOR"
    TAMAMLANDI = "✅ TAMAMLANDI"
    MUDUR_ONAYI = "👨‍💼 MUDUR_ONAYINDA"
    YONETICI_ONAYI = "👩‍💻 YONETICI_ONAYINDA"
    ODEME_BEKLIYOR = "💰 ODEME_BEKLENIYOR"
    ONAYLANDI = "🌟 ONAYLANDI"

# --- 📱 UI & LOGIC ---
st.set_page_config(page_title="Anatolia Bilişim Demo", layout="wide")

if 'user' not in st.session_state:
    st.session_state.user = None

# --- 🔑 GİRİŞ SİMÜLASYONU ---
if not st.session_state.user:
    st.title("🏢 Anatolia Bilişim Prototip Girişi")
    u = st.text_input("Kullanıcı Adı (Demo: Mudur_Ali, Saha_Can, Yonetici_Ayşe)")
    p = st.text_input("Şifre (1234)", type="password")
    if st.button("Giriş Yap"):
        st.session_state.user = {"name": u, "role": "Müdür" if "Mudur" in u else ("Yönetici" if "Yonetici" in u else "Saha Personeli")}
        st.rerun()

else:
    # --- 📋 SOL MENÜ ---
    st.sidebar.title(f"👤 {st.session_state.user['name']}")
    st.sidebar.write(f"🛡️ Rol: {st.session_state.user['role']}")
    
    menu = ["İş Akışı", "Raporlama (Demo)", "Sistem Logları", "Çıkış"]
    choice = st.sidebar.radio("Menü", menu)

    conn = sqlite3.connect('anatolia_demo.db')

    # --- 3. DEMO İŞ AKIŞI (WORKFLOW) ---
    if choice == "İş Akışı":
        st.header("🔄 Rol Bazlı İş Akışı Simülasyonu")
        
        # MÜDÜR: İŞ ATAMA (Madde 3.1)
        if st.session_state.user['role'] == "Müdür":
            with st.expander("➕ Yeni İş Ata (Müdür Yetkisi)"):
                t = st.text_input("İş Başlığı")
                if st.button("Ata"):
                    conn.execute("INSERT INTO jobs (title, assigned_to, status) VALUES (?, ?, ?)", (t, 'Saha_Can', Status.ATANDI))
                    conn.execute("INSERT INTO logs VALUES (?, ?)", (f"İş atandı: {t}", datetime.now().isoformat()))
                    conn.commit()
                    st.success("İş Saha Personeline atandı!")

        # SAHA PERSONELİ: FOTOĞRAF VE TAMAMLAMA (Madde 3.2, 3.3, 6)
        if st.session_state.user['role'] == "Saha Personeli":
            st.subheader("📥 Üzerimdeki İşler")
            jobs = pd.read_sql("SELECT * FROM jobs WHERE assigned_to='Saha_Can' AND status='🎯 ATANDI'", conn)
            for _, row in jobs.iterrows():
                st.info(f"İş: {row['title']}")
                # Madde 6: Fotoğraf Yönetimi (Mock)
                photo_count = st.slider("Eklenecek Mock Fotoğraf Sayısı (Maks 65)", 0, 65, 5)
                if st.button("İşi Tamamla & Onaya Gönder"):
                    conn.execute("UPDATE jobs SET status=?, photos_count=? WHERE id=?", (Status.TAMAMLANDI, photo_count, row['id']))
                    conn.commit()
                    st.success(f"{photo_count} dummy fotoğraf eklendi. Statü: TAMAMLANDI")

        # YÖNETİCİ: ÖDEME VE ONAY (Madde 3.5)
        if st.session_state.user['role'] == "Yönetici":
            st.subheader("💳 Ödeme ve Son Onay Ekranı")
            jobs = pd.read_sql(f"SELECT * FROM jobs WHERE status='{Status.TAMAMLANDI}'", conn)
            for _, row in jobs.iterrows():
                st.warning(f"Onay Bekleyen: {row['title']} ({row['photos_count']} Fotoğraf)")
                pay = st.checkbox(f"Ödeme Alındı mı? (ID: {row['id']})")
                if st.button(f"Süreci Kapat (ID: {row['id']})"):
                    final_status = Status.ONAYLANDI if pay else Status.ODEME_BEKLIYOR
                    conn.execute("UPDATE jobs SET status=?, payment_status=? WHERE id=?", (final_status, pay, row['id']))
                    conn.commit()
                    st.rerun()

    # --- 9. RAPORLAMA (DEMO) ---
    elif choice == "Raporlama (Demo)":
        st.header("📊 Demo Raporlama Paneli")
        df_all = pd.read_sql("SELECT * FROM jobs", conn)
        st.table(df_all)

    # --- 7. LOGLAMA ---
    elif choice == "Sistem Logları":
        st.header("📜 İşlem Geçmişi (Logs)")
        logs = pd.read_sql("SELECT * FROM logs ORDER BY timestamp DESC", conn)
        st.dataframe(logs)

    elif choice == "Çıkış":
        st.session_state.user = None
        st.rerun()

    conn.close()
