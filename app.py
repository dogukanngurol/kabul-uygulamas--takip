import streamlit as st
from db.database import create_tables
from auth.login import login_page, logout
from utils.helpers import get_greeting

st.set_page_config(page_title="Anatoli Bilişim", layout="wide")

create_tables()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "user_role" not in st.session_state:
    st.session_state.user_role = ""

if not st.session_state.logged_in:
    login_page()
else:
    st.sidebar.title("Anatoli Bilişim")
    st.sidebar.markdown(f"### {get_greeting()}, {st.session_state.user_name}")
    st.sidebar.caption(f"Rol: {st.session_state.user_role}")
    st.sidebar.divider()

    menu = ["Ana Panel", "İş Takibi", "Envanter & Zimmet", "Raporlar"]
    
    if st.session_state.user_role in ["Admin", "Yönetici"]:
        menu.append("Kullanıcı Yönetimi")

    choice = st.sidebar.radio("Menü", menu)

    if choice == "Ana Panel":
        st.header("Genel Durum Paneli")
        st.write(f"Hoş geldiniz, {st.session_state.user_name}. Lütfen soldaki menüden işlem seçin.")
        
    elif choice == "İş Takibi":
        from pages.jobs import jobs_page
        jobs_page()
        
    elif choice == "Envanter & Zimmet":
        from pages.inventory import inventory_page
        inventory_page()
        
    elif choice == "Raporlar":
        from pages.reports import reports_page
        reports_page()
        
    elif choice == "Kullanıcı Yönetimi":
        from pages.admin import admin_page
        admin_page()

    st.sidebar.divider()
    if st.sidebar.button("Güvenli Çıkış"):
        logout()
