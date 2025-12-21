import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- GÖRSEL VE KÜTÜPHANE KONTROLÜ ---
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 13. FOTOĞRAF VE VERİTABANI OPTİMİZASYONU ---
UPLOAD_DIR = "saha_dosyalari"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]

# --- VERİTABANI BAŞLATMA ---
def get_db():
    return sqlite3.connect('operasyon_v55.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    # 1. KULLANICI TANIMLARI
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    # 2. İŞ VE TASLAK YÖNETİMİ
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    # 9. ZİMMET
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

# --- EXCEL RAPORLAMA MOTORU ---
def excel_indir(df, dosya_adi):
    if df.empty:
        return None
    output = io.BytesIO()
    # xlsxwriter motoru ile güvenli oluşturma
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

# --- 11. DİNAMİK KARŞILAMA ---
def get_greeting(name):
    hr = datetime.now().hour
    if 8 <= hr < 12: msg = "Günaydın"
    elif 12 <= hr < 18: msg = "İyi Günler"
    elif 18 <= hr < 24: msg = "İyi Akşamlar"
    else: msg = "İyi Geceler"
    return f"**{msg} {name}**, İyi Çalışmalar"

# --- 5. FİLTRELEME ALTYAPISI (GENEL) ---
def apply_filters(df, key_prefix):
    st.write("### 🔍 Filtreleme Paneli")
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_tarih = st.date_input("Tarih", [], key=f"{key_prefix}_t")
    with c2: f_pers = st.selectbox("Personel", ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"], key=f"{key_prefix}_p")
    with c3: f_sehir = st.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"{key_prefix}_s")
    
    d_opts = ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
    if st.session_state.u_role in ['Admin', 'Müdür']:
        d_opts += ["Türk Telekom Onayında", "Hak Ediş Bekleniyor", "Hak Ediş Alındı"]
    with c4: f_durum = st.selectbox("Durum", d_opts, key=f"{key_prefix}_d")
    
    res_df = df.copy()
    if not res_df.empty:
        if f_pers != "Hepsi": res_df = res_df[res_df['assigned_to'] == f_pers]
        if f_sehir != "Hepsi": res_df = res_df[res_df['city'] == f_sehir]
        if f_durum != "Hepsi":
            if f_durum in ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]:
                res_df = res_df[res_df['result_type'] == f_durum]
            else:
                res_df = res_df[res_df['status'] == f_durum]
    
    # EXCEL BUTONU
    ex_data = excel_indir(res_df, key_prefix)
    if ex_data:
        st.download_button(label="📥 Excel Raporu İndir", data=ex_data, file_name=f"{key_prefix}_rapor.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"{key_prefix}_btn")
    elif not res_df.empty:
        st.info("Excel hazırlanıyor...")
    
    # 12. BOŞ EKRAN DAVRANIŞI
    if res_df.empty:
        st.warning("⚠️ Gösterilecek Tamamlanmış İş Bulunmamaktadır")
        return pd.DataFrame()
    return res_df

# --- ARAYÜZ VE OTURUM ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🛡️ Saha Operasyon v55")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı Giriş")
else:
    st.sidebar.markdown(get_greeting(st.session_state.u_name))
    
    # MENÜ YETKİLERİ
    if st.session_state.u_role in ['Admin', 'Müdür']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcılar"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]
    
    for m in menu:
        if st.sidebar.button(m, use_container_width=True): st.session_state.page = m; st.rerun()
    if st.sidebar.button("🔴 ÇIKIŞ"): st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- EKRANLAR ---
    if cp == "🏠 Ana Sayfa":
        st.header("🏠 Anasayfa")
        c1, c2, c3 = st.columns(3)
        if st.session_state.u_role in ['Admin', 'Müdür']:
            c1.metric("Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Bekleyen Atamalar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            c3.metric("Haftalık İş Sayısı", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", ((datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d"),)).fetchone()[0])
        else:
            c1.metric("Tamamladığım", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Üzerimdeki İş", conn.execute(f"SELECT COUNT(*) FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status='Bekliyor'").fetchone()[0])

    elif cp == "➕ İş Atama":
        st.header("➕ Yeni İş Atama")
        # Müdür listede olmayacak
        p_df = pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)
        with st.form("atama"):
            t = st.text_input("İş Başlığı")
            p = st.selectbox("Personel", p_df['email'].tolist())
            s = st.selectbox("Şehir", ILLER)
            d = st.text_area("Açıklama")
            if st.form_submit_button("Atama Yap"):
                conn.execute("INSERT INTO tasks (assigned_to, title, description, status, city, created_at) VALUES (?,?,?,?,?,?)", (p, t, d, 'Bekliyor', s, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.success("İş Atandı")

    elif cp == "⏳ Atanan İşlerim":
        st.header("⏳ Atanan İşlerim")
        tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor', 'Ret Edildi')", conn)
        for _, r in tasks.iterrows():
            with st.expander(f"📋 {r['title']} - {r['city']}"):
                # 3. DURUM SEÇENEKLERİ
                res = st.selectbox("Sonuç Durumu", ["Seçiniz", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR", "Giriş Mail Onayı Bekler"], key=f"r_{r['id']}")
                rep = st.text_area("Rapor", value=r['report'] if r['report'] else "", key=f"rep_{r['id']}")
                fots = st.file_uploader("Dosya/Fotoğraf", accept_multiple_files=True, key=f"f_{r['id']}")
                
                c1, c2 = st.columns(2)
                # 2. TASLAK SİSTEMİ
                if c1.button("💾 Kaydet (Taslak)", key=f"ts_{r['id']}"):
                    p_json = r['photos_json']
                    if fots:
                        f_list = []
                        for idx, f in enumerate(fots):
                            fn = f"T{r['id']}_{idx}.jpg"
                            with open(os.path.join(UPLOAD_DIR, fn), "wb") as file: file.write(f.getbuffer())
                            f_list.append(fn)
                        p_json = json.dumps(f_list)
                    conn.execute("UPDATE tasks SET report=?, result_type=?, photos_json=? WHERE id=?", (rep, res, p_json, r['id']))
                    conn.commit(); st.success("Taslak Kaydedildi")
                
                if c2.button("🚀 İşi Gönder", type="primary", key=f"g_{r['id']}"):
                    stt = 'Giriş Onayı Bekliyor' if res == 'Giriş Mail Onayı Bekler' else 'Onay Bekliyor'
                    conn.execute("UPDATE tasks SET status=?, report=?, result_type=?, updated_at=? WHERE id=?", (stt, rep, res, datetime.now().strftime("%Y-%m-%d %H:%M"), r['id']))
                    conn.commit(); st.success("İş Gönderildi"); st.rerun()

    elif cp == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Arşivi")
        # 4. FİLTRE MANTIĞI
        raw_df = pd.read_sql("SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Onay Bekliyor')", conn)
        df = apply_filters(raw_df, "tamamlanan")
        if not df.empty:
            st.dataframe(df)
            for _, r in df.iterrows():
                with st.expander(f"Detay: {r['title']}"):
                    # 7. DETAY EKRANI
                    if r['photos_json']:
                        cols = st.columns(4)
                        for i, img in enumerate(json.loads(r['photos_json'])):
                            cols[i%4].image(os.path.join(UPLOAD_DIR, img))
                    
                    c1, c2, c3 = st.columns(3)
                    if c1.button("📡 TT Onay Bekleniyor", key=f"tt_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Türk Telekom Onayında' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                    
                    ret_seb = st.text_input("Ret Sebebi", key=f"rs_{r['id']}")
                    if c2.button("✅ Kabul", key=f"kb_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Hak Ediş Bekleyen' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()
                    if c3.button("❌ Ret", key=f"rt_{r['id']}"):
                        if ret_seb:
                            conn.execute("UPDATE tasks SET status='Ret Edildi', ret_sebebi=? WHERE id=?", (ret_seb, r['id'])); conn.commit(); st.rerun()
                        else: st.warning("Ret sebebi giriniz")

    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Raporu")
        h_df = pd.read_sql("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleyen', 'Hak Ediş Alındı')", conn)
        df = apply_filters(h_df, "hakedis")
        if not df.empty:
            st.dataframe(df)

    elif cp == "👤 Profilim":
        st.header("👤 Profil Ayarları")
        u = conn.execute("SELECT email, phone FROM users WHERE email=?", (st.session_state.u_email,)).fetchone()
        # Müdür harici güncelleme yapabilir
        dis = True if st.session_state.u_role == 'Müdür' else False
        with st.form("p_g"):
            n_m = st.text_input("E-posta", value=u[0], disabled=dis)
            n_p = st.text_input("Telefon", value=u[1], disabled=dis)
            if st.form_submit_button("Güncellemeleri Kaydet"):
                conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (n_m, n_p, st.session_state.u_email))
                conn.commit(); st.success("Kaydedildi")
        
        with st.form("s_d"):
            n_pw = st.text_input("Yeni Şifre", type='password')
            if st.form_submit_button("Şifre Değiştir"):
                conn.execute("UPDATE users SET password=? WHERE email=?", (hashlib.sha256(n_pw.encode()).hexdigest(), st.session_state.u_email))
                conn.commit(); st.success("Şifre Değişti")

    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Envanter")
        if st.session_state.u_role in ['Admin', 'Müdür']:
            with st.expander("Yeni Zimmet"):
                with st.form("z"):
                    m = st.text_input("Malzeme")
                    p = st.selectbox("Personel", pd.read_sql("SELECT email FROM users WHERE role='Saha Personeli'", conn)['email'].tolist())
                    a = st.number_input("Adet", 1)
                    if st.form_submit_button("Zimmetle"):
                        conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)", (m, p, a, st.session_state.u_name))
                        conn.commit(); st.rerun()
        
        z_df = pd.read_sql("SELECT * FROM inventory", conn)
        if st.session_state.u_role == 'Admin':
            ex = excel_indir(z_df, "envanter")
            if ex: st.download_button("📥 Envanter Excel", ex, "envanter.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.dataframe(z_df)
