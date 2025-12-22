import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. KULLANICI VERİTABANI (Örnek Giriş Bilgileri) ---
# Gerçek sistemde bunlar şifrelenmiş olarak tutulmalıdır.
USERS = {
    "dogukan": {"sifre": "1234", "ad_soyad": "Doğukan Gürol", "yetki": "Admin / Müdür"},
    "yonetici01": {"sifre": "4321", "ad_soyad": "Ahmet Yılmaz", "yetki": "Yönetici"},
    "saha01": {"sifre": "0000", "ad_soyad": "Mehmet Saha", "yetki": "Saha Personeli"}
}

# --- 2. AYARLAR VE SESSION STATE ---
st.set_page_config(page_title="Anatoli Bilişim", layout="wide")

if 'auth' not in st.session_state:
    st.session_state['auth'] = False
    st.session_state['user_info'] = None

if 'is_verisi' not in st.session_state:
    st.session_state['is_verisi'] = pd.DataFrame(columns=[
        "İş ID", "Tarih", "İş Başlığı", "Personel", "Şehir", "Durum", "Notlar"
    ])

# --- 3. GİRİŞ EKRANI (Yetki Seçimi Kaldırıldı) ---
if not st.session_state['auth']:
    st.title("Anatoli Bilişim - Sistem Girişi")
    
    with st.container():
        kullanici_adi = st.text_input("Kullanıcı Adı")
        sifre = st.text_input("Şifre", type="password")
        
        if st.button("Giriş Yap"):
            if kullanici_adi in USERS and USERS[kullanici_adi]["sifre"] == sifre:
                st.session_state['auth'] = True
                st.session_state['user_info'] = USERS[kullanici_adi]
                st.success("Giriş Başarılı!")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")

# --- 4. ANA UYGULAMA ---
else:
    user = st.session_state['user_info']
    
    # SOL MENÜ
    with st.sidebar:
        st.header("Anatoli Bilişim")
        st.subheader(f"👤 {user['ad_soyad']}")
        st.caption(f"🛡️ Yetki: {user['yetki']}")
        st.divider()
        
        # Yetkiye göre dinamik menü
        if "Saha" in user['yetki']:
            menu = st.radio("Menü", ["Ana Sayfa", "Üzerime Atanan İşler", "Tamamladığım İşler", "Profilim", "Çıkış"])
        else:
            menu = st.radio("Menü", ["Ana Sayfa", "İş Ataması", "Atanan İşler", "Giriş Onayları", "TT Onayı Bekleyenler", "Kullanıcı Yönetimi", "Çıkış"])

    # --- 5. EKRAN İÇERİKLERİ ---
    if menu == "Ana Sayfa":
        # Saat bazlı karşılama
        saat = datetime.now().hour
        mesaj = "Günaydın" if 8<=saat<12 else "İyi Günler" if 12<=saat<18 else "İyi Akşamlar" if 18<=saat<24 else "İyi Geceler"
        st.title(f"{mesaj} {user['ad_soyad']}, İyi Çalışmalar")
        
        # Sayaçlar (Sadece Yönetici Grubuna)
        if "Saha" not in user['yetki']:
            c1, c2, c3 = st.columns(3)
            c1.metric("Günlük Tamamlanan", "12")
            c2.metric("Bekleyen Atamalar", "5")
            c3.metric("Aylık Toplam İş", "145")

    elif menu == "İş Ataması":
        st.header("📌 Yeni İş Ataması")
        with st.form("atama_formu"):
            baslik = st.text_input("İş Başlığı")
            personel = st.selectbox("Saha Personeli Seçin", ["Mehmet Saha", "Ali Saha"])
            sehir = st.selectbox("Şehir", ["İstanbul", "Ankara", "İzmir", "Bursa"]) # Liste uzatılabilir
            if st.form_submit_button("İşi Ata"):
                st.success(f"İş başarıyla {personel} personeline atandı.")

    elif menu == "Atanan İşler":
        st.header("📊 Atanan İşler Takibi")
        df = st.session_state['is_verisi']
        st.dataframe(df, use_container_width=True)
        
        # Excel Raporu
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Excel Olarak İndir", data=output.getvalue(), file_name="is_listesi.xlsx")

    elif menu == "Çıkış":
        st.session_state['auth'] = False
        st.session_state['user_info'] = None
        st.rerun()
