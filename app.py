import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. AYARLAR VE VERİ YAPILARI ---
st.set_page_config(page_title="Anatoli Bilişim", layout="wide")

# Kullanıcılar
if 'users' not in st.session_state:
    st.session_state['users'] = {
        "dogukan": {"sifre": "1234", "ad_soyad": "Doğukan Gürol", "yetki": "Admin / Müdür"},
        "yonetici01": {"sifre": "4321", "ad_soyad": "Ahmet Yılmaz", "yetki": "Yönetici"},
        "saha01": {"sifre": "0000", "ad_soyad": "Mehmet Saha", "yetki": "Saha Personeli"}
    }

# İş Listesi
if 'is_verisi' not in st.session_state:
    st.session_state['is_verisi'] = pd.DataFrame(columns=[
        "İş ID", "Tarih", "İş Başlığı", "Personel", "Şehir", "Durum", "Notlar"
    ])

sehirler = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"]

# --- 2. GİRİŞ KONTROLÜ ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("Anatoli Bilişim - Giriş")
    k_adi = st.text_input("Kullanıcı Adı")
    sifre = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if k_adi in st.session_state['users'] and st.session_state['users'][k_adi]["sifre"] == sifre:
            st.session_state['auth'] = True
            st.session_state['user_info'] = st.session_state['users'][k_adi]
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı!")

# --- 3. ANA UYGULAMA ---
else:
    user = st.session_state['user_info']
    
    # Yan Menü
    with st.sidebar:
        st.subheader("Anatoli Bilişim")
        st.write(f"👤 {user['ad_soyad']}")
        st.caption(f"Yetki: {user['yetki']}")
        st.divider()
        
        if "Saha" in user['yetki']:
            menu = st.radio("Menü", ["Ana Sayfa", "Üzerime Atanan İşler", "Tamamladığım İşler", "Profilim", "Çıkış"])
        else:
            menu = st.radio("Menü", ["Ana Sayfa", "İş Ataması", "Atanan İşler", "Giriş Onayları", "TT Onayı Bekleyenler", "Kullanıcı Yönetimi", "Çıkış"])

    # EKRANLAR
    if menu == "Ana Sayfa":
        # Saat Bazlı Karşılama
        saat = datetime.now().hour
        if 8 <= saat < 12: selam = "Günaydın"
        elif 12 <= saat < 18: selam = "İyi Günler"
        elif 18 <= saat < 24: selam = "İyi Akşamlar"
        else: selam = "İyi Geceler"
        
        st.title(f"👋 {selam} {user['ad_soyad']}, İyi Çalışmalar")
        
        # Sayaçlar
        df = st.session_state['is_verisi']
        c1, c2, c3 = st.columns(3)
        if "Saha" not in user['yetki']:
            c1.metric("Bekleyen Atamalar", len(df[df['Durum'] == "Atandı"]))
            c2.metric("Günlük Tamamlanan", len(df[df['Durum'] == "Tamamlandı"]))
            c3.metric("Toplam Kayıtlı İş", len(df))
        else:
            kendi_isleri = df[df['Personel'] == user['ad_soyad']]
            c1.metric("Üzerimdeki İşler", len(kendi_isleri[kendi_isleri['Durum'] == "Atandı"]))
            c2.metric("Tamamladığım", len(kendi_isleri[kendi_isleri['Durum'] == "Tamamlandı"]))

    elif menu == "İş Ataması":
        st.header("📌 Yeni İş Ataması")
        with st.form("yeni_is"):
            baslik = st.text_input("İş Başlığı")
            saha_personelleri = [u["ad_soyad"] for u in st.session_state['users'].values() if "Saha" in u["yetki"]]
            personel = st.selectbox("Saha Personeli", saha_personelleri)
            sehir = st.selectbox("Şehir", sehirler)
            if st.form_submit_button("İşi Gönder"):
                yeni = {"İş ID": len(df)+1, "Tarih": str(datetime.now().date()), "İş Başlığı": baslik, "Personel": personel, "Şehir": sehir, "Durum": "Atandı", "Notlar": ""}
                st.session_state['is_verisi'] = pd.concat([st.session_state['is_verisi'], pd.DataFrame([yeni])], ignore_index=True)
                st.success(f"İş {personel} personeline atandı!")

    elif menu == "Kullanıcı Yönetimi":
        st.header("👥 Kullanıcı Yönetimi")
        with st.expander("➕ Yeni Kullanıcı Ekle"):
            nkadi = st.text_input("Giriş Adı")
            nad = st.text_input("İsim Soyisim")
            nsifre = st.text_input("Şifre")
            nyetki = st.selectbox("Yetki", ["Yönetici", "Müdür", "Saha Personeli"])
            if st.button("Kaydet"):
                st.session_state['users'][nkadi] = {"sifre": nsifre, "ad_soyad": nad, "yetki": nyetki}
                st.success("Kullanıcı oluşturuldu!")

    elif choice == "Çıkış" if 'choice' in locals() else menu == "Çıkış":
        st.session_state['auth'] = False
        st.rerun()
