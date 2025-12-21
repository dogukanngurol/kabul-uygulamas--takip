import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# --- 1. KURUMSAL AYARLAR ---
COMPANY_NAME = "Anatolia Bilişim"
ILLER = ["Adana", "Ankara", "Antalya", "Bursa", "İstanbul", "İzmir", "Konya", "Samsun"] # 81 il listesi buraya genişletilebilir.

# --- 2. VERİTABANI VE ŞEMA ---
def get_db():
    return sqlite3.connect('anatolia_v60.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    # Tanımlı Kullanıcılar (Madde 1)
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Admin Kullanıcı', '0555'),
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
def excel_export(df, key):
    if df is None or df.empty:
        st.warning("⚠️ Gösterilecek Tamamlanmış İş Bulunmamaktadır")
        return
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    st.download_button(label="📥 Excel Raporu Al", data=output.getvalue(), file_name=f"{key}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def get_greeting():
    hr = datetime.now().hour
    if 8 <= hr < 12: return "Günaydın"
    elif 12 <= hr < 18: return "İyi Günler"
    elif 18 <= hr < 24: return "İyi Akşamlar"
    else: return "İyi Geceler"

# --- 4. GİRİŞ VE OTURUM ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title(f"🏢 {COMPANY_NAME} Sistem Girişi")
    with st.form("login"):
        e = st.text_input("E-posta"); p = st.text_input("Şifre", type='password')
        if st.form_submit_button("Giriş"):
            conn = get_db()
            u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hashlib.sha256(p.encode()).hexdigest())).fetchone()
            if u:
                st.session_state.update({'logged_in':True, 'u_email':u[0], 'u_role':u[2], 'u_name':u[3], 'page':"🏠 Ana Sayfa"})
                st.rerun()
            else: st.error("Hatalı Giriş!")
else:
    # --- SIDEBAR TASARIMI (Madde 9) ---
    st.sidebar.markdown(f"### 🏢 {COMPANY_NAME}")
    st.sidebar.markdown(f"👤 **{st.session_state.u_name}**\n⭐ *{st.session_state.u_role}*")
    st.sidebar.divider()

    # Rol Bazlı Menü Yapılandırması
    role = st.session_state.u_role
    if role == 'Admin':
        menu = ["🏠 Ana Sayfa", "➕ İş Atama", "📋 Atanan İşler", "📨 Giriş Onayları", "📡 TT Onay Bekleyenler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi", "👤 Profilim"]
    elif role == 'Yönetici':
        menu = ["🏠 Ana Sayfa", "📋 Atanan İşler", "✅ Tamamlanan İşler", "💰 Hak Ediş", "👤 Profilim"]
    elif role == 'Müdür':
        menu = ["🏠 Ana Sayfa", "📡 TT Onay Bekleyenler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👤 Profilim"]
    else: # Saha Personeli
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşlerim", "📜 Çalışmalarım", "🎒 Zimmetim", "👤 Profilim"]

    for m in menu:
        is_active = "primary" if st.session_state.page == m else "secondary"
        if st.sidebar.button(m, use_container_width=True, type=is_active):
            st.session_state.page = m; st.rerun()

    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True):
        st.session_state.logged_in = False; st.rerun()

    conn = get_db()
    cp = st.session_state.page

    # --- 5. ORTAK FİLTRELEME (Madde 6) ---
    def apply_filters(query_base, filter_key):
        df = pd.read_sql(query_base, conn)
        st.write("### 🔍 Filtreler")
        c1, c2, c3, c4 = st.columns(4)
        with c1: f_tarih = st.date_input("Tarih", [], key=f"t_{filter_key}")
        with c2: f_pers = st.selectbox("Personel", ["Hepsi"] + sorted(df['assigned_to'].unique().tolist()) if not df.empty else ["Hepsi"], key=f"p_{filter_key}")
        with c3: f_sehir = st.selectbox("Şehir", ["Hepsi"] + ILLER, key=f"s_{filter_key}")
        
        d_opts = ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
        if st.session_state.u_role in ['Admin', 'Yönetici', 'Müdür']:
            d_opts += ["Türk Telekom Onayında", "Hak Ediş Bekleniyor", "Hak Ediş Alındı"]
        with c4: f_durum = st.selectbox("Durum", d_opts, key=f"d_{filter_key}")
        
        filtered = df.copy()
        if not filtered.empty:
            if f_pers != "Hepsi": filtered = filtered[filtered['assigned_to'] == f_pers]
            if f_sehir != "Hepsi": filtered = filtered[filtered['city'] == f_sehir]
            if f_durum != "Hepsi":
                if f_durum in ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]:
                    filtered = filtered[filtered['result_type'] == f_durum]
                else: filtered = filtered[filtered['status'] == f_durum]
        
        excel_export(filtered, filter_key)
        return filtered

    # --- 6. SAYFA İÇERİKLERİ ---
    if cp == "🏠 Ana Sayfa":
        st.header(f"📊 {get_greeting()}, {st.session_state.u_name}")
        if role in ['Admin', 'Yönetici']:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tamamlanan İşler", conn.execute("SELECT COUNT(*) FROM tasks WHERE result_type='İŞ TAMAMLANDI'").fetchone()[0])
            c2.metric("Bekleyen Atamalar", conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Bekliyor'").fetchone()[0])
            c3.metric("Haftalık Toplam", conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= ?", ((datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d"),)).fetchone()[0])

    elif cp == "👥 Kullanıcı Yönetimi" and role == 'Admin':
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı Tanımla"):
            with st.form("new_user"):
                e = st.text_input("E-posta"); n = st.text_input("İsim"); t = st.text_input("Telefon")
                r = st.selectbox("Rol", ["Saha Personeli", "Yönetici", "Müdür", "Admin"])
                p = st.text_input("Şifre", type='password')
                if st.form_submit_button("Kaydet"):
                    hp = hashlib.sha256(p.encode()).hexdigest()
                    conn.execute("INSERT INTO users VALUES (?,?,?,?,?)", (e, hp, r, n, t))
                    conn.commit(); st.success("Kullanıcı Eklendi"); st.rerun()
        
        u_list = pd.read_sql("SELECT email, name, role, phone FROM users", conn)
        st.dataframe(u_list, use_container_width=True)

    elif cp == "➕ İş Atama" and role == 'Admin':
        st.header("➕ Yeni İş Atama")
        # Müdür listelenmez (Madde 1)
        pers_list = pd.read_sql("SELECT email FROM users WHERE role IN ('Saha Personeli', 'Yönetici')", conn)['email'].tolist()
        with st.form("atama"):
            title = st.text_input("Başlık"); p = st.selectbox("Personel", pers_list); s = st.selectbox("Şehir", ILLER)
            if st.form_submit_button("Ata"):
                conn.execute("INSERT INTO tasks (assigned_to, title, status, city, created_at) VALUES (?,?,?,?,?)", (p, title, 'Bekliyor', s, datetime.now().strftime("%Y-%m-%d")))
                conn.commit(); st.success("İş Atandı")

    elif cp == "⏳ Atanan İşlerim":
        st.header("⏳ Üzerimdeki İşler")
        # Taslak Sistemi (Madde 5)
        my_tasks = pd.read_sql(f"SELECT * FROM tasks WHERE assigned_to='{st.session_state.u_email}' AND status IN ('Bekliyor', 'Ret Edildi')", conn)
        if my_tasks.empty: st.info("Gösterilecek Tamamlanmış İş Bulunmamaktadır")
        else:
            for _, r in my_tasks.iterrows():
                with st.expander(f"📌 {r['title']} ({r['city']})"):
                    st.selectbox("Durum Seçiniz", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"], key=f"res_{r['id']}")
                    st.text_area("Notlar", value=r['report'] if r['report'] else "", key=f"not_{r['id']}")
                    if st.button("💾 Kaydet (Taslak)", key=f"tas_{r['id']}"):
                        st.success("Taslak Kaydedildi")
                    if st.button("🚀 İşi Gönder", type="primary", key=f"gön_{r['id']}"):
                        conn.execute("UPDATE tasks SET status='Onay Bekliyor' WHERE id=?", (r['id'],)); conn.commit(); st.rerun()

    elif cp == "👤 Profilim":
        st.header("👤 Profil Ayarları")
        u = conn.execute("SELECT email, phone, name FROM users WHERE email=?", (st.session_state.u_email,)).fetchone()
        with st.form("p_update"):
            new_mail = st.text_input("E-posta", u[0]); new_phone = st.text_input("Telefon", u[1])
            new_pass = st.text_input("Yeni Şifre (Değişmeyecekse boş bırakın)", type='password')
            if st.form_submit_button("💾 Güncelle"):
                if new_pass:
                    hp = hashlib.sha256(new_pass.encode()).hexdigest()
                    conn.execute("UPDATE users SET email=?, phone=?, password=? WHERE email=?", (new_mail, new_phone, hp, st.session_state.u_email))
                else:
                    conn.execute("UPDATE users SET email=?, phone=? WHERE email=?", (new_mail, new_phone, st.session_state.u_email))
                conn.commit(); st.success("Profil Güncellendi")

    # Filtre Altyapılı Rapor Ekranları
    elif cp == "✅ Tamamlanan İşler":
        st.header("✅ Tamamlanan İş Arşivi")
        df = apply_filters("SELECT * FROM tasks WHERE status NOT IN ('Bekliyor', 'Ret Edildi')", "tamamlananlar")
        if not df.empty: st.dataframe(df, use_container_width=True)

    elif cp == "💰 Hak Ediş":
        st.header("💰 Hak Ediş Raporu")
        df = apply_filters("SELECT * FROM tasks WHERE status IN ('Hak Ediş Bekleyen', 'Hak Ediş Alındı')", "hakedis")
        if not df.empty: st.dataframe(df, use_container_width=True)
