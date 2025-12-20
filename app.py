import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json

# --- 1. VERİTABANI ---
def init_db():
    conn = sqlite3.connect('saha_final_v28.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, result_type TEXT, hakedis_durum TEXT)''')
    
    def h(p): return hashlib.sha256(p.encode()).hexdigest()
    users = [
        ('admin@sirket.com', h('1234'), 'admin', 'Sistem Yöneticisi', 'Genel Müdür', '0555'),
        ('filiz@deneme.com', h('1234'), 'admin', 'Filiz Hanım', 'Müdür', '0555'),
        ('dogukan@deneme.com', h('1234'), 'worker', 'Doğukan Gürol', 'Saha Çalışanı', '0555'),
        ('doguscan@deneme.com', h('1234'), 'worker', 'Doğuşcan Gürol', 'Saha Çalışanı', '0555'),
        ('cuneyt@deneme.com', h('1234'), 'worker', 'Cüneyt Bey', 'Saha Çalışanı', '0555')
    ]
    c.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?)", users)
    conn.commit()
    return conn

conn = init_db()

# --- 2. ARAYÜZ ---
st.set_page_config(page_title="Saha Operasyon v28", layout="wide")

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

    # --- SAYFA: ÇALIŞAN PANELİ (TASLAK VE DOSYA EKLEME) ---
    if cp == "⏳ Atanan İşler":
        st.header("⏳ Üstüme Atanan İşler")
        # Bekleyen veya Kabul Yapılabilir durumdaki işleri çek
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state['user_email']}' AND status IN ('Bekliyor', 'Kabul Yapılabilir')", conn)
        
        if tasks.empty:
            st.info("Şu an aktif bir görev bulunmuyor.")
        
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']} - {r['city']} {'(✅ ONAYLANDI)' if r['status'] == 'Kabul Yapılabilir' else ''}"):
                st.markdown(f"**Görev Detayı:** {r['description']}")
                st.divider()

                # --- Veri Giriş Alanları ---
                res_list = ["Seçiniz", "Giriş Mail Onayı Bekler", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
                # Eğer daha önce taslak kaydedilmişse eski sonucu getir
                try: default_idx = res_list.index(r['result_type']) if r['result_type'] in res_list else 0
                except: default_idx = 0

                res = st.selectbox("İşlem/Sonuç Tipi", res_list, index=default_idx, key=f"res_{r['id']}")
                rep = st.text_area("İşte Yapılan Notlar / Rapor", value=r['report'] if r['report'] else "", placeholder="Yapılan işlemleri buraya yazın...", key=f"rep_{r['id']}")
                
                fots = st.file_uploader("Fotoğraf ve Dosya Ekle", accept_multiple_files=True, key=f"file_{r['id']}")
                
                if r['photos_json']:
                    st.caption("✅ Sistemde kayıtlı taslak fotoğraflarınız var. Yeni yükleme yapmazsanız onlar korunur.")

                # --- Butonlar ---
                c1, c2 = st.columns(2)
                
                # 1. TASLAK KAYDET BUTONU
                if c1.button("💾 Taslağı Kaydet", key=f"save_{r['id']}", use_container_width=True):
                    # Fotoğrafları hex formatına çevir (eğer yeni fotoğraf yüklendiyse)
                    p_json = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                    conn.execute("UPDATE tasks SET report=?, photos_json=?, result_type=? WHERE id=?", 
                                 (rep, p_json, res, r['id']))
                    conn.commit()
                    st.toast("İlerleyişiniz başarıyla kaydedildi!", icon="💾")

                # 2. İŞİ GÖNDER BUTONU
                if c2.button("🚀 İşi Onaya Gönder", key=f"send_{r['id']}", use_container_width=True, type="primary"):
                    if res == "Seçiniz":
                        st.error("Lütfen bir İş Sonucu seçin!")
                    elif res == "Giriş Mail Onayı Bekler":
                        conn.execute("UPDATE tasks SET status='Giriş Mail Onayı Bekler', updated_at=? WHERE id=?", 
                                     (datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                        conn.commit()
                        st.warning("İş müdür onayına gönderildi.")
                        st.rerun()
                    else:
                        p_json = json.dumps([f.read().hex() for f in fots]) if fots else r['photos_json']
                        conn.execute("UPDATE tasks SET status='Onay Bekliyor', report=?, photos_json=?, result_type=?, updated_at=? WHERE id=?", 
                                     (rep, p_json, res, datetime.now().strftime("%d/%m/%Y %H:%M"), r['id']))
                        conn.commit()
                        st.success("İş başarıyla tamamlandı ve merkeze gönderildi!")
                        st.rerun()

    # --- SAYFA: MÜDÜR ONAY EKRANI ---
    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Onayı Bekleyen Talepler")
        onay_bekleyenler = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        for _, r in onay_bekleyenler.iterrows():
            with st.expander(f"📍 {r['title']} - {r['assigned_to']}"):
                st.write(f"**Personel Notu:** {r['report']}")
                if st.button("Kabul Yapılabilir", key=f"ok_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Kabul Yapılabilir' WHERE id=?", (r['id'],))
                    conn.commit(); st.success("Onay verildi."); st.rerun()

    # --- DİĞER SAYFALAR (v27 ile aynı) ---
    elif cp == "🏠 Ana Sayfa":
        st.info(f"✨ {st.session_state['user_name']}, Hoş Geldiniz!")
        # ... Sayaçlar ve karşılama metni ...
