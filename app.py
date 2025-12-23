import streamlit as st
import pandas as pd
from datetime import datetime
import io
import plotly.graph_objects as go

# --- 1. SİSTEM YAPILANDIRMASI VE VERİ SETİ ---
st.set_page_config(page_title="Saha İş Takip v2", layout="wide")

if 'db_jobs' not in st.session_state:
    st.session_state.db_jobs = pd.DataFrame(columns=[
        "Saha ID", "Personel", "Sehir", "Durum", "Tarih", "Notlar", "Foto_URL", "Red_Nedeni", "Taslak"
    ])

if 'user_db' not in st.session_state:
    st.session_state.user_db = {
        "admin@sirket.com": {"sifre": "1234", "rol": "Admin", "tel": "0500", "mail": "admin@sirket.com"},
        "dogukan@deneme.com": {"sifre": "123", "rol": "Saha Personeli", "tel": "0501", "mail": "dogukan@deneme.com"},
        "doguscan@deneme.com": {"sifre": "123", "rol": "Saha Personeli", "tel": "0502", "mail": "doguscan@deneme.com"},
        "cuneyt@deneme.com": {"sifre": "123", "rol": "Saha Personeli", "tel": "0503", "mail": "cuneyt@deneme.com"},
        "filiz@deneme.com": {"sifre": "123", "rol": "Müdür", "tel": "0504", "mail": "filiz@deneme.com"}
    }

if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=["Personel", "Esya", "Miktar"])

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = {}

TURKIYE_ILLER = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
]

# --- 2. YARDIMCI FONKSİYONLAR ---
def get_greeting():
    hr = datetime.now().hour
    name = st.session_state.user_info.get('mail', 'Kullanıcı')
    if 8 <= hr < 12: return f"Günaydın {name} İyi Çalışmalar"
    elif 12 <= hr < 18: return f"İyi Günler {name} İyi Çalışmalar"
    elif 18 <= hr < 24: return f"İyi Akşamlar {name} İyi Çalışmalar"
    else: return f"İyi Geceler {name} İyi Çalışmalar"

def draw_gauge(value, title):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        title = {'text': title},
        gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "darkblue"}}
    ))
    fig.update_layout(height=250)
    return fig

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def filter_component(df):
    col1, col2, col3, col4 = st.columns(4)
    with col1: f_date = st.date_input("Tarih Filtresi", value=None)
    with col2: f_pers = st.selectbox("Personel Filtresi", ["Hepsi"] + list(st.session_state.user_db.keys()))
    with col3: f_city = st.selectbox("Şehir Filtresi", ["Hepsi"] + TURKIYE_ILLER)
    with col4:
        st_opts = ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"]
        if st.session_state.user_info['rol'] in ["Admin", "Müdür"]:
            st_opts += ["Türk Telekom Onayında", "Hak Ediş Bekleniyor", "Hak Ediş Alındı"]
        f_status = st.selectbox("Durum Filtresi", st_opts)
    
    filtered = df.copy()
    if f_date: filtered = filtered[pd.to_datetime(filtered["Tarih"]).dt.date == f_date]
    if f_pers != "Hepsi": filtered = filtered[filtered["Personel"] == f_pers]
    if f_city != "Hepsi": filtered = filtered[filtered["Sehir"] == f_city]
    if f_status != "Hepsi": filtered = filtered[filtered["Durum"] == f_status]
    return filtered

# --- 3. GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.title("Saha Operasyon Girişi")
    u = st.text_input("E-posta")
    p = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if u in st.session_state.user_db and st.session_state.user_db[u]["sifre"] == p:
            st.session_state.logged_in = True
            st.session_state.user_info = st.session_state.user_db[u]
            st.rerun()
        else: st.error("Hatalı Giriş!")

# --- 4. ANA PANEL ---
else:
    rol = st.session_state.user_info['rol']
    user_mail = st.session_state.user_info['mail']

    st.sidebar.title(f"Hoşgeldiniz")
    st.sidebar.write(f"Kullanıcı: {user_mail}")
    
    if rol == "Saha Personeli":
        menu = ["Anasayfa", "Üzerime Atanan İşler", "Zimmetim", "Profil", "Çıkış"]
    else:
        menu = ["Anasayfa", "İş Ataması", "Atanan İşler Takip", "Tamamlanan İşler", "TT Onay Bekleyenler", "Hak Ediş", "Zimmet/Envanter", "Kullanıcı Yönetimi", "Profil", "Çıkış"]
    
    choice = st.sidebar.radio("Menü Seçin", menu)

    # GÖSTERGELER (Gauge)
    gc1, gc2, gc3 = st.columns(3)
    gc1.plotly_chart(draw_gauge(70, "Günlük %"), use_container_width=True)
    gc2.plotly_chart(draw_gauge(55, "Haftalık %"), use_container_width=True)
    gc3.plotly_chart(draw_gauge(40, "Aylık %"), use_container_width=True)

    if choice == "Anasayfa":
        st.header(get_greeting())
        df = st.session_state.db_jobs
        if rol in ["Admin", "Müdür"]:
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Tamamlanan", len(df[df["Durum"]=="İŞ TAMAMLANDI"]))
            c2.metric("Atanmış Bekleyen", len(df[df["Durum"]=="Yeni Atama"]))
            c3.metric("Haftalık İş", 12)
        else:
            c1, c2 = st.columns(2)
            c1.metric("Tamamladığım", len(df[(df["Personel"]==user_mail) & (df["Durum"]=="İŞ TAMAMLANDI")]))
            c2.metric("Üzerime Atanan", len(df[(df["Personel"]==user_mail) & (df["Durum"]=="Yeni Atama")]))

    elif choice == "İş Ataması":
        st.subheader("Yeni İş Atama")
        sid = st.text_input("Saha ID")
        sehir = st.selectbox("Şehir", TURKIYE_ILLER)
        saha_pers = [m for m, v in st.session_state.user_db.items() if v["rol"] == "Saha Personeli"]
        pers = st.selectbox("Personel Seçin", saha_pers)
        notlar = st.text_area("İş Notları")
        if st.button("Atama Yap"):
            new_job = pd.DataFrame([{
                "Saha ID": sid, "Personel": pers, "Sehir": sehir, "Durum": "Yeni Atama",
                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "Notlar": notlar, "Taslak": False
            }])
            st.session_state.db_jobs = pd.concat([st.session_state.db_jobs, new_job], ignore_index=True)
            st.success("İş Atandı.")

    elif choice == "Üzerime Atanan İşler":
        my_jobs = st.session_state.db_jobs[st.session_state.db_jobs["Personel"] == user_mail]
        if my_jobs.empty: st.info("Bekleyen işiniz yok.")
        else:
            job_id = st.selectbox("Saha ID Seç", my_jobs["Saha ID"])
            idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == job_id].index[0]
            st.selectbox("Durum", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"])
            n = st.text_area("Notlar", value=st.session_state.db_jobs.at[idx, 'Notlar'])
            st.file_uploader("Fotoğraf Ekle")
            if st.button("İşi Gönder"):
                st.session_state.db_jobs.at[idx, 'Durum'] = "İŞ TAMAMLANDI"
                st.session_state.db_jobs.at[idx, 'Notlar'] = n
                st.success("Gönderildi.")

    elif choice == "Tamamlanan İşler":
        filtered = filter_component(st.session_state.db_jobs)
        if filtered.empty: st.warning("Gösterilecek Tamamlanmış İş Bulunmamaktadır")
        else:
            st.dataframe(filtered)
            st.download_button("Excel İndir", to_excel(filtered), "rapor.xlsx")

    elif choice == "Kullanıcı Yönetimi":
        if rol in ["Admin", "Müdür"]:
            nu = st.text_input("Yeni E-posta")
            np = st.text_input("Yeni Şifre", type="password")
            nr = st.selectbox("Rol", ["Saha Personeli", "Müdür", "Admin"])
            if st.button("Kullanıcı Ekle"):
                st.session_state.user_db[nu] = {"sifre": np, "rol": nr, "mail": nu, "tel": ""}
                st.success("Kullanıcı Oluşturuldu.")

    elif choice == "Profil":
        st.subheader("Profil Ayarları")
        if rol != "Müdür":
            st.text_input("Telefon", value=st.session_state.user_info.get('tel', ''))
            st.text_input("Mail", value=user_mail)
            st.button("Güncellemeleri Kaydet")
        st.text_input("Yeni Şifre", type="password")
        st.button("Şifre Değiştir")

    elif choice == "Çıkış":
        st.session_state.logged_in = False
        st.rerun()
