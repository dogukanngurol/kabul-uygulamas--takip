import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. VERİ YAPILARI VE AYARLAR ---
st.set_page_config(page_title="Anatoli Bilişim", layout="wide")

# Kullanıcı Veritabanı
if 'users' not in st.session_state:
    st.session_state['users'] = {
        "dogukan": {"sifre": "1234", "ad_soyad": "Doğukan Gürol", "yetki": "Admin / Müdür"},
        "yonetici01": {"sifre": "4321", "ad_soyad": "Ahmet Yılmaz", "yetki": "Yönetici"},
        "saha01": {"sifre": "0000", "ad_soyad": "Mehmet Saha", "yetki": "Saha Personeli"}
    }

# İş Veritabanı (Simüle edilmiş)
if 'is_verisi' not in st.session_state:
    st.session_state['is_verisi'] = pd.DataFrame(columns=[
        "İş ID", "Tarih", "İş Başlığı", "Personel", "Şehir", "Durum", "Notlar"
    ])

# 81 İl
sehirler = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"]

# --- 2. YARDIMCI FONKSİYONLAR ---
def excel_indir(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 3. GİRİŞ EKRANI ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("Anatoli Bilişim Giriş")
    k_adi = st.text_input("Kullanıcı Adı")
    sifre = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if k_adi in st.session_state['users'] and st.session_state['users'][k_adi]["sifre"] == sifre:
            st.session_state['auth'] = True
            st.session_state['user_info'] = st.session_state['users'][k_adi]
            st.rerun()
        else: st.error("Hatalı giriş!")

# --- 4. ANA UYGULAMA ---
else:
    user = st.session_state['user_info']
    
    with st.sidebar:
        st.subheader("Anatoli Bilişim")
        st.write(f"👤 {user['ad_soyad']}")
        st.caption(f"Yetki: {user['yetki']}")
        st.divider()
        
        menu_items = ["Ana Sayfa", "İş Ataması", "Atanan İşler", "Giriş Onayları", "TT Onayı Bekleyenler", "Tamamlanan İşler", "Hak Ediş", "Zimmet & Envanter", "Kullanıcı Yönetimi", "Profilim", "Çıkış"]
        if "Saha" in user['yetki']:
            menu_items = ["Ana Sayfa", "Üzerime Atanan İşler", "Tamamladığım İşler", "Profilim", "Çıkış"]
        
        choice = st.radio("Menü", menu_items)

    # --- EKRANLAR ---
    if choice == "Ana Sayfa":
        st.title("Hoş Geldiniz")
        st.write(f"Sayın {user['ad_soyad']}, iyi çalışmalar dileriz.")
        
    elif choice == "İş Ataması":
        st.header("📌 Yeni İş Ataması")
        with st.form("is_atama"):
            baslik = st.text_input("İş Başlığı")
            saha_elemanlari = [u["ad_soyad"] for u in st.session_state['users'].values() if "Saha" in u["yetki"]]
            personel = st.selectbox("Personel", saha_elemanlari)
            sehir = st.selectbox("Şehir", sehirler)
            if st.form_submit_button("Ata"):
                yeni = {"İş ID": len(st.session_state['is_verisi'])+1, "Tarih": str(datetime.now().date()), "İş Başlığı": baslik, "Personel": personel, "Şehir": sehir, "Durum": "Atandı", "Notlar": ""}
                st.session_state['is_verisi'] = pd.concat([st.session_state['is_verisi'], pd.DataFrame([yeni])], ignore_index=True)
                st.success("İş atandı!")

    elif choice == "Giriş Onayları":
        st.header("📩 Giriş Maili Bekleyenler")
        onay_bekleyenler = st.session_state['is_verisi'][st.session_state['is_verisi']['Durum'] == "Giriş Maili Bekler"]
        st.dataframe(onay_bekleyenler)
        if not onay_bekleyenler.empty:
            if st.button("Seçili İşi 'Kabul Yapılabilir' Olarak Güncelle"):
                st.info("Bu özellik bir sonraki adımda ID seçimi ile detaylandırılacaktır.")

    elif choice == "TT Onayı Bekleyenler":
        st.header("🏢 Türk Telekom Onay Ekranı")
        tt_bekleyen = st.session_state['is_verisi'][st.session_state['is_verisi']['Durum'] == "TT Onayı Bekliyor"]
        st.dataframe(tt_bekleyen)
        if not tt_bekleyen.empty:
            st.download_button("Raporu Excel Olarak İndir", data=excel_indir(tt_bekleyen), file_name="tt_onay.xlsx")

    elif choice == "Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        # Yeni Kullanıcı Ekleme
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            y_kadi = st.text_input("Kullanıcı Adı (Giriş için)")
            y_ad = st.text_input("İsim Soyisim")
            y_sifre = st.text_input("Şifre")
            y_yetki = st.selectbox("Yetki", ["Yönetici", "Müdür", "Saha Personeli"])
            if st.button("Kullanıcıyı Kaydet"):
                st.session_state['users'][y_kadi] = {"sifre": y_sifre, "ad_soyad": y_ad, "yetki": y_yetki}
                st.success("Kullanıcı eklendi!")
        
        # Mevcut Kullanıcıları Listele
        st.subheader("Aktif Kullanıcılar")
        user_df = pd.DataFrame.from_dict(st.session_state['users'], orient='index')
        st.table(user_df[["ad_soyad", "yetki"]])

    elif choice == "Çıkış":
        st.session_state['auth'] = False
        st.rerun()
