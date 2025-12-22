import streamlit as st

def init_auth():
    if "user" not in st.session_state:
        st.session_state.user = None

def login(role):
    st.session_state.user = {"name": "Demo Kullanıcı", "role": role}
    st.rerun()

def logout():
    st.session_state.user = None
    st.rerun()
