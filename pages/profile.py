import streamlit as st
from db.database import get_connection

def profile_page():
    if not st.session_state.logged_in:
        st.error("Lütfen önce giriş yapın.")
        return

    st.title("Profil Bilgilerim")
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT name, username, role, phone FROM users WHERE id = ?", (st.session_state.user_id,))
    user_data = c.fetchone()
    
    if user_data:
        name, username, role, current_phone = user_data
        
        st.subheader(f"Hoş geldin, {name}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Ad Soyad", value=name, disabled=True)
            st.text_input("Kullanıcı Adı", value=username, disabled=True)
        with col2:
            st.text_input("Mevcut Rol", value=role, disabled=True)
            new_phone = st.text_input("Telefon Numarası", value=current_phone if current_phone else "")

        if st.button("Bilgileri Güncelle"):
            try:
                c.execute("UPDATE users SET phone = ? WHERE id = ?", (new_phone, st.session_state.user_id))
                conn.commit()
                st.success("Profil bilgileriniz başarıyla güncellendi.")
            except Exception as e:
                st.error(f"Güncelleme sırasında bir hata oluştu: {e}")
    else:
        st.error("Kullanıcı bilgileri alınamadı.")
    
    conn.close()

if __name__ == "__main__":
    profile_page()
