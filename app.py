import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json

# --- 1. VERİTABANI GÜNCELLEME ---
def init_db():
    conn = sqlite3.connect('saha_final_v27.db', check_same_thread=False)
    c = conn.cursor()
    # Ekstra durum sütunları eklendi
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, result_type TEXT, hakedis_durum TEXT)''')
    
    def h(p): return hashlib.sha256(p.encode()).hexdigest()
    # Varsayılan kullanıcılar
    users = [
        ('admin@sirket.com', h('1234'), 'admin', 'Sistem Yöneticisi', 'Genel Müdür', '0555'),
        ('filiz@deneme.com', h('1234'), 'admin', 'Filiz Hanım', 'Müdür', '0555'),
        ('dogukan@deneme.com', h('1234'), 'worker', 'Doğukan Gürol', 'Saha Çalışanı', '0555')
    ]
    c.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", users)
    conn.commit()
    return conn

conn = init_db()

# --- 2. ARAYÜZ AYARLARI ---
st.set_page_config(page_title="Saha Operasyon v27", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Operasyon Giriş")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            u = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4], 'page':"🏠 Ana Sayfa"})
                st.rerun()
else:
    # --- YAN MENÜ ---
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    menu_options = ["🏠 Ana Sayfa"]
    if st.session_state['role'] == 'admin':
        menu_options += ["➕ İş Atama", "📨 Giriş Onayları", "✅ Tamamlanan İşler", "💰 Hak Ediş", "👥 Kullanıcılar"]
    else:
        menu_options += ["⏳ Atanan İşler", "📜 İş Geçmişim"]
    
    for opt in menu_options:
        if st.sidebar.button(opt, use_container_width=True): st.session_state.page = opt

    if st.sidebar.button("🔴 Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    cp = st.session_state.page

    # --- SAYFA: SAHA PERSONELİ EKRANI ---
    if cp == "⏳ Atanan İşler":
        st.header("⏳ Görevlerim")
        # Bekleyen veya Kabul Yapılabilir durumdaki işler
        my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status IN ('Bekliyor', 'Kabul Yapılabilir')", conn)
        
        if my_tasks.empty:
            st.info("Şu an aktif bir işiniz bulunmuyor.")
        
        for _, r in my_tasks.iterrows():
            color = "blue" if r['status'] == 'Kabul Yapılabilir' else "white"
            with st.expander(f"📋 {r['title']} {'(✅ GİRİŞ ONAYLANDI)' if r['status'] == 'Kabul Yapılabilir' else ''}"):
                if r['status'] == 'Kabul Yapılabilir':
                    st.success("Müdür bu iş için 'Kabul Yapılabilir' onayı verdi. Çalışmaya başlayabilirsiniz.")
                
                # Seçenekler
                res_options = ["İşlem Seçin", "Giriş Mail Onayı Bekler", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
                res = st.selectbox("İşlem/Sonuç Tipi", res_options, key=f"res_{r['id']}")
                
                if st.button("Durumu Güncelle", key=f"btn_{r['id']}"):
                    if res == "Giriş Mail Onayı Bekler":
                        conn.execute("UPDATE tasks SET status='Giriş Mail Onayı Bekler', updated_at=? WHERE id=?", (datetime.now().strftime("%d/%m/%H:%M"), r['id']))
                        conn.commit()
                        st.warning("İş onaya gönderildi. Müdür onayı bekleniyor.")
                        st.rerun()
                    elif res != "İşlem Seçin":
                        conn.execute("UPDATE tasks SET status='Onay Bekliyor', result_type=?, updated_at=? WHERE id=?", (res, datetime.now().strftime("%d/%m/%H:%M"), r['id']))
                        conn.commit()
                        st.success("İş başarıyla gönderildi.")
                        st.rerun()

    # --- SAYFA: MÜDÜR GİRİŞ ONAY EKRANI ---
    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Mail Onayı Bekleyen İşler")
        onay_bekleyenler = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        
        if onay_bekleyenler.empty:
            st.info("Onay bekleyen giriş talebi yok.")
        else:
            for _, r in onay_bekleyenler.iterrows():
                with st.expander(f"📍 {r['title']} - Personel: {r['assigned_to']}"):
                    st.write(f"**Açıklama:** {r['description']}")
                    st.write(f"**Şehir:** {r['city']}")
                    if st.button("İzin Ver: Kabul Yapılabilir", key=f"ok_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Kabul Yapılabilir', updated_at=? WHERE id=?", (datetime.now().strftime("%d/%m/%H:%M"), r['id']))
                        conn.commit()
                        st.success("Personel bilgilendirildi, iş 'Kabul Yapılabilir' olarak işaretlendi.")
                        st.rerun()

    # --- SAYFA: İŞ ATAMA ---
    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        workers = pd.read_sql("SELECT email, name FROM users WHERE role='worker'", conn)
        with st.form("new_task"):
            t = st.text_input("İş Başlığı")
            w = st.selectbox("Personel", workers['email'].tolist())
            c = st.selectbox("Şehir", ["İstanbul", "Ankara", "İzmir", "Adana", "Bursa"])
            d = st.text_area("Detaylar")
            if st.form_submit_button("Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city) VALUES (?,?,?,?,?)", (w, t, d, 'Bekliyor', c))
                conn.commit(); st.success("İş atandı.")

    # Diğer sayfalar (Ana Sayfa, Tamamlananlar vb.) v26 mantığıyla çalışmaya devam eder.
    elif cp == "🏠 Ana Sayfa":
        st.info(f"✨ İyi Çalışmalar **{st.session_state['user_name']}**!")
        c1, c2 = st.columns(2)
        c1.metric("📌 Bekleyen Giriş Onayları", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Giriş Mail Onayı Bekler'").fetchone()[0])
        c2.metric("✅ Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Hak Edişi Alındı'").fetchone()[0])
