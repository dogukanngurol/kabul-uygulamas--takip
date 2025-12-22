import streamlit as st
from src.utils.roleUtils import PAGE_PERMISSIONS

def render_sidebar():
    st.sidebar.title("İş Takip Sistemi")
    user_role = st.session_state.user["role"]
    
    st.sidebar.write(f"Hoşgeldin, **{user_role}**")
    
    # Role göre menü filtreleme
    available_pages = [
        page for page, roles in PAGE_PERMISSIONS.items() 
        if user_role in roles
    ]
    
    selection = st.sidebar.radio("Menü", available_pages)
    
    if st.sidebar.button("Güvenli Çıkış"):
        from src.store.AuthContext import logout
        logout()
        
    return selection
