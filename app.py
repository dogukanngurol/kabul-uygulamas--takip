import streamlit as st
from db.database import create_tables
from auth.login import login_page, logout

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
    st.sidebar.markdown(f"**{st.session_state.user_name}**")
    st.sidebar.caption(f"Rol: {st.session_state.user_role}")
    st.sidebar.divider()

    menu_options = {
        "Ana Panel": "dashboard",
        "İş Atama": "job_assign",
        "Giriş Onayları": "entry_approvals",
        "TT Onayları": "tt_approvals",
        "Atanan İşler": "assigned_jobs",
        "Hak Ediş": "hak_edis",
        "Tamamlananlar": "completed_jobs",
        "Envanter": "inventory",
        "Kullanıcılar": "users",
        "Profil": "profile"
    }
    
    choice = st.sidebar.selectbox("Menü", list(menu_options.keys()))

    if choice == "Ana Panel":
        from pages.dashboard import dashboard_page
        dashboard_page()
    elif choice == "İş Atama":
        from pages.job_assign import job_assign_page
        job_assign_page()
    elif choice == "Giriş Onayları":
        from pages.entry_approvals import entry_approvals_page
        entry_approvals_page()
    elif choice == "TT Onayları":
        from pages.tt_approvals import tt_approvals_page
        tt_approvals_page()
    elif choice == "Atanan İşler":
        from pages.assigned_jobs import assigned_jobs_page
        assigned_jobs_page()
    elif choice == "Hak Ediş":
        from pages.hak_edis import hak_edis_page
        hak_edis_page()
    elif choice == "Tamamlananlar":
        from pages.completed_jobs import completed_jobs_page
        completed_jobs_page()
    elif choice == "Envanter":
        from pages.inventory import inventory_page
        inventory_page()
    elif choice == "Kullanıcılar":
        from pages.users import users_page
        users_page()
    elif choice == "Profil":
        from pages.profile import profile_page
        profile_page()

    st.sidebar.divider()
    if st.sidebar.button("Güvenli Çıkış"):
        logout()
