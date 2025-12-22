import streamlit as st
from src.store.AuthContext import init_auth, login
from src.layout.Sidebar import render_sidebar
from src.utils.roleUtils import ROLES

# Sayfa Konfigürasyonu
st.set_page_config(page_title="İş Takip Demo", layout="wide")

init_auth()

# Giriş Kontrolü
if st.session_state.user is None:
    st.title("Sistem Girişi")
    st.info("Lütfen bir rol seçerek giriş yapın (Demo)")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Admin Olarak Gir"): login(ROLES["ADMIN"])
        if st.button("Yönetici Olarak Gir"): login(ROLES["MANAGER"])
    with col2:
        if st.button("Müdür Olarak Gir"): login(ROLES["DIRECTOR"])
        if st.button("Saha Personeli Olarak Gir"): login(ROLES["FIELD"])
else:
    # Kullanıcı giriş yaptıysa Sidebar ve Sayfaları göster
    selected_page = render_sidebar()
    
    st.header(f"📍 {selected_page}")
    
    # Sayfa Yönlendirmeleri (Burada 'pages' altındaki dosyalar çağrılabilir)
    if selected_page == "Dashboard":
        st.write("Özet veriler buraya gelecek.")
    elif selected_page == "Yeni İş Ata":
        st.write("İş atama formu.")
    elif selected_page == "Raporlar":
        st.write("Grafikler ve tablolar.")
