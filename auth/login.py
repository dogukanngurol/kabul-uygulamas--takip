import streamlit as st
import hashlib
from db.database import get_connection

def login_page():
    st.title("İşletme Yönetim Sistemi Giriş")
    
    with st.form("login_form"):
        email = st.text_input("E-posta")
        password = st.text_input("Şifre", type="password")
        submit_button = st.form_submit_button("Giriş Yap")

        if submit_button:
            if email and password:
                pwd_hash = hashlib.sha256(password.encode()).hexdigest()
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                    SELECT id, name, role FROM users 
                    WHERE email = ? AND password = ?
                """, (email, pwd_hash))
                user = c.fetchone()
                conn.close()

                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.user_name = user[1]
                    st.session_state.user_role = user[2]
                    st.success(f"Hoş geldiniz, {user[1]}")
                    st.rerun()
                else:
                    st.error("E-posta veya şifre hatalı.")
            else:
                st.warning("Lütfen tüm alanları doldurun.")

def logout():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.user_role = ""
    st.rerun()
