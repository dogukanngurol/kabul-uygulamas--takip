import streamlit as st
import sqlite3
from datetime import datetime
from db.database import get_connection
from data.cities import TURKIYE_ILLER
from utils.constants import STATUS_ATANDI

def job_assign_page():
    if st.session_state.user_role not in ["Admin", "Yönetici", "Müdür"]:
        st.error("Bu sayfaya erişim yetkiniz yoktur.")
        return

    st.title("Yeni İş Atama Paneli")

    with st.form("job_assign_form", clear_on_submit=True):
        title = st.text_input("İş Başlığı *")
        detail = st.text_area("İş Detayı")
        city = st.selectbox("Şehir", options=TURKIYE_ILLER)
        
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM users WHERE role = 'Saha Personeli'")
        staff_data = c.fetchall()
        conn.close()

        staff_options = {row[1]: row[0] for row in staff_data}
        assigned_name = st.selectbox("Atanacak Personel", options=list(staff_options.keys()))

        submit = st.form_submit_button("İşi Ata")

        if submit:
            if not title:
                st.error("Başlık alanı boş geçilemez!")
            elif not assigned_name:
                st.error("Atanacak bir saha personeli bulunamadı!")
            else:
                try:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO jobs (title, detail, city, assigned_to, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        title, 
                        detail, 
                        city, 
                        staff_options[assigned_name], 
                        STATUS_ATANDI, 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    conn.commit()
                    conn.close()
                    st.success(f"İş başarıyla '{assigned_name}' personeline atandı.")
                except Exception as e:
                    st.error(f"Veritabanı hatası: {e}")

if __name__ == "__main__":
    job_assign_page()
