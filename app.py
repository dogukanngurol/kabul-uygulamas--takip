import streamlit as st
import pandas as pd
from datetime import datetime
import io
from PIL import Image

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Anatoli Bilişim", layout="wide", initial_sidebar_state="expanded")

# --- VERİ SİMÜLASYONU (SESSION STATE) ---
if 'is_verisi' not in st.session_state:
    st.session_state['is_verisi'] = pd.DataFrame(columns=[
        "İş ID", "Tarih", "İş Başlığı", "Personel", "Şehir", "Durum", "Notlar", "Fotoğraf Sayısı"
    ])

# --- 81 İL LİSTESİ ---
sehirler = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"]

# --- FONKSİYONLAR ---
def excel_olustur(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

def saatlik_mesaj(isim):
    saat = datetime.now().hour
    if 8 <= saat < 12: mesaj = "Günaydın"
    elif 12 <= saat < 18: mesaj = "İyi Günler"
    elif 18 <= saat < 24: mesaj = "İyi Akşamlar"
    else: mesaj = "İyi Geceler"
    return f"{mesaj} {isim}, İyi Çalışmalar"

# --- GİRİŞ EKRANI ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("Anatoli Bilişim Sistem Girişi")
    kullanici = st.text_input("Kullanıcı Adı")
    sifre = st.text_input("Şifre", type="password")
    yetki = st.selectbox("Giriş Yetkisi", ["Admin", "Yönetici", "Müdür", "Saha Personeli"])
    
    if st.button("Giriş Yap"):
        st.session_state['auth'] = True
        st.session_state['user_name'] = kullanici
        st.session_state['role'] = yetki
        st.rerun()

else:
    # --- YAN MENÜ ---
    with st.sidebar:
        st.header("Anatoli Bilişim")
        st.write(f"👤 {st.session_state['user_name']}")
        st.caption(f"🛡️ Yetki: {st.session_state['role']}")
        st.divider()
        
        if st.session_state['role'] in ["Admin", "Yönetici", "Müdür"]:
            menu = st.radio("Menü", ["Ana Sayfa", "İş Ataması", "Atanan İşler", "Tamamlanan İşler", "Kullanıcı Yönetimi", "Çıkış"])
        else:
            menu = st.radio("Menü", ["Ana Sayfa", "Üzerime Atanan İşler", "Tamamladığım İşler", "Profilim", "Çıkış"])

    # --- EKRANLAR ---
    if menu == "Ana Sayfa":
        st.title(saatlik_mesaj(st.session_state['user_name']))
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Bekleyen İşler", "5")
        c2.metric("Tamamlanan (Günlük)", "12")
        c3.metric("Aylık Toplam", "145")

    elif menu == "İş Ataması":
        st.header("📌 Yeni İş Atama Paneli")
        with st.form("atama_formu"):
            baslik = st.text_input("İş Başlığı")
            personel = st.selectbox("Saha Personeli", ["Ahmet Saha", "Mehmet Saha", "Zeynep Saha"])
            sehir = st.selectbox("Şehir", sehirler)
            if st.form_submit_button("İşi Gönder"):
                yeni_satir = {
                    "İş ID": len(st.session_state['is_verisi']) + 1,
                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "İş Başlığı": baslik, "Personel": personel, "Şehir": sehir,
                    "Durum": "Atandı", "Notlar": "", "Fotoğraf Sayısı": 0
                }
                st.session_state['is_verisi'] = pd.concat([st.session_state['is_verisi'], pd.DataFrame([yeni_satir])], ignore_index=True)
                st.success("İş başarıyla personele iletildi.")

    elif menu == "Atanan İşler":
        st.header("📊 Atanan İşlerin Takibi")
        df = st.session_state['is_verisi']
        
        # Filtreler
        f_sehir = st.multiselect("Şehir Filtresi", sehirler)
        if f_sehir:
            df = df[df['Şehir'].isin(f_sehir)]
        
        st.dataframe(df, use_container_width=True)
        
        # Excel İndirme
        if not df.empty:
            excel_data = excel_olustur(df)
            st.download_button("📥 Excel Raporu İndir", data=excel_data, file_name="is_raporu.xlsx")

    elif menu == "Üzerime Atanan İşler":
        st.header("🛠️ Görevlerim")
        st.info("Tamamladığınız işler için fotoğraf yükleyip 'İşi Gönder' butonuna basınız.")
        
        with st.expander("İş Detayı ve Formu Aç"):
            is_detay = st.text_area("İş Detayı (Zorunlu)")
            yuklenen_dosyalar = st.file_uploader("Fotoğraflar (Maks 65 Adet)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
            
            if len(yuklenen_dosyalar) > 65:
                st.error("En fazla 65 fotoğraf yükleyebilirsiniz!")
            
            if st.button("İşi Gönder"):
                if not is_detay:
                    st.warning("Lütfen iş detayını doldurunuz!")
                else:
                    st.success("İş başarıyla tamamlandı ve merkeze gönderildi.")

    elif menu == "Çıkış":
        st.session_state['auth'] = False
        st.rerun()
