import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
from docx import Document
from docx.shared import Inches

# --- 1. VERİTABANI VE KURULUM ---
def init_db():
    conn = sqlite3.connect('saha_operasyon_v24.db', check_same_thread=False)
    c = conn.cursor()
    # Tablo Güncellemeleri (City ve Hakedis durumları eklendi)
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, task_result TEXT, hakedis_durum TEXT)''')
    
    # Şifre Hash Fonksiyonu
    def h(p): return hashlib.sha256(p.encode()).hexdigest()
    
    # --- OTOMATİK KULLANICI TANIMLAMALARI ---
    users = [
        ('admin@sirket.com', h('1234'), 'admin', 'Ahmet Salça', 'Genel Müdür'),
        ('filiz@deneme.com', h('1234'), 'admin', 'Filiz Hanım', 'Müdür'),
        ('dogukan@deneme.com', h('1234'), 'worker', 'Doğukan Gürol', 'Saha Çalışanı'),
        ('doguscan@deneme.com', h('1234'), 'worker', 'Doğuşcan Gürol', 'Saha Çalışanı'),
        ('cuneyt@deneme.com', h('1234'), 'worker', 'Cüneyt Bey', 'Saha Çalışanı')
    ]
    c.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", users)
    conn.commit()
    return conn

conn = init_db()

# --- ŞEHİR LİSTESİ ---
SEHIRLER = ["İstanbul", "Ankara", "İzmir", "Adana", "Antalya", "Bursa", "Diyarbakır", "Erzurum", "Gaziantep", "Konya", "Samsun", "Trabzon", "Şanlıurfa"]

# --- 2. ANA UYGULAMA ---
st.set_page_config(page_title="Saha Operasyon v24", layout="wide")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Operasyon Giriş Paneli")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            u = conn.cursor().execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'user_email':u[0], 'role':u[2], 'user_name':u[3], 'user_title':u[4], 'page': "🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı giriş!")
else:
    # --- SIDEBAR ---
    st.sidebar.title(f"👤 {st.session_state['user_name']}")
    st.sidebar.caption(f"🏷️ {st.session_state['user_title']}")
    
    # Menü Ayarları
    if st.session_state['role'] == 'admin':
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "✅ Tamamlanan İşler", "💰 Hak Ediş Paneli", "📦 Zimmet", "👥 Kullanıcılar"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Üstüme Atanan İşler", "📜 İş Geçmişim"]

    for item in menu:
        if st.sidebar.button(item, use_container_width=True): st.session_state.page = item

    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    cp = st.session_state.page

    # --- SAYFA: İŞ ATAMA (FİLİZ HANIM GİZLENDİ) ---
    if cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        # Sadece Saha Çalışanlarını (Worker) listele
        workers = pd.read_sql("SELECT email, name FROM users WHERE role='worker'", conn)
        with st.form("task_form"):
            col1, col2 = st.columns(2)
            t = col1.text_input("İş Başlığı")
            w = col1.selectbox("Saha Personeli", workers['email'].tolist())
            city = col2.selectbox("Şehir", SEHIRLER)
            desc = st.text_area("İş Detayı")
            if st.form_submit_button("Görevi Tanımla"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city, hakedis_durum) VALUES (?,?,?,?,?,?)", 
                             (w, t, desc, 'Bekliyor', city, 'Süreçte'))
                conn.commit(); st.success("İş atandı!")

    # --- SAYFA: SAHA ÇALIŞANI EKRANI (KAYDET & GÖNDER) ---
    elif cp == "⏳ Üstüme Atanan İşler":
        st.header("⏳ Bekleyen Görevlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status='Bekliyor'", conn)
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']} - {r['city']}"):
                # Durum Seçenekleri
                res = st.selectbox("İş Durumu", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"], key=f"res_{r['id']}")
                rep = st.text_area("Rapor Notu", value=r['report'] if r['report'] else "", key=f"r_{r['id']}")
                fots = st.file_uploader("Fotoğraf Ekle", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                if c1.button("💾 Taslak Olarak Kaydet", key=f"s_{r['id']}"):
                    p_json = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET report=?, photos_json=?, task_result=? WHERE id=?", (rep, p_json, res, r['id']))
                    conn.commit(); st.info("Taslak kaydedildi.")
                
                if c2.button("🚀 İşi Gönder", key=f"b_{r['id']}"):
                    p_json = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET status='Onay Bekliyor', report=?, photos_json=?, task_result=?, updated_at=? WHERE id=?", 
                                 (rep, p_json, res, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                    conn.commit(); st.success("İş onaya gönderildi!"); st.rerun()

    # --- SAYFA: TAMAMLANAN İŞLER (ADMİN FİLTRELEME) ---
    elif cp == "✅ Tamamlanan İşler":
        st.header("📑 İş Takip Arşivi")
        
        # Gelişmiş Filtreleme Alanı
        with st.container():
            f1, f2, f3, f4 = st.columns(4)
            f_person = f1.selectbox("Çalışan", ["Hepsi"] + pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist())
            f_city = f2.selectbox("Şehir Filtresi", ["Hepsi"] + SEHIRLER)
            f_status = f3.selectbox("Durum Filtresi", ["Hepsi", "Türk Telekom Onayında", "Tamamlandı", "Hak Edişi Alındı"])
            
            q = "SELECT * FROM tasks WHERE status != 'Bekliyor'"
            if f_person != "Hepsi": q += f" AND assigned_to='{f_person}'"
            if f_city != "Hepsi": q += f" AND city='{f_city}'"
            if f_status != "Hepsi": q += f" AND status='{f_status}'"
            
            df = pd.read_sql(q, conn)
            st.dataframe(df[['id', 'title', 'assigned_to', 'city', 'status', 'task_result', 'updated_at']], use_container_width=True)

            for _, r in df.iterrows():
                with st.expander(f"Detay: {r['title']}"):
                    if r['status'] == 'Onay Bekliyor' and st.session_state['user_title'] == 'Müdür':
                        if st.button("Türk Telekom Onayına Al", key=f"tt_{r['id']}"):
                            conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],))
                            conn.commit(); st.rerun()
                    
                    if r['status'] == 'Türk Telekom Onayında' and st.session_state['user_title'] == 'Müdür':
                        if st.button("Onaylandı - Filiz Hanım'a Gönder", key=f"f_{r['id']}"):
                            conn.execute("UPDATE tasks SET status='Tamamlandı', hakedis_durum='Hak Ediş Bekliyor' WHERE id=?", (r['id'],))
                            conn.commit(); st.rerun()

    # --- SAYFA: HAK EDİŞ PANELİ (FİLİZ HANIM ÖZEL) ---
    elif cp == "💰 Hak Ediş Paneli":
        st.header("💰 Hak Ediş Yönetimi")
        q_h = "SELECT * FROM tasks WHERE status='Tamamlandı'"
        if st.session_state['user_email'] == 'filiz@deneme.com':
            st.write("Hoş geldiniz Filiz Hanım. Hak edişi gelen işleri buradan yönetebilirsiniz.")
        
        df_h = pd.read_sql(q_h, conn)
        for _, r in df_h.iterrows():
            with st.expander(f"💎 {r['title']} - {r['assigned_to']}"):
                st.write(f"Durum: {r['hakedis_durum']}")
                if r['hakedis_durum'] == 'Hak Ediş Bekliyor':
                    if st.button("Hak Ediş Alındı Olarak İşaretle", key=f"h_{r['id']}"):
                        conn.execute("UPDATE tasks SET hakedis_durum='Hak Edişi Alındı', status='Hak Edişi Alındı' WHERE id=?", (r['id'],))
                        conn.commit(); st.rerun()
