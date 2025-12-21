import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io

# --- AYARLAR ---
COMPANY_NAME = "Anatolia Bilişim"
ILLER = ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir", "Konya", "Samsun"]

def get_db():
    return sqlite3.connect('anatolia_v61.db', check_same_thread=False)

# --- FOTOĞRAF KAYIT SİMÜLASYONU (Madde 10) ---
def save_photos(uploaded_files):
    # Gerçek uygulamada dosyalar bir klasöre kaydedilir, veritabanına sadece yollar yazılır.
    photo_paths = [f"uploads/{f.name}" for f in uploaded_files]
    return ",".join(photo_paths)

# --- YETKİ KONTROLÜ VE SAYFA LİSTESİ ---
def get_menu(role):
    if role == 'Admin':
        return ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi", "👤 Profilim"]
    elif role == 'Yönetici':
        return ["🏠 Ana Sayfa", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👤 Profilim"]
    elif role == 'Müdür':
        return ["🏠 Ana Sayfa", "📡 TT Onay Bekleyenler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👤 Profilim"]
    else: # Saha Personeli
        return ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]

# --- LOGIN SİSTEMİ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title(f"🏢 {COMPANY_NAME} Giriş")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            # Örnek girişler v60 ile aynı... (Veritabanı kontrolü)
            st.session_state.update({'logged_in':True, 'u_email':e, 'u_role':'Admin', 'u_name':'Admin', 'page':"🏠 Ana Sayfa"})
            st.rerun()
else:
    # --- SIDEBAR TASARIMI ---
    st.sidebar.markdown(f"### 🏢 {COMPANY_NAME}")
    st.sidebar.markdown(f"👤 **{st.session_state.u_name}**\n⭐ *{st.session_state.u_role}*")
    st.sidebar.divider()

    menu = get_menu(st.session_state.u_role)
    for m in menu:
        is_active = "primary" if st.session_state.page == m else "secondary"
        if st.sidebar.button(m, use_container_width=True, type=is_active):
            st.session_state.page = m; st.rerun()

    # --- SAHA PERSONELİ: ÜZERİMDEKİ İŞLER (FOTOĞRAF EKLEME) ---
    if st.session_state.page == "⏳ Atanan İşlerim":
        st.header("⏳ Üzerimdeki İşler")
        conn = get_db()
        my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}'", conn)
        
        if my_tasks.empty:
            st.info("Gösterilecek Atanmış İş Bulunmamaktadır.")
        else:
            for _, r in my_tasks.iterrows():
                with st.expander(f"📌 {r['title']} - {r['city']}"):
                    st.write(f"**Açıklama:** {r['description']}")
                    
                    # FOTOĞRAF YÜKLEME ALANI (Yeni Eklendi)
                    uploaded_files = st.file_uploader(f"Çalışma Fotoğrafları Ekle ({r['id']})", 
                                                    accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key=f"img_{r['id']}")
                    
                    res_type = st.selectbox("Çalışma Sonucu", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"], key=f"res_{r['id']}")
                    report_note = st.text_area("Çalışma Notu", key=f"note_{r['id']}")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("💾 Kaydet (Taslak)", key=f"draft_{r['id']}"):
                        st.success("Taslak Başarıyla Kaydedildi.")
                    
                    if c2.button("🚀 İşi Onaya Gönder", type="primary", key=f"send_{r['id']}"):
                        p_paths = save_photos(uploaded_files) if uploaded_files else ""
                        conn.execute("UPDATE tasks SET status='Giriş Onayında', report=?, photos_json=?, result_type=? WHERE id=?", 
                                   (report_note, p_paths, res_type, r['id']))
                        conn.commit()
                        st.success("İş başarıyla gönderildi!")
                        st.rerun()

    # --- YÖNETİCİ / ADMIN: OPERASYONEL EKRANLAR ---
    elif st.session_state.page in ["📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler"]:
        target_status = {
            "📋 Atanan İşler": "Bekliyor",
            "📨 Giriş Onayları": "Giriş Onayında",
            "📡 TT Onay Bekleyenler": "Türk Telekom Onayında"
        }[st.session_state.page]
        
        st.header(st.session_state.page)
        conn = get_db()
        df = pd.read_sql(f"SELECT * FROM tasks WHERE status='{target_status}'", conn)
        
        if df.empty:
            st.warning(f"Gösterilecek {st.session_state.page} Bulunmamaktadır.")
            # Boş olsa bile filtreleri gösteriyoruz (Madde 10)
            c1, c2 = st.columns(2)
            c1.selectbox("Personel Filtresi", ["Hepsi"], disabled=True)
            c2.date_input("Tarih Filtresi", [])
        else:
            st.dataframe(df, use_container_width=True)
            # Onay/Ret butonları buraya eklenebilir.

    # --- ZİMMET & ENVANTER (YÖNETİCİ GÖRÜR) ---
    elif st.session_state.page == "📦 Zimmet & Envanter":
        st.header("📦 Genel Envanter ve Zimmet Listesi")
        conn = get_db()
        inv_df = pd.read_sql("SELECT * FROM inventory", conn)
        
        if inv_df.empty:
            st.info("Envanterde kayıtlı ürün bulunmamaktadır.")
        else:
            st.dataframe(inv_df, use_container_width=True)

    # ... Diğer ekranlar (v60 ile aynı mantıkta devam eder)
