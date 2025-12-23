import streamlit as st
from db.database import get_connection
from data.cities import TURKIYE_ILLER
from utils.constants import STATUS_ATANDI
from utils.permissions import can_assign_jobs
from datetime import datetime

def job_assign_page():
    if not can_assign_jobs():
        st.error("Bu işlemi yapmak için yetkiniz bulunmamaktadır.")
        return

    st.title("Yeni İş Atama")

    with st.form("job_assign_form"):
        title = st.text_input("İş Başlığı")
        detail = st.text_area("İş Detayı")
        city = st.selectbox("Şehir", options=TURKIYE_ILLER)
        
        # Personel Listesi (Saha Personeli Rolündekiler)
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name FROM users WHERE role = 'Saha Personeli'")
        staff_members = c.fetchall()
        conn.close()
        
        staff_options = {s[1]: s[0] for s in staff_members}
        assigned_name = st.selectbox("Personel Seçin", options=list(staff_options.keys()))
        
        submit = st.form_submit_button("İşi Ata")

        if submit:
            if title and assigned_name:
                try:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO jobs (title, detail, city, assigned_to, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (title, detail, city, staff_options[assigned_name], STATUS_ATANDI, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success(f"İş başarıyla {assigned_name} adlı personele atandı.")
                except Exception as e:
                    st.error(f"Hata oluştu: {e}")
            else:
                st.warning("Lütfen başlık ve personel alanlarını doldurun.")

if __name__ == "__main__":
    job_assign_page()
