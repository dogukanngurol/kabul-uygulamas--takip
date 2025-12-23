import streamlit as st

def is_logged_in():
    return st.session_state.get("logged_in", False)

def is_admin():
    return st.session_state.get("user_role") == "Admin"

def is_manager():
    return st.session_state.get("user_role") in ["Admin", "Yönetici", "Müdür"]

def is_field_staff():
    return st.session_state.get("user_role") == "Saha Personeli"

def can_assign_jobs():
    return st.session_state.get("user_role") in ["Admin", "Yönetici"]

def can_view_all_jobs():
    return st.session_state.get("user_role") in ["Admin", "Yönetici", "Müdür"]

def can_edit_inventory():
    return st.session_state.get("user_role") in ["Admin", "Yönetici"]

def can_approve_hak_edis():
    return st.session_state.get("user_role") in ["Admin", "Yönetici"]
