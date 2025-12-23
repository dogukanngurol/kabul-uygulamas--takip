import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# --- VERİTABANI VE OTURUM YÖNETİMİ ---
def init_db():
    conn = sqlite3.connect('anatoli_sistem.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, title TEXT, staff TEXT, city TEXT, detail TEXT, status TEXT, date TEXT, photos TEXT, note TEXT, is_draft INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, assigned_to TEXT)''')
    
    c.execute("SELECT * FROM users WHERE email='admin@anatoli.com'")
    if not c.fetchone():
        c.execute("INSERT INTO users (name, email, phone, password, role) VALUES (?,?,?,?,?)",
                  ('Doğukan Gürol', 'admin@anatoli.com', '5551234567', 'admin123', 'Admin'))
    conn.commit()
    return conn

conn = init_db()

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

CITIES = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"]

# --- GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.title("Anatoli Bilişim - Giriş")
    email = st.text_input("E-posta")
    pwd = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        u = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, pwd)).fetchone()
        if u:
            st.session_state.logged_in, st.session_state.user = True, {"id":u[0],"name":u[1],"email":u[2],"phone":u[3],"role":u[5]}
            st.rerun()
        else: st.error("Hatalı giriş.")
else:
    user = st.session_state.user
    st.sidebar.title("Anatoli Bilişim")
    st.sidebar.markdown(f"**{user['name']}**\n\n*{user['role']}*")
    
    all_tabs = ["Ana Sayfa", "İş Ataması", "Atanan İşler", "Giriş Onayları", "TT Onayı Bekleyenler", "Tamamlanan İşler", "Hak Ediş", "Zimmet & Envanter", "Kullanıcı Yönetimi", "Profilim", "Çıkış"]
    if user['role'] == "Saha Personeli":
        tabs = ["Ana Sayfa", "Üzerime Atanan İşler", "Tamamladığım İşler", "Zimmet & Envanter", "Profilim", "Çıkış"]
    elif user['role'] == "Müdür":
        tabs = ["Ana Sayfa", "İş Ataması", "Atanan İşler", "Giriş Onayları", "TT Onayı Bekleyenler", "Tamamlanan İşler", "Zimmet & Envanter", "Profilim", "Çıkış"]
    else:
        tabs = all_tabs

    choice = st.sidebar.radio("Menü", tabs)

    # --- ANA SAYFA ---
    if choice == "Ana Sayfa":
        h = datetime.now().hour
        msg = "Günaydın" if 8<=h<12 else "İyi Günler" if 12<=h<18 else "İyi Akşamlar" if 18<=h<23 else "İyi Geceler"
        st.header(f"{msg} {user['name']} İyi Çalışmalar")
        if user['role'] != "Saha Personeli":
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Günlük Tamamlanan", conn.execute("SELECT count(*) FROM jobs WHERE status='Kabul Alındı' AND date=?", (datetime.now().strftime("%Y-%m-%d"),)).fetchone()[0])
            c2.metric("Bekleyen Atamalar", conn.execute("SELECT count(*) FROM jobs WHERE status='Atandı'").fetchone()[0])
            c3.metric("Haftalık Tamamlanan", "15") 
            c4.metric("Aylık Tamamlanan", "60")
        else:
            st.write(f"Üzerime Atanan İşler: {conn.execute('SELECT count(*) FROM jobs WHERE staff=? AND status=?', (user['name'], 'Atandı')).fetchone()[0]}")
            st.write(f"Tamamladığım İşler: {conn.execute('SELECT count(*) FROM jobs WHERE staff=? AND status=?', (user['name'], 'Kabul Alındı')).fetchone()[0]}")

    # --- İŞ ATAMASI (GÜNCEL PERSONEL LİSTESİ İLE) ---
    elif choice == "İş Ataması":
        st.header("Yeni İş Ataması")
        staff_query = conn.execute("SELECT name FROM users WHERE role='Saha Personeli'").fetchall()
        staff_list = [r[0] for r in staff_query]
        
        if not staff_list:
            st.error("Sistemde kayıtlı Saha Personeli bulunamadı. Lütfen önce 'Kullanıcı Yönetimi' sekmesinden Saha Personeli ekleyin.")
        else:
            with st.form("ata"):
                t = st.text_input("İş Başlığı")
                p = st.selectbox("Personel", options=staff_list)
                s = st.selectbox("Şehir", options=CITIES)
                if st.form_submit_button("İşi Ata"):
                    if t:
                        conn.execute("INSERT INTO jobs (title, staff, city, status, date) VALUES (?,?,?,?,?)", (t, p, s, "Atandı", datetime.now().strftime("%Y-%m-%d")))
                        conn.commit()
                        st.success(f"İş başarıyla {p} personeline atandı.")
                    else: st.warning("Lütfen bir iş başlığı giriniz.")

    # --- ATANAN İŞLER (ADM/YÖN/MÜD) ---
    elif choice == "Atanan İşler":
        st.header("Sistemdeki Atanan İşler")
        df = pd.read_sql("SELECT id, title, staff, city, status, date FROM jobs WHERE status='Atandı'", conn)
        if df.empty: st.info("Atanan Bir Görev Bulunmamaktadır")
        else:
            f_p = st.multiselect("Personel Filtre", df['staff'].unique())
            if f_p: df = df[df['staff'].isin(f_p)]
            st.dataframe(df)
            st.download_button("Excel İndir", to_excel(df), "atanan_isler.xlsx")

    # --- ÜZERİME ATANAN İŞLER (SAHA) ---
    elif choice == "Üzerime Atanan İşler":
        st.header("Görevlerim")
        jobs = conn.execute("SELECT id, title FROM jobs WHERE staff=? AND status='Atandı'", (user['name'],)).fetchall()
        if not jobs: st.info("Atanan iş yok.")
        else:
            job_sel = st.selectbox("İş Seç", [j[1] for j in jobs])
            det = st.text_area("İş Detayı (Zorunlu)")
            g_mail = st.checkbox("Giriş Maili Gerekli")
            pics = st.file_uploader("Fotoğraflar (Maks 65)", accept_multiple_files=True)
            c1, c2 = st.columns(2)
            if c1.button("İşi Gönder"):
                stat = "Giriş Maili Bekler" if g_mail else "Kabul Alındı"
                conn.execute("UPDATE jobs SET detail=?, status=?, date=? WHERE title=?", (det, stat, datetime.now().strftime("%Y-%m-%d"), job_sel))
                conn.commit(); st.success("Gönderildi."); st.rerun()
            if c2.button("Kaydet"):
                conn.execute("UPDATE jobs SET detail=?, is_draft=1 WHERE title=?", (det, job_sel))
                conn.commit(); st.info("Taslak kaydedildi.")

    # --- GİRİŞ ONAYLARI ---
    elif choice == "Giriş Onayları":
        st.header("Giriş Maili Bekleyenler")
        df = pd.read_sql("SELECT id, title, staff, city, status FROM jobs WHERE status='Giriş Maili Bekler'", conn)
        st.dataframe(df)
        target = st.number_input("İş ID", step=1)
        if st.button("Kabul Yapılabilir"):
            conn.execute("UPDATE jobs SET status='Atandı' WHERE id=?", (target,))
            conn.commit(); st.rerun()

    # --- TAMAMLANAN İŞLER ---
    elif choice == "Tamamlanan İşler" or choice == "Tamamladığım İşler":
        st.header("Tamamlanan İşler")
        q = "SELECT * FROM jobs WHERE status='Kabul Alındı'"
        if user['role'] == "Saha Personeli": q += f" AND staff='{user['name']}'"
        df = pd.read_sql(q, conn)
        st.dataframe(df)
        if user['role'] != "Saha Personeli" and not df.empty:
            t_id = st.number_input("İş ID (TT Onay İçin)", step=1)
            if st.button("Türk Telekom Onaya Gönder"):
                conn.execute("UPDATE jobs SET status='TT Onayı Bekliyor' WHERE id=?", (t_id,))
                conn.commit(); st.rerun()

    # --- TT ONAYI BEKLEYENLER ---
    elif choice == "TT Onayı Bekleyenler":
        df = pd.read_sql("SELECT * FROM jobs WHERE status='TT Onayı Bekliyor'", conn)
        st.dataframe(df)
        if not df.empty:
            t_id = st.number_input("İş ID", step=1)
            c1, c2 = st.columns(2)
            if c1.button("Hak Edişe Gönder"):
                conn.execute("UPDATE jobs SET status='Hak Ediş Beklemede' WHERE id=?", (t_id,))
                conn.commit(); st.rerun()
            if c2.button("RET"):
                conn.execute("UPDATE jobs SET status='RET' WHERE id=?", (t_id,))
                conn.commit(); st.rerun()

    # --- HAK EDİŞ ---
    elif choice == "Hak Ediş":
        df = pd.read_sql("SELECT * FROM jobs WHERE status LIKE 'Hak Ediş%'", conn)
        st.dataframe(df)
        if not df.empty:
            t_id = st.number_input("İş ID", step=1)
            if st.button("Hak Ediş Alındı"):
                conn.execute("UPDATE jobs SET status='Hak Ediş Alındı' WHERE id=?", (t_id,))
                conn.commit(); st.rerun()

    # --- ZİMMET ---
    elif choice == "Zimmet & Envanter":
        if user['role'] != "Saha Personeli":
            with st.form("zimmet"):
                i = st.text_input("Eşya Adı")
                p = st.selectbox("Personel", [r[0] for r in conn.execute("SELECT name FROM users").fetchall()])
                if st.form_submit_button("Ekle"):
                    conn.execute("INSERT INTO inventory (item_name, assigned_to) VALUES (?,?)", (i, p))
                    conn.commit(); st.success("Eklendi")
        q = "SELECT * FROM inventory"
        if user['role'] == "Saha Personeli": q += f" WHERE assigned_to='{user['name']}'"
        st.dataframe(pd.read_sql(q, conn))

    # --- KULLANICI YÖNETİMİ ---
    elif choice == "Kullanıcı Yönetimi":
        with st.form("user_add"):
            n, m, p, ph, r = st.text_input("Ad Soyad"), st.text_input("Mail"), st.text_input("Şifre"), st.text_input("Telefon"), st.selectbox("Yetki", ["Admin", "Yönetici", "Müdür", "Saha Personeli"])
            if st.form_submit_button("Kullanıcı Ekle"):
                conn.execute("INSERT INTO users (name, email, phone, password, role) VALUES (?,?,?,?,?)", (n, m, ph, p, r))
                conn.commit(); st.success("Kullanıcı Eklendi"); st.rerun()
        df_u = pd.read_sql("SELECT id, name, email, role FROM users", conn)
        st.dataframe(df_u)
        d_id = st.number_input("Silinecek ID", step=1)
        if st.button("Kullanıcı Sil"):
            conn.execute("DELETE FROM users WHERE id=?", (d_id,))
            conn.commit(); st.rerun()

    # --- PROFİLİM ---
    elif choice == "Profilim":
        new_phone = st.text_input("Telefon Güncelle", value=user['phone'])
        if st.button("Güncelle"):
            conn.execute("UPDATE users SET phone=? WHERE id=?", (new_phone, user['id']))
            conn.commit(); st.success("Profil güncellendi")

    # --- ÇIKIŞ ---
    elif choice == "Çıkış":
        st.session_state.logged_in = False
        st.rerun()
