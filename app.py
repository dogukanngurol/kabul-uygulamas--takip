import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os
import plotly.graph_objects as go

# --- 1. AYARLAR VE STORAGE ---
UPLOAD_DIR = "uploaded_photos"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]

# --- 2. VERİTABANI YÖNETİMİ ---
def get_db():
    conn = sqlite3.connect('operasyon_v49.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    # Varsayılan Kullanıcılar
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Sistem Yöneticisi', '0555'),
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
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

def create_gauge(value, title):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 16}},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 85], 'color': "gray"}]}))
    fig.update_layout(height=180, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def advanced_filter(df, key_suffix, empty_msg="Gösterilecek Veri Bulunmamaktadır"):
    st.write("### 🔍 Filtreler")
    c1, c2, c3, c4 = st.columns(4)
    
    p_list = ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"]
    p_filter = c1.selectbox("Personel", p_list, key=f"p_{key_suffix}")
    c_filter = c2.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"c_{key_suffix}")
    
    d_list = ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler"]
    if st.session_state.u_role in ['Admin', 'Müdür']:
        d_list += ["Türk Telekom Onayında", "Hak Ediş Bekleyen", "Hak Ediş Alındı"]
    d_filter = c3.selectbox("Durum", d_list, key=f"d_{key_suffix}")
    t_filter = c4.date_input("Tarih Aralığı", [], key=f"t_{key_suffix}")

    f_df = df.copy()
    if not f_df.empty:
        if p_filter != "Hepsi": f_df = f_df[f_df['assigned_to'] == p_filter]
        if c_filter != "Hepsi": f_df = f_df[f_df['city'] == c_filter]
        
        if d_filter == "Tamamlanan İşler": f_df = f_df[f_df['result_type'] == "İŞ TAMAMLANDI"]
        elif d_filter == "Tamamlanamayan İşler": f_df = f_df[f_df['result_type'].isin(["GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"])]
        elif d_filter != "Hepsi": f_df = f_df[f_df['status'] == d_filter]
        
        if not f_df.empty:
            st.download_button("📊 Excel Olarak İndir", to_excel(f_df), f"{key_suffix}.xlsx", key=f"dl_{key_suffix}")
    
    if f_df.empty:
        st.info(f"ℹ️ {empty_msg}")
        return pd.DataFrame()
    return f_df

# --- 4. OTURUM VE GİRİŞ ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🛡️ Saha Operasyon v49")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı Bilgiler")
else:
    # Karşılama Mesajı
    hr = datetime.now().hour
    msg = "Günaydın" if 8<=hr<12 else "İyi Günler" if 12<=hr<18 else "İyi Akşamlar" if 18<=hr<24 else "İyi Geceler"
    st.sidebar.markdown(f"### {msg}, {st.session_state.u_name} \n İyi Çalışmalar")

    # Menü Yapısı
    if st.session_state.u_role in ['Admin', 'Müdür']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler Takip", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- Üst Göstergeler (Gauges) ---
    if st.session_state.u_role in ['Admin', 'Müdür']:
        g1, g2, g3 = st.columns(3)
        # Örnek hesaplama (Gerçek veriye bağlanabilir)
        g1.plotly_chart(create_gauge(75, "Günlük Plan"), use_container_width=True)
        g2.plotly_chart(create_gauge(60, "Haftalık Plan"), use_container_width=True)
        g3.plotly_chart(create_gauge(45, "Aylık Plan"), use_container_width=True)

    # --- ANA SAYFA ---
    if cp == "🏠 Ana Sayfa":
        st.header("📊 Operasyonel Durum")
        c1, c2, c3 = st.columns(3)
        if st.session_state.u_role in ['Admin', 'Müdür']:
            c1.metric("Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Atanmış Bekleyenler", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            c3.metric("Haftalık Toplam İş", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", (week_ago,)).fetchone()[0])
        else:
            c1.metric("Tamamladığım İşler", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Üzerimdeki İşler", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status='Bekliyor'").fetchone()[0])

    # --- İŞ ATAMA ---
    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        p_list = pd.read_sql("SELECT email FROM users WHERE role = 'Saha Personeli'", conn)['email'].tolist()
        with st.form("task_add"):
            t1 = st.text_input("İş Başlığı")
            t2 = st.selectbox("Saha Personeli", p_list)
            t3 = st.selectbox("Şehir", ILLER)
            t4 = st.text_area("Açıklama")
            if st.form_submit_button("Atama Yap"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city, created_at) VALUES (?,?,?,?,?,?)", (t2, t1, t4, 'Bekliyor', t3, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.success("İş atandı."); st.rerun()

    # --- ATANAN İŞLERİM (PERSONEL VE TASLAK) ---
    elif cp == "⏳ Atanan İşlerim":
        st.header("⏳ Atanan İşlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor', 'Kabul Yapılabilir', 'Ret Edildi')", conn)
        
        if tasks.empty:
            st.info("Gösterilecek Atanmış İş Bulunmamaktadır")
        
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']} {'(🔴 RET)' if r['status'] == 'Ret Edildi' else ''}"):
                if r['ret_sebebi']: st.error(f"Ret Sebebi: {r['ret_sebebi']}")
                
                # Taslak Yönetimi
                res_list = ["Seçiniz", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"]
                res_idx = res_list.index(r['result_type']) if r['result_type'] in res_list else 0
                
                res = st.selectbox("Durum Seçin", res_list, index=res_idx, key=f"res_{r['id']}")
                rep = st.text_area("Rapor / Notlar", value=r['report'] if r['report'] else "", key=f"rep_{r['id']}")
                fots = st.file_uploader("Dosya/Fotoğraf Ekle", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                if c1.button("💾 Kaydet (Taslak)", key=f"save_{r['id']}"):
                    p_json = r['photos_json']
                    if fots:
                        new_files = []
                        for i, f in enumerate(fots):
                            fn = f"task_{r['id']}_{datetime.now().strftime('%H%M%S')}_{i}.jpg"
                            with open(os.path.join(UPLOAD_DIR, fn), "wb") as file: file.write(f.getbuffer())
                            new_files.append(fn)
                        p_json = json.dumps(new_files)
                    conn.execute("UPDATE tasks SET report=?, result_type=?, photos_json=? WHERE id=?", (rep, res, p_json, r['id']))
                    conn.commit(); st.success("Taslak Kaydedildi.")

                if c2.button("🚀 İşi Gönder", type="primary", key=f"send_{r['id']}"):
                    stt = 'Giriş Mail Onayı Bekler' if res == 'Giriş Mail Onayı Bekler' else 'Onay Bekliyor'
                    conn.execute("UPDATE tasks SET status=?, report=?, result_type=?, updated_at=? WHERE id=?", (stt, rep, res, datetime.now().strftime("%Y-%m-%d %H:%M"), r['id']))
                    conn.commit(); st.success("İş Gönderildi."); st.rerun()

    # --- TAMAMLANAN İŞLER ---
    elif cp == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Arşivi")
        df = pd.read_sql("SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Giriş Mail Onayı Bekler', 'Onay Bekliyor')", conn)
        df = advanced_filter(df, "arsiv", "Gösterilecek Tamamlanmış İş Bulunmamaktadır")
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            for _, r in df.iterrows():
                with st.expander(f"Detay: {r['title']}"):
                    # Fotoğraflar
                    if r['photos_json']:
                        cols = st.columns(4)
                        for i, fn in enumerate(json.loads(r['photos_json'])):
                            cols[i%4].image(os.path.join(UPLOAD_DIR, fn))
                    
                    c1, c2, c3 = st.columns(3)
                    if c1.button("📡 Türk Telekom Onay Bekleniyor", key=f"ttb_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                    
                    ret_txt = st.text_input("Ret Sebebi", key=f"ret_in_{r['id']}")
                    if c2.button("✅ Kabul", key=f"kab_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                    if c3.button("❌ Ret", key=f"ret_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Ret Edildi', ret_sebebi=? WHERE id=?", (ret_txt, r['id'])); conn.commit(); st.rerun()

    # --- HAK EDİŞ ---
    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Paneli")
        df = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleyen', 'Hak Edişi Alındı')", conn)
        df = advanced_filter(df, "hakedis", "Gösterilecek Hak Ediş Bulunmamaktadır")
        if not df.empty:
            st.dataframe(df)
            for _, r in df.iterrows():
                if r['status'] == 'Hak Ediş Bekleyen' and st.button(f"Hak Ediş Alındı: {r['title']}"):
                    conn.execute("UPDATE tasks SET status='Hak Edişi Alındı' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    # --- PROFİL VE GÜVENLİK ---
    elif cp == "👤 Profilim":
        st.header("👤 Profil Ayarları")
        with st.form("prof_up"):
            u = conn.execute("SELECT phone, email FROM users WHERE email=?", (st.session_state.u_email,)).fetchone()
            new_mail = st.text_input("E-posta", value=u[1])
            new_phone = st.text_input("Telefon", value=u[0])
            if st.form_submit_button("Güncellemeleri Kaydet"):
                if st.session_state.u_role != 'Müdür':
                    conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (new_mail, new_phone, st.session_state.u_email))
                    conn.commit(); st.success("Güncellendi."); st.rerun()
                else: st.warning("Müdür yetkilisi bilgileri kilitlidir.")
        
        with st.form("pass_up"):
            p1 = st.text_input("Yeni Şifre", type='password')
            p2 = st.text_input("Tekrar", type='password')
            if st.form_submit_button("Şifre Güncelle"):
                if p1 == p2:
                    conn.execute("UPDATE users SET password=? WHERE email=?", (hashlib.sha256(p1.encode()).hexdigest(), st.session_state.u_email))
                    conn.commit(); st.success("Şifre Değişti.")

    # --- ZİMMET ---
    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Zimmet & Envanter")
        if st.session_state.u_role in ['Admin', 'Müdür']:
            with st.expander("➕ Zimmet Ekle"):
                with st.form("zim_add"):
                    z1 = st.text_input("Malzeme"); z2 = st.selectbox("Personel", pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist()); z3 = st.number_input("Adet", 1)
                    if st.form_submit_button("Zimmetle"):
                        conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (z1, z2, z3, st.session_state.u_name))
                        conn.commit(); st.rerun()
        
        df_inv = pd.read_sql("SELECT * FROM inventory", conn)
        df_inv = advanced_filter(df_inv, "inv", "Kayıtlı Zimmet Bulunmamaktadır")
        if not df_inv.empty: st.table(df_inv)

    # --- KULLANICI YÖNETİMİ ---
    elif cp == "👥 Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        u_df = pd.read_sql("SELECT name, email, role, phone FROM users", conn)
        st.dataframe(u_df)
        with st.expander("➕ Ekle / ❌ Sil"):
            c1, c2 = st.columns(2)
            with c1:
                with st.form("u_add"):
                    un = st.text_input("Ad"); ue = st.text_input("E-posta"); up = st.text_input("Şifre"); ur = st.selectbox("Rol", ["Saha Personeli", "Müdür", "Admin"])
                    if st.form_submit_button("Ekle"):
                        conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (ue, hashlib.sha256(up.encode()).hexdigest(), ur, un, ""))
                        conn.commit(); st.rerun()
            with c2:
                sel_u = st.selectbox("Sil", u_df['email'].tolist())
                if st.button("Kullanıcıyı Sil"):
                    conn.execute("DELETE FROM users WHERE email=?", (sel_u,))
                    conn.commit(); st.rerun()

    # --- ÇALIŞMALARIM VE DİĞERLERİ ---
    elif cp == "📜 Çalışmalarım":
        st.header("📜 Tüm Çalışmalarım")
        df = pd.read_sql(f"SELECT title, city, status, result_type, updated_at FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type IS NOT NULL", conn)
        df = advanced_filter(df, "my_work", "Henüz bir çalışma kaydınız bulunmamaktadır")
        if not df.empty: st.dataframe(df)

    elif cp == "🎒 Zimmetim":
        st.header("🎒 Üzerimdeki Zimmet")
        df = pd.read_sql(f"SELECT item_name, quantity, updated_by FROM inventory WHERE assigned_to='{st.session_state.u_email}'", conn)
        if df.empty: st.info("Zimmetli Eşya Bulunmamaktadır")
        else: st.table(df)

    elif cp == "📋 Atanan İşler Takip":
        st.header("📋 Atanan İşler Takip")
        df = pd.read_sql("SELECT assigned_to, title, status, city FROM tasks WHERE status IN ('Bekliyor', 'Kabul Yapılabilir', 'Ret Edildi')", conn)
        df = advanced_filter(df, "takip", "Aktif Atanmış İş Bulunmamaktadır")
        if not df.empty: st.dataframe(df)
