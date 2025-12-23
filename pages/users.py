import streamlit as st
import pandas as pd
import hashlib
from db.database import get_connection

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def users_page():
    if st.session_state.user_role not in ["Admin", "Yönetici"]:
        st.error("Bu sayfaya erişim yetkiniz yoktur.")
        return

    st.title("Kullanıcı Yönetimi")

    # Kullanıcı Ekleme Formu
    with st.expander("Yeni Kullanıcı Ekle", expanded=False):
        with st.form("new_user_form", clear_on_submit=True):
            new_name = st.text_input("Ad Soyad")
            new_username = st.text_input("Kullanıcı Adı")
            new_password = st.text_input("Şifre", type="password")
            new_role = st.selectbox("Rol", ["Admin", "Yönetici", "Müdür", "Saha Personeli"])
            
            submit_user = st.form_submit_button("Kullanıcıyı Kaydet")
            
            if submit_user:
                if new_name and new_username and new_password:
                    try:
                        conn = get_connection()
                        c = conn.cursor()
                        hashed_pw = hash_password(new_password)
                        c.execute("""
                            INSERT INTO users (name, username, password, role) 
                            VALUES (?, ?, ?, ?)
                        """, (new_name, new_username, hashed_pw, new_role))
                        conn.commit()
                        conn.close()
                        st.success(f"{new_name} kullanıcısı başarıyla eklendi.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")
                else:
                    st.warning("Lütfen tüm alanları doldurun.")

    st.divider()

    # Kullanıcı Listesi ve Silme İşlemi
    st.subheader("Mevcut Kullanıcılar")
    conn = get_connection()
    df_users = pd.read_sql_query("SELECT id, name, username, role FROM users", conn)
    
    if not df_users.empty:
        for index, row in df_users.iterrows():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            col1.write(row["name"])
            col2.write(row["username"])
            col3.write(row["role"])
            
            # Kendi kullanıcısını silmeyi engelle
            if row["id"] == st.session_state.user_id:
                col4.write("---")
            else:
                if col4.button("Sil", key=f"del_{row['id']}"):
                    c = conn.cursor()
                    c.execute("DELETE FROM users WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.rerun()
            st.divider()
    else:
        st.info("Sistemde kayıtlı kullanıcı bulunamadı.")
    
    conn.close()

if __name__ == "__main__":
    users_page()
