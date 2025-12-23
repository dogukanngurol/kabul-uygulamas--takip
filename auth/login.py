import streamlit as st
import hashlib
from db.database import get_connection

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def login_page():
    st.title("Anatoli Bilişim - Giriş")

    with st.form("login_form"):
        email = st.text_input("Kullanıcı Adı (Email)")
        password = st.text_input("Şifre", type="password")
        submit = st.form_submit_button("Giriş Yap")

        if submit:
            conn = get_connection()
            cursor = conn.cursor()

            hashed_pw = hash_password(password)

            cursor.execute(
                """
                SELECT id, name, role
                FROM users
                WHERE email = ? AND password = ?
                """,
                (email, hashed_pw)
            )

            user = cursor.fetchone()
            conn.close()

            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.session_state.user_name = user[1]
                st.session_state.user_role = user[2]
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")

def logout():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.user_role = ""
    st.rerun()
