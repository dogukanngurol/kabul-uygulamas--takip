import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import io
import json
import zipfile

# --- 1. VERİTABANI ---
def init_db():
    conn = sqlite3.connect('saha_operasyon_v31.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, title TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, 
                  description TEXT, status TEXT, report TEXT, photos_json TEXT, 
                  updated_at TEXT, city TEXT, result_type TEXT, hakedis_durum TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, 
                  assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- 2. YARDIMCI ARAÇLAR ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

# --- 3. ARAYÜZ ---
st.set_page_config(page_title="Saha Operasyon v31", layout="wide")

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
    if st.session_state['user_title'] in ['Müdür', 'Genel Müdür', 'admin']:
        menu = ["🏠 Ana Sayfa", "➕ İş Atama & Takip", "📨 Giriş Onayları", "✅ Tamamlanan İşler", "💰 Hak Ediş", "📦 Zimmet & Envanter", "👥 Kullanıcı Yönetimi"]
    else:
        menu = ["🏠 Ana Sayfa", "⏳ Atanan İşler", "📜 Çalışma Geçmişim", "🎒 Zimmetim", "👤 Profilim"]
    
    for item in menu:
        if st.sidebar.button(item, use_container_width=True): st.session_state.page = item
    
    if st.sidebar.button("🔴 ÇIKIŞ", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    cp = st.session_state.page

    # --- DÜZELTİLEN SAYFA: ÇALIŞMA GEÇMİŞİM ---
    if cp == "📜 Çalışma Geçmişim":
        st.header("📜 Kişisel Çalışma Geçmişim")
        # Sadece bu çalışana ait ve 'Bekliyor' olmayan (gönderilmiş/onaylanmış) işleri getir
        my_history = pd.read_sql(f"""
            SELECT id, title, city, result_type, status, updated_at 
            FROM tasks 
            WHERE assigned_to='{st.session_state['user_email']}' 
            AND status NOT IN ('Bekliyor', 'Kabul Yapılabilir')
        """, conn)
        
        if my_history.empty:
            st.info("Henüz tamamlanmış bir işiniz bulunmuyor.")
        else:
            st.dataframe(my_history, use_container_width=True)

    # --- DÜZELTİLEN SAYFA: ZİMMETİM (SAHA ÇALIŞANI) ---
    elif cp == "🎒 Zimmetim":
        st.header("🎒 Üzerimdeki Zimmetli Envanterler")
        # Sadece bu çalışana zimmetlenmiş ürünleri getir
        my_inv = pd.read_sql(f"SELECT item_name, quantity, updated_by FROM inventory WHERE assigned_to='{st.session_state['user_email']}'", conn)
        
        if my_inv.empty:
            st.warning("Üzerinize kayıtlı herhangi bir zimmet bulunamadı.")
        else:
            st.table(my_inv)

    # --- SAYFA: ZİMMET & ENVANTER (MÜDÜR/ADMİN) ---
    elif cp == "📦 Zimmet & Envanter":
        st.header("📦 Genel Envanter ve Zimmet Yönetimi")
        
        # Filtreleme (Müdür için tüm çalışanları görme)
        f_user = st.selectbox("Personel Filtrele", ["Hepsi"] + pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist())
        
        inv_query = "SELECT * FROM inventory"
        if f_user != "Hepsi":
            inv_query += f" WHERE assigned_to='{f_user}'"
        
        all_inv = pd.read_sql(inv_query, conn)
        st.dataframe(all_inv, use_container_width=True)
        
        if st.button("📊 Envanter Listesini Excel İndir"):
            st.download_button("Excel İndir", data=to_excel(all_inv), file_name="Envanter_Rapor.xlsx")

        with st.expander("➕ Yeni Zimmet Ekle"):
            with st.form("inv_form"):
                item = st.text_input("Malzeme Adı")
                target = st.selectbox("Personel E-posta", pd.read_sql("SELECT email FROM users WHERE role='worker'", conn)['email'].tolist())
                qty = st.number_input("Adet", min_value=1, value=1)
                if st.form_submit_button("Zimmetle"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to, quantity, updated_by) VALUES (?,?,?,?)",
                                 (item, target, qty, st.session_state['user_name']))
                    conn.commit(); st.success("Zimmet başarıyla eklendi."); st.rerun()

    # --- DİĞER SAYFALAR (v30 MANTIĞI İLE AYNI) ---
    elif cp == "🏠 Ana Sayfa":
        st.info(f"✨ Hoş Geldin **{st.session_state['user_name']}**")
        # Sayaçlar buraya gelecek...
