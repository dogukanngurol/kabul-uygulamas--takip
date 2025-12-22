import streamlit as st
from src.store.AuthContext import init_auth, login
from src.layout.Sidebar import render_sidebar
from src.utils.roleUtils import ROLES

st.set_page_config(page_title="İş Takip Sistemi", layout="wide")
init_auth()

if st.session_state.user is None:
    st.title("Sistem Girişi")
    st.subheader("Lütfen bir rol seçerek sistemi simüle edin:")
    
    cols = st.columns(4)
    if cols[0].button("Admin"): login(ROLES["ADMIN"])
    if cols[1].button("Yönetici"): login(ROLES["MANAGER"])
    if cols[2].button("Müdür"): login(ROLES["DIRECTOR"])
    if cols[3].button("Saha"): login(ROLES["FIELD"])

else:
    # Kullanıcı giriş yaptıysa menüyü ve içeriği göster
    selected_page = render_sidebar()
    
    st.title(f"📍 {selected_page}")
    
    # Basit sayfa yönlendirme mantığı
    if selected_page == "Dashboard":
        st.write("Genel durum raporları burada görünecek.")
    elif selected_page == "İş Atama":
        st.write("Saha personeline iş atama formu.")
    elif selected_page == "Raporlar":
        st.write("Detaylı performans analizleri.")
