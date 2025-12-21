import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- 1. AYARLAR VE STORAGE ---
UPLOAD_DIR = "uploaded_photos"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]

# --- 2. VERİTABANI ---
def get_db():
    return sqlite3.connect('operasyon_v47.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [('admin@sirket.com', pw, 'Admin', 'Sistem Admin', '0555'),
             ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '0555'),
             ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', '0555')]
    for u in users: c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. YARDIMCI FONKSİYONLAR ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

def advanced_filter(df, key_suffix, empty_msg="Gösterilecek Veri Bulunmamaktadır"):
    """Filtreleme kutucuklarını her zaman gösterir, veri yoksa mesaj döner."""
    with st.expander("🔍 Filtreleme ve Raporlama Seçenekleri", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        
        # Personel Listesi Hazırlığı
        p_list = ["Hepsi"]
        if not df.empty and 'assigned_to' in df.columns:
            p_list += sorted(df['assigned_to'].unique().tolist())
            
        p_filter = c1.selectbox("Personel", p_list, key=f"p_{key_suffix}")
        c_filter = c2.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"c_{key_suffix}")
        d_list = ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
        d_filter = c3.selectbox("Durum (Sonuç)", d_list, key=f"d_{key_suffix}")
        t_filter = c4.date_input("Tarih Aralığı", [], key=f"t_{key_suffix}")
        
        # Filtreleme İşlemleri
        filtered_df = df.copy()
        if not filtered_df.empty:
            if p_filter != "Hepsi": filtered_df = filtered_df[filtered_df['assigned_to'] == p_filter]
            if c_filter != "Hepsi": filtered_df = filtered_df[filtered_df['city'] == c_filter]
            if d_filter != "Hepsi": filtered_df = filtered_df[filtered_df['result_type'] == d_filter]
            # Tarih filtresi eklenebilir (created_at üzerinden)

        # Excel İndirme Butonu (Sadece veri varsa aktif)
        if not filtered_df.empty:
            st.download_button("📥 Filtrelenmiş Veriyi Excel Olarak İndir", to_excel(filtered_df), f"Rapor_{key_suffix}.xlsx", key=f"dl_{key_suffix}")
        
    if filtered_df.empty:
        st.info(f"ℹ️ {empty_msg}")
        return pd.DataFrame() # Boş DF dön
    return filtered_df

# --- 4. ARAYÜZ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🛡️ Saha Operasyon v47")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
else:
    # Sidebar Karşılama
    hr = datetime.now().hour
    msg = "Günaydın" if 8<=hr<12 else "İyi Günler" if 12<=hr<18 else "İyi Akşamlar" if 18<=hr<24 else "İyi Geceler"
    st.sidebar.markdown(f"### {msg}, {st.session_state.u_name}")
    
    # Menü Tanımları
    if st.session_state.u_role in ['Admin', 'Müdür']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler Takip", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- YÖNETİCİ EKRANLARI ---
    if cp == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Arşivi")
        # Sadece "Onay Bekliyor" olmayan ve "Bekliyor" olmayan işleri çek (Tamamlanmış veya Tamamlanamamış olanlar)
        df = pd.read_sql("SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Mail Onayı Bekler', 'Onay Bekliyor')", conn)
        df = advanced_filter(df, "arsiv", "Gösterilecek Tamamlanmış İş Bulunmamaktadır")
        if not df.empty:
            st.dataframe(df, use_container_width=True)

    elif cp == "📋 Atanan İşler Takip":
        st.header("📋 Tüm Atanan İşler Takip Listesi")
        df = pd.read_sql("SELECT assigned_to, title, city, status, created_at FROM tasks WHERE status IN ('Bekliyor', 'Ret Edildi', 'Kabul Yapılabilir')", conn)
        df = advanced_filter(df, "takip", "Şu an sahada bekleyen veya atanan bir iş bulunmamaktadır")
        if not df.empty:
            st.dataframe(df, use_container_width=True)

    elif cp == "📨 Giriş Onayları":
        st.header("📨 Giriş Onay Bekleyenler")
        df = pd.read_sql("SELECT * FROM tasks WHERE status='Giriş Mail Onayı Bekler'", conn)
        df = advanced_filter(df, "giris_onay", "Onay bekleyen giriş maili bulunmamaktadır")
        if not df.empty:
            for _, r in df.iterrows():
                with st.container():
                    st.write(f"📌 **{r['title']}** ({r['assigned_to']})")
                    if st.button(f"Kabul Yapılabilir Olarak İşaretle", key=f"go_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Kabul Yapılabilir' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "📡 TT Onay Bekleyenler":
        st.header("📡 Türk Telekom Onay Listesi")
        df = pd.read_sql("SELECT * FROM tasks WHERE status='Türk Telekom Onayında'", conn)
        df = advanced_filter(df, "tt_onay", "Türk Telekom onayında bekleyen iş bulunmamaktadır")
        if not df.empty:
            for _, r in df.iterrows():
                if st.button(f"💰 Hak Edişe Gönder: {r['title']}", key=f"tt_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    # --- SAHA PERSONELİ EKRANLARI ---
    elif cp == "📜 Çalışmalarım":
        st.header("📜 Tüm Çalışmalarım")
        df = pd.read_sql(f"SELECT title, city, status, result_type, updated_at FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type IS NOT NULL", conn)
        df = advanced_filter(df, "calismalarim", "Henüz bir çalışma kaydınız bulunmamaktadır")
        if not df.empty:
            st.dataframe(df, use_container_width=True)

    elif cp == "🎒 Zimmetim":
        st.header("🎒 Üzerimdeki Zimmetli Eşyalar")
        df = pd.read_sql(f"SELECT item_name, quantity, updated_by FROM inventory WHERE assigned_to='{st.session_state.u_email}'", conn)
        # Zimmet ekranı tablo olduğu için filtreleme yerine doğrudan kontrol yapıyoruz
        if df.empty:
            st.info("ℹ️ Üzerinizde zimmetli herhangi bir eşya bulunmamaktadır.")
        else:
            st.table(df)

    # (Geri kalan form ve fonksiyon yapıları v46 ile aynıdır...)
