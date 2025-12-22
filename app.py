import streamlit as st
import pandas as pd
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Anatoli Bilişim - İş Yönetimi", layout="wide")

# --- SESSION STATE (OTURUM YÖNETİMİ) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_info'] = {}

# --- YARDIMCI FONKSİYONLAR (SAAT BAZLI MESAJ) ---
def get_greeting(name):
    hour = datetime.now().hour
    if 8 <= hour < 12:
        return f"Günaydın {name}, İyi Çalışmalar"
    elif 12 <= hour < 18:
        return f"İyi Günler {name}, İyi Çalışmalar"
    elif 18 <= hour < 0:
        return f"İyi Akşamlar {name}, İyi Çalışmalar"
    else:
        return f"İyi Geceler {name}, İyi Çalışmalar"

# --- GİRİŞ EKRANI ---
if not st.session_state['logged_in']:
    st.title("Anatoli Bilişim Giriş Paneli")
    email = st.text_input("Şirket Maili")
    password = st.text_input("Şifre", type="password")
    
    if st.button("Giriş Yap"):
        # Not: Burası veritabanından kontrol edilecek. Şimdilik örnek giriş:
        if email == "admin@anatoli.com" and password == "1234":
            st.session_state['logged_in'] = True
            st.session_state['user_info'] = {"ad": "Doğukan Gürol", "yetki": "Admin / Müdür"}
            st.rerun()
        else:
            st.error("Hatalı kullanıcı adı veya şifre!")

# --- ANA UYGULAMA ---
else:
    # SOL MENÜ
    with st.sidebar:
        st.subheader("Anatoli Bilişim")
        st.write(f"**{st.session_state['user_info']['ad']}**")
        st.caption(st.session_state['user_info']['yetki'])
        st.divider()
        
        menu_options = [
            "Ana Sayfa", "İş Ataması", "Atanan İşler", "Giriş Onayları", 
            "TT Onayı Bekleyenler", "Tamamlanan İşler", "Hak Ediş", 
            "Zimmet & Envanter", "Kullanıcı Yönetimi", "Profilim", "Çıkış"
        ]
        
        # Yetkiye göre menü kısıtlama (Örn: Sadece Admin/Yönetici Kullanıcı Yönetimi görür)
        if "Saha" in st.session_state['user_info']['yetki']:
            menu_options = ["Ana Sayfa", "Üzerime Atanan İşler", "Tamamladığım İşler", "Profilim", "Çıkış"]

        choice = st.radio("Menü", menu_options)

    # EKRANLAR
    if choice == "Ana Sayfa":
        st.title(get_greeting(st.session_state['user_info']['ad']))
        
        # Sayaçlar (Layout)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Günlük Tamamlanan", "12")
        col2.metric("Bekleyen Atamalar", "5")
        col3.metric("Haftalık Toplam", "84")
        col4.metric("Aylık Toplam", "320")

    elif choice == "İş Ataması":
        st.header("Yeni İş Ataması")
        with st.form("is_atama_form"):
            is_basligi = st.text_input("İş Başlığı")
            personel = st.selectbox("Personel Seçimi", ["Ahmet Yılmaz", "Mehmet Demir"]) # Veritabanından gelecek
            sehir = st.selectbox("Şehir Seçimi", ["İstanbul", "Ankara", "İzmir", "Bursa"]) # 81 il eklenecek
            submit = st.form_submit_button("İşi Ata")
            if submit:
                st.success(f"{is_basligi} işi {personel} personeline atandı!")

    elif choice == "Çıkış":
        st.session_state['logged_in'] = False
        st.rerun()
