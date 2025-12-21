import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import io
import json
import os

# Plotly kütüphanesini güvenli bir şekilde içe aktaralım
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. AYARLAR VE STORAGE ---
UPLOAD_DIR = "uploaded_photos"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kırıkkale", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Şanlıurfa", "Siirt", "Sinop", "Sivas", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak"]

# --- 2. VERİTABANI YÖNETİMİ ---
def get_db():
    return sqlite3.connect('operasyon_v50.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT, phone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, assigned_to TEXT, title TEXT, description TEXT, status TEXT, report TEXT, photos_json TEXT, updated_at TEXT, city TEXT, result_type TEXT, ret_sebebi TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, assigned_to TEXT, quantity INTEGER, updated_by TEXT)''')
    
    pw = hashlib.sha256('1234'.encode()).hexdigest()
    users = [
        ('admin@sirket.com', pw, 'Admin', 'Sistem Yöneticisi', '0555'),
        ('filiz@deneme.com', pw, 'Müdür', 'Filiz Hanım', '0555'),
        ('dogukan@deneme.com', pw, 'Saha Personeli', 'Doğukan Gürol', '0555')
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", u)
    conn.commit()

init_db()

# --- 3. YARDIMCI FONKSİYONLAR ---
def to_excel(df):
    if df.empty:
        return None
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Rapor')
        return output.getvalue()
    except Exception as e:
        st.error(f"Excel oluşturma hatası: {e}")
        return None

def create_gauge(value, title):
    if not PLOTLY_AVAILABLE:
        return f"{title}: %{value}"
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title, 'font': {'size': 16}},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "darkblue"}}
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# --- 4. ANA DÖNGÜ VE FİLTRELEME ---
# (Uygulamanın geri kalanı v49 ile aynı akışta, ancak veri boşsa Excel butonu gösterilmeyecek şekilde revize edildi)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

# Giriş ekranı ve sidebar kodları buraya gelecek...
# Önemli: Görseldeki hatayı alan Excel butonu kısmını şu şekilde güncelledim:

def safe_download_button(df, key):
    excel_data = to_excel(df)
    if excel_data:
        st.download_button("📊 Excel İndir", excel_data, f"rapor_{key}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"btn_{key}")
    else:
        st.warning("İndirilecek veri bulunamadı.")
