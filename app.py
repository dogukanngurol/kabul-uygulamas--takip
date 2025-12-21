import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- GÖRSEL HATALARI ENGELLEMEK İÇİN KORUMA ---
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. AYARLAR VE STORAGE ---
UPLOAD_DIR = "saha_fotograflari"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]

# --- 2. VERİTABANI YÖNETİMİ ---
def get_db():
    return sqlite3.connect('saha_v53.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    # 1. KULLANICI TİPLERİ VE HESAPLAR
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    # 14. VERİTABANI OPTİMİZASYONU (photos_json URL/Path saklar)
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Admin', '0555'),
        ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '0555'),
        ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', '0555'),
        ('doguscan@deneme.com', pw, 'Saha Personeli', 'Doğuşcan Gürol', '0555'),
        ('cuneyt@deneme.com', pw, 'Saha Personeli', 'Cüneyt Bey', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. YARDIMCI FONKSİYONLAR ---
def to_excel(df):
    if df.empty: return None
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def create_gauge(value, title):
    if not PLOTLY_AVAILABLE: return None
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = value,
        title = {'text': title, 'font': {'size': 14}},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "darkblue"}}
    ))
    fig.update_layout(height=150, margin=dict(l=10, r=10, t=30, b=10))
    return fig

def filter_ui(df, key_suffix):
    # 4. FİLTRELEME ALTYAPISI
    st.write("### 🔍 Filtreleme Paneli")
    c1, c2, c3, c4 = st.columns(4)
    t_f = c1.date_input("Tarih Aralığı", [], key=f"t_{key_suffix}")
    p_f = c2.selectbox("Personel", ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"], key=f"p_{key_suffix}")
    c_f = c3.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"c_{key_suffix}")
    
    d_opts = ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
    if st.session_state.u_role in ['Admin', 'Müdür']:
        d_opts += ["Türk Telekom Onayında", "Hak Ediş Bekleniyor", "Hak Ediş Alındı"]
    d_f = c4.selectbox("Durum", d_opts, key=f"d_{key_suffix}")
    
    f_df = df.copy()
    if not f_df.empty:
        if p_f != "Hepsi": f_df = f_df[f_df['assigned_to'] == p_f]
        if c_f != "Hepsi": f_df = f_df[f_df['city'] == c_f]
        if d_f != "Hepsi":
            if d_f in ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]:
                f_df = f_df[f_df['result_type'] == d_f]
            else:
                f_df = f_df[f_df['status'] == d_f]
    
    # 5. EXCEL İNDİRME ÖZELLİĞİ
    ex = to_excel(f_df)
    if ex: st.download_button("📥 Seçilenleri Excel Olarak İndir", ex, f"{key_suffix}.xlsx", key=f"dl_{key_suffix}")
    
    if f_df.empty:
        # 12. BOŞ EKRAN DAVRANIŞI
        st.warning("⚠️ Gösterilecek Tamamlanmış İş Bulunmamaktadır")
        return pd.DataFrame()
    return f_df

# --- 4. OTURUM VE GİRİŞ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🛡️ Saha Operasyon Sistemi")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş Yap"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı e-posta veya şifre!")
else:
    # 11. DİNAMİK KARŞILAMA MESAJI
    hr = datetime.now().hour
    if 8 <= hr < 12: greet = "Günaydın"
    elif 12 <= hr < 18: greet = "İyi Günler"
    elif 18 <= hr < 24: greet = "İyi Akşamlar"
    else: greet = "İyi Geceler"
    st.sidebar.markdown(f"#### {greet} {st.session_state.u_name} \n **İyi Çalışmalar**")

    # MENÜ TANIMLARI
    if st.session_state.u_role in ['Admin', 'Müdür']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler Takip", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # 13. GÖRSEL İLERLEME GÖSTERGELERİ (SOL ÜST)
    if PLOTLY_AVAILABLE:
        st.sidebar.markdown("---")
        st.sidebar.plotly_chart(create_gauge(75, "Günlük Plan %"), use_container_width=True)
        st.sidebar.plotly_chart(create_gauge(60, "Haftalık Plan %"), use_container_width=True)
        st.sidebar.plotly_chart(create_gauge(45, "Aylık Plan %"), use_container_width=True)

    # --- ANA SAYFA ---
    if cp == "🏠 Ana Sayfa":
        st.header("📊 Genel Durum")
        c1, c2, c3 = st.columns(3)
        if st.session_state.u_role in ['Admin', 'Müdür']:
            c1.metric("Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Bekleyen Atamalar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            c3.metric("Haftalık Toplam İş", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", (week_start,)).fetchone()[0])
        else:
            c1.metric("Tamamladığım İşler", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Üzerimdeki Atamalar", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status='Bekliyor'").fetchone()[0])

    # --- İŞ ATAMA ---
    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        # Müdür iş atama listesinde listelenmemeli
        pers_df = pd.read_sql("SELECT email, name FROM users WHERE role='Saha Personeli'", conn)
        with st.form("atama_form"):
            t_title = st.text_input("Müşteri / İş Başlığı")
            t_pers = st.selectbox("Görevlendirilecek Personel", pers_df['email'].tolist())
            t_city = st.selectbox("Şehir", ILLER)
            t_desc = st.text_area("İş Talimatları")
            if st.form_submit_button("✅ İşi Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city, created_at) VALUES (?,?,?,?,?,?)", (t_pers, t_title, t_desc, 'Bekliyor', t_city, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.success("İş başarıyla atandı."); st.rerun()

    # --- SAHA PERSONELİ: ATANAN İŞLERİM ---
    elif cp == "⏳ Atanan İşlerim":
        st.header("⏳ Atanan İşlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor', 'Ret Edildi')", conn)
        if tasks.empty: st.info("Şu an üzerinizde bekleyen bir iş bulunmamaktadır.")
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']} - {r['city']}"):
                if r['ret_sebebi']: st.error(f"RET SEBEBİ: {r['ret_sebebi']}")
                # 3. İŞ DURUM SEÇENEKLERİ
                res = st.selectbox("İş Durumu", ["Seçiniz", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"], key=f"res_{r['id']}")
                rep = st.text_area("Rapor / Notlar", value=r['report'] if r['report'] else "", key=f"rep_{r['id']}")
                files = st.file_uploader("Fotoğraf / Dosya Ekle", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                # 2. TASLAK SİSTEMİ
                if c1.button("💾 Kaydet (Taslak)", key=f"save_{r['id']}"):
                    p_json = r['photos_json']
                    if files:
                        f_list = []
                        for i, f in enumerate(files):
                            fn = f"T{r['id']}_F{i}_{datetime.now().strftime('%H%M%S')}.jpg"
                            with open(os.path.join(UPLOAD_DIR, fn), "wb") as file: file.write(f.getbuffer())
                            f_list.append(fn)
                        p_json = json.dumps(f_list)
                    conn.execute("UPDATE tasks SET report=?, result_type=?, photos_json=? WHERE id=?", (rep, res, p_json, r['id']))
                    conn.commit(); st.success("Taslak olarak saklandı.")
                
                if c2.button("🚀 İşi Gönder", type="primary", key=f"send_{r['id']}"):
                    if res == "Seçiniz": st.warning("Lütfen bir durum seçin.")
                    else:
                        stt = 'Giriş Onayı Bekliyor' if res == 'Giriş Mail Onayı Bekler' else 'Onay Bekliyor'
                        conn.execute("UPDATE tasks SET status=?, report=?, result_type=?, updated_at=? WHERE id=?", (stt, rep, res, datetime.now().strftime("%Y-%m-%d %H:%M"), r['id']))
                        conn.commit(); st.success("İş onaya gönderildi."); st.rerun()

    # --- TAMAMLANAN İŞLER ---
    elif cp == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Arşivi")
        all_df = pd.read_sql("SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Onayı Bekliyor', 'Onay Bekliyor')", conn)
        df = filter_ui(all_df, "arsiv")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            for _, r in df.iterrows():
                with st.expander(f"İncele: {r['title']}"):
                    # 7. TAMAMLANMIŞ İŞ DETAY
                    if r['photos_json']:
                        cols = st.columns(4)
                        for idx, img_p in enumerate(json.loads(r['photos_json'])):
                            cols[idx%4].image(os.path.join(UPLOAD_DIR, img_p))
                    
                    st.write(f"**Personel:** {r['assigned_to']} | **Şehir:** {r['city']} | **Sonuç:** {r['result_type']}")
                    st.write(f"**Rapor:** {r['report']}")
                    
                    c1, c2, c3 = st.columns(3)
                    if c1.button("📡 Türk Telekom Onay Bekleniyor", key=f"ttb_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                    
                    ret_msg = st.text_input("Ret Sebebi (Ret edilecekse zorunludur)", key=f"rm_{r['id']}")
                    if c2.button("✅ Kabul", key=f"ok_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                    if c3.button("❌ Ret", key=f"rj_{r['id']}"):
                        if ret_msg:
                            conn.execute("UPDATE tasks SET status='Ret Edildi', ret_sebebi=? WHERE id=?", (ret_msg, r['id'])); conn.commit(); st.rerun()
                        else: st.warning("Lütfen ret sebebi girin.")

    # --- ZİMMET VE ENVANTER ---
    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Zimmet & Envanter Yönetimi")
        if st.session_state.u_role in ['Admin', 'Müdür']:
            with st.expander("➕ Yeni Zimmet Tanımla"):
                with st.form("zimmet_form"):
                    z_name = st.text_input("Malzeme Adı")
                    z_pers = st.selectbox("Personel", pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist())
                    z_qty = st.number_input("Adet", 1)
                    if st.form_submit_button("Zimmet Kaydet"):
                        conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (z_name, z_pers, z_qty, st.session_state.u_name))
                        conn.commit(); st.success("Zimmetlendi."); st.rerun()
        
        inv_df = pd.read_sql("SELECT * FROM inventory", conn)
        # Admin Excel indirebilir
        if st.session_state.u_role == 'Admin':
            ex = to_excel(inv_df)
            if ex: st.download_button("📥 Tüm Envanteri Excel İndir", ex, "envanter.xlsx")
        
        st.dataframe(inv_df, use_container_width=True)

    # --- PROFİL VE GÜVENLİK ---
    elif cp == "👤 Profilim":
        st.header("👤 Profil ve Güvenlik")
        # Müdür harici güncelleme yapabilir
        is_disabled = True if st.session_state.u_role == 'Müdür' else False
        u_data = conn.execute("SELECT email, phone FROM users WHERE email=?", (st.session_state.u_email,)).fetchone()
        
        with st.form("profile_form"):
            new_mail = st.text_input("E-posta Adresi", value=u_data[0], disabled=is_disabled)
            new_phone = st.text_input("Telefon Numarası", value=u_data[1], disabled=is_disabled)
            if st.form_submit_button("💾 Güncellemeleri Kaydet"):
                conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (new_mail, new_phone, st.session_state.u_email))
                conn.commit(); st.success("Bilgiler güncellendi."); st.rerun()
        
        with st.form("password_form"):
            new_pw = st.text_input("Yeni Şifre", type='password')
            if st.form_submit_button("🔑 Şifreyi Değiştir"):
                conn.execute("UPDATE users SET password=? WHERE email=?", (hashlib.sha256(new_pw.encode()).hexdigest(), st.session_state.u_email))
                conn.commit(); st.success("Şifre başarıyla değiştirildi.")

    # --- KULLANICI YÖNETİMİ ---
    elif cp == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        u_df = pd.read_sql("SELECT name, email, role, phone FROM users", conn)
        st.dataframe(u_df, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1.expander("➕ Yeni Kullanıcı Ekle"):
            with st.form("new_u"):
                n_n = st.text_input("Ad Soyad")
                n_e = st.text_input("E-posta")
                n_p = st.text_input("Şifre", type='password')
                n_r = st.selectbox("Yetki", ["Saha Personeli", "Müdür", "Admin"])
                if st.form_submit_button("Ekle"):
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (n_e, hashlib.sha256(n_p.encode()).hexdigest(), n_r, n_n, ""))
                    conn.commit(); st.rerun()
        with c2.expander("❌ Kullanıcı Sil"):
            s_e = st.selectbox("Silinecek E-posta", u_df['email'].tolist())
            if st.button("🔴 Seçili Kullanıcıyı Sil"):
                if s_e != st.session_state.u_email:
                    conn.execute("DELETE FROM users WHERE email=?", (s_e,))
                    conn.commit(); st.success("Silindi."); st.rerun()
                else: st.error("Kendi hesabınızı silemezsiniz!")

    # --- HAK EDİŞ ---
    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş")
        h_df = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleyen', 'Hak Ediş Alındı')", conn)
        df = filter_ui(h_df, "hakedis")
        if not df.empty:
            for _, r in df.iterrows():
                if r['status'] == 'Hak Ediş Bekleyen' and st.button(f"Hak Ediş Alındı: {r['title']}", key=f"ha_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Alındı' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    # --- TT ONAY BEKLEYENLER ---
    elif cp == "📡 TT Onay Bekleyenler":
        st.header("📡 TT Onay Bekleyenler")
        tt_df = pd.read_sql("SELECT * FROM tasks WHERE status='Türk Telekom Onayında'", conn)
        df = filter_ui(tt_df, "tt_onay")
        if not df.empty:
            for _, r in df.iterrows():
                if st.button(f"💰 Hak Edişe Gönder: {r['title']}", key=f"het_{r['id']}"):
                    conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    # --- DİĞER EKRANLAR ---
    elif cp == "📋 Atanan İşler Takip":
        st.header("📋 Atanan İşler Takip")
        t_df = pd.read_sql("SELECT assigned_to, title, status, city FROM tasks WHERE status IN ('Bekliyor', 'Ret Edildi')", conn)
        st.dataframe(t_df, use_container_width=True)

    elif cp == "📜 Çalışmalarım":
        st.header("📜 Tüm Çalışmalarım")
        c_df = pd.read_sql(f"SELECT title, city, status, result_type, updated_at FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type IS NOT NULL", conn)
        st.dataframe(c_df, use_container_width=True)

    elif cp == "🎒 Zimmetim":
        st.header("🎒 Üzerimdeki Zimmet")
        z_df = pd.read_sql(f"SELECT item_name, quantity, updated_by FROM inventory WHERE assigned_to='{st.session_state.u_email}'", conn)
        if z_df.empty: st.info("Zimmetli eşyanız bulunmamaktadır.")
        else: st.table(z_df)
