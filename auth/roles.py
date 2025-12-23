ROLE_ADMIN = "Admin"
ROLE_YONETICI = "Yönetici"
ROLE_MUDUR = "Müdür"
ROLE_SAHA = "Saha Personeli"

ALL_ROLES = [ROLE_ADMIN, ROLE_YONETICI, ROLE_MUDUR, ROLE_SAHA]

def has_role(required_roles):
    import streamlit as st
    if st.session_state.get("logged_in") and st.session_state.get("user_role") in required_roles:
        return True
    return False

def is_admin():
    import streamlit as st
    return st.session_state.get("user_role") == ROLE_ADMIN

def can_edit_jobs():
    import streamlit as st
    return st.session_state.get("user_role") in [ROLE_ADMIN, ROLE_YONETICI, ROLE_MUDUR]
