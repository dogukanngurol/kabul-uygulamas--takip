import streamlit as st
import pandas as pd
from datetime import datetime
import io
import plotly.graph_objects as go

# --- 1. CONFIG & DATA INITIALIZATION ---
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

# --- 2. HELPERS ---
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
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title},
        gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "darkblue"}}
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=50, b=20))
    return fig

def filter_component(df):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        f_date = st.date_input("Tarih Seçiniz", value=None)
    with col2:
        f_pers = st.selectbox("Personel", ["Hepsi"] + list(st.session_state.user_db.keys()))
    with col3:
        f_city = st.selectbox("Şehir", ["Hepsi"] + TURKIYE_ILLER)
    with col4:
        st_opts = ["Hepsi", "İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBI GELMİYOR"]
        if st.session_state.user_info['rol'] in ["Admin", "Müdür"]:
            st_opts += ["Türk Telekom Onayında", "Hak Ediş Bekleniyor", "Hak Ediş Alındı"]
        f_status = st.selectbox("Durum", st_opts)
    
    filtered = df.copy()
    if f_date: filtered = filtered[pd.to_datetime(filtered["Tarih"]).dt.date == f_date]
    if f_pers != "Hepsi": filtered = filtered[filtered["Personel"] == f_pers]
    if f_city != "Hepsi": filtered = filtered[filtered["Sehir"] == f_city]
    if f_status != "Hepsi": filtered = filtered[filtered["Durum"] == f_status]
    return filtered

# --- 3. LOGIN ---
if not st.session_state.logged_in:
    st.title("Giriş Paneli")
    u = st.text_input("E-posta")
    p = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if u in st.session_state.user_db and st.session_state.user_db[u]["sifre"] == p:
            st.session_state.logged_in = True
            st.session_state.user_info = st.session_state.user_db[u]
            st.rerun()
        else: st.error("Hatalı kimlik bilgileri")

# --- 4. MAIN INTERFACE ---
else:
    rol = st.session_state.user_info['rol']
    user_mail = st.session_state.user_info['mail']

    # GAUGE SECTION
    gc1, gc2, gc3 = st.columns(3)
    gc1.plotly_chart(draw_gauge(75, "Günlük Plan %"), use_container_width=True)
    gc2.plotly_chart(draw_gauge(60, "Haftalık Plan %"), use_container_width=True)
    gc3.plotly_chart(draw_gauge(40, "Aylık Plan %"), use_container_width=True)

    st.sidebar.title("MENÜ")
    if rol == "Saha Personeli":
        menu = ["Anasayfa", "Üzerime Atanan İşler", "Zimmetim", "Profil", "Çıkış"]
    elif rol == "Müdür":
        menu = ["Anasayfa", "İş Ataması", "Atanan İşler Takip", "Tamamlanan İşler", "TT Onay Bekleyenler", "Hak Ediş", "Zimmet/Envanter", "Kullanıcı Yönetimi", "Profil", "Çıkış"]
    else: # Admin
        menu = ["Anasayfa", "İş Ataması", "Atanan İşler Takip", "Tamamlanan İşler", "TT Onay Bekleyenler", "Hak Ediş", "Zimmet/Envanter", "Kullanıcı Yönetimi", "Profil", "Çıkış"]
    
    choice = st.sidebar.radio("Sayfa", menu)

    # --- PAGES ---
    if choice == "Anasayfa":
        st.header(get_greeting())
        df = st.session_state.db_jobs
        if rol in ["Admin", "Müdür"]:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tamamlanan İşler", len(df[df["Durum"]=="İŞ TAMAMLANDI"]))
            c2.metric("Atanmış Bekleyen", len(df[df["Durum"]=="Yeni Atama"]))
            c3.metric("Haftalık Toplam", 15) # Örnek sayaç
        else:
            c1, c2 = st.columns(2)
            c1.metric("Tamamladığım İşler", len(df[(df["Personel"]==user_mail) & (df["Durum"]=="İŞ TAMAMLANDI")]))
            c2.metric("Üzerime Atananlar", len(df[(df["Personel"]==user_mail) & (df["Durum"]=="Yeni Atama")]))

    elif choice == "İş Ataması":
        st.subheader("İş Atama Ekranı")
        sid = st.text_input("Saha ID")
        sehir = st.selectbox("Şehir", TURKIYE_ILLER)
        # Müdür kullanıcıları iş atama listesinde görünmez
        saha_personeli = [m for m, v in st.session_state.user_db.items() if v["rol"] == "Saha Personeli"]
        pers = st.selectbox("Atanacak Personel", saha_personeli)
        notlar = st.text_area("İş Notu")
        if st.button("Atamayı Yap"):
            new_job = pd.DataFrame([{
                "Saha ID": sid, "Personel": pers, "Sehir": sehir, "Durum": "Yeni Atama",
                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "Notlar": notlar, "Taslak": False
            }])
            st.session_state.db_jobs = pd.concat([st.session_state.db_jobs, new_job], ignore_index=True)
            st.success("Atama yapıldı.")

    elif choice == "Üzerime Atanan İşler":
        st.subheader("Aktif İşlerim")
        my_jobs = st.session_state.db_jobs[st.session_state.db_jobs["Personel"] == user_mail]
        if my_jobs.empty: st.warning("Atanmış işiniz bulunmamaktadır.")
        else:
            job_id = st.selectbox("İş Seç", my_jobs["Saha ID"])
            idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == job_id].index[0]
            
            st.write(f"Mevcut Durum: {st.session_state.db_jobs.at[idx, 'Durum']}")
            new_st = st.selectbox("Durum Güncelle", ["İŞ TAMAMLANDI", "GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"])
            new_notes = st.text_area("Rapor / Notlar", value=st.session_state.db_jobs.at[idx, 'Notlar'])
            st.file_uploader("Dosya/Fotoğraf Ekle (Storage'a gönderilir)")
            
            col_t1, col_t2 = st.columns(2)
            if col_t1.button("Kaydet (Taslak)"):
                st.session_state.db_jobs.at[idx, 'Notlar'] = new_notes
                st.session_state.db_jobs.at[idx, 'Taslak'] = True
                st.info("Taslak olarak kaydedildi.")
            if col_t2.button("İşi Gönder"):
                st.session_state.db_jobs.at[idx, 'Durum'] = new_st
                st.session_state.db_jobs.at[idx, 'Notlar'] = new_notes
                st.session_state.db_jobs.at[idx, 'Taslak'] = False
                st.success("İş gönderildi.")

    elif choice == "Tamamlanan İşler":
        st.subheader("İş Takip ve Onay")
        mode = st.radio("Liste Tipi", ["Hepsi", "Tamamlanan İşler", "Tamamlanamayan İşler"])
        df_view = st.session_state.db_jobs
        if mode == "Tamamlanan İşler": df_view = df_view[df_view["Durum"] == "İŞ TAMAMLANDI"]
        elif mode == "Tamamlanamayan İşler": df_view = df_view[df_view["Durum"].isin(["GİRİŞ YAPILAMADI", "TEPKİLİ", "MAL SAHİBİ GELMİYOR"])]
        
        filtered = filter_component(df_view)
        if filtered.empty: st.write("Gösterilecek Tamamlanmış İş Bulunmamaktadır")
        else:
            st.dataframe(filtered)
            st.download_button("Excel İndir", to_excel(filtered), "rapor.xlsx")
            
            selected_sid = st.selectbox("İşlem Yapmak İçin Saha ID Seç", filtered["Saha ID"])
            f_idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == selected_sid].index[0]
            
            c_onay1, c_onay2, c_onay3 = st.columns(3)
            if c_onay1.button("Kabul"):
                st.session_state.db_jobs.at[f_idx, "Durum"] = "Türk Telekom Onayında"
                st.rerun()
            if c_onay2.button("Ret"):
                ret_reason = st.text_input("Ret Sebebi")
                if ret_reason:
                    st.session_state.db_jobs.at[f_idx, "Durum"] = "Yeni Atama"
                    st.session_state.db_jobs.at[f_idx, "Red_Nedeni"] = ret_reason
                    st.rerun()
            if c_onay3.button("Türk Telekom Onay Bekler"):
                st.session_state.db_jobs.at[f_idx, "Durum"] = "Türk Telekom Onayında"
                st.rerun()

    elif choice == "TT Onay Bekleyenler":
        st.subheader("Türk Telekom Onay Süreci")
        df_tt = st.session_state.db_jobs[st.session_state.db_jobs["Durum"] == "Türk Telekom Onayında"]
        filtered = filter_component(df_tt)
        st.dataframe(filtered)
        if not filtered.empty:
            target_sid = st.selectbox("İş Seç", filtered["Saha ID"])
            if st.button("Hak Edişe Gönder"):
                t_idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == target_sid].index[0]
                st.session_state.db_jobs.at[t_idx, "Durum"] = "Hak Ediş Bekleniyor"
                st.rerun()

    elif choice == "Hak Ediş":
        st.subheader("Hak Ediş Yönetimi")
        df_hak = st.session_state.db_jobs[st.session_state.db_jobs["Durum"].isin(["Hak Ediş Bekleniyor", "Hak Ediş Alındı"])]
        filtered = filter_component(df_hak)
        st.dataframe(filtered)
        if not filtered.empty:
            h_sid = st.selectbox("İş Seç", filtered["Saha ID"])
            if st.button("Hak Ediş Alındı Seç"):
                h_idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == h_sid].index[0]
                st.session_state.db_jobs.at[h_idx, "Durum"] = "Hak Ediş Alındı"
                st.rerun()

    elif choice == "Zimmet/Envanter":
        st.subheader("Zimmet ve Envanter Yönetimi")
        if rol in ["Admin", "Müdür"]:
            pers_zimmet = st.selectbox("Personel", list(st.session_state.user_db.keys()))
            esya = st.text_input("Eşya Adı")
            adet = st.number_input("Adet", min_value=1)
            if st.button("Zimmetle"):
                st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([{"Personel": pers_zimmet, "Esya": esya, "Miktar": adet}])], ignore_index=True)
            st.dataframe(st.session_state.inventory)
            st.download_button("Zimmet Excel İndir", to_excel(st.session_state.inventory), "zimmet.xlsx")
        else:
            st.write("Üzerime Zimmetli Eşyalar")
            st.dataframe(st.session_state.inventory[st.session_state.inventory["Personel"] == user_mail])

    elif choice == "Kullanıcı Yönetimi":
        st.subheader("Kullanıcı Kontrol Paneli")
        nu = st.text_input("Yeni Kullanıcı E-posta")
        np = st.text_input("Şifre", type="password")
        nr = st.selectbox("Rol", ["Saha Personeli", "Müdür", "Admin"])
        if st.button("Kullanıcı Ekle"):
            st.session_state.user_db[nu] = {"sifre": np, "rol": nr, "mail": nu, "tel": ""}
            st.success("Kullanıcı eklendi.")
        
        del_u = st.selectbox("Silinecek Kullanıcı", list(st.session_state.user_db.keys()))
        if st.button("Kullanıcıyı Sil"):
            del st.session_state.user_db[del_u]
            st.rerun()

    elif choice == "Profil":
        st.subheader("Profil Ayarları")
        st.write(f"E-posta: {user_mail}")
        if rol != "Müdür":
            new_tel = st.text_input("Telefon", value=st.session_state.user_info.get('tel',''))
            new_mail = st.text_input("Mail Adresi", value=user_mail)
            if st.button("Güncellemeleri Kaydet"):
                st.session_state.user_db[user_mail]['tel'] = new_tel
                st.success("Kaydedildi.")
        
        new_pwd = st.text_input("Yeni Şifre", type="password")
        if st.button("Şifre Değiştir"):
            st.session_state.user_db[user_mail]['sifre'] = new_pwd
            st.success("Şifre güncellendi.")

    elif choice == "Atanan İşler Takip":
        st.subheader("Atanan İşlerin Takibi")
        st.dataframe(st.session_state.db_jobs[st.session_state.db_jobs["Durum"] == "Yeni Atama"])

    elif choice == "Çıkış":
        st.session_state.logged_in = False
        st.rerun()

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()
