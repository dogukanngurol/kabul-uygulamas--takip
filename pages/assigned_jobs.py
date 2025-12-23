import streamlit as st
import pandas as pd
from db.database import get_connection
from utils.constants import STATUSES
from utils.export_excel import download_button
from datetime import datetime

def assigned_jobs_page():
    st.title("Atanan İşler Listesi")

    conn = get_connection()
    
    # Yetki bazlı veri çekme
    if st.session_state.user_role in ["Admin", "Yönetici", "Müdür"]:
        query = """
            SELECT j.*, u.name as staff_name 
            FROM jobs j 
            LEFT JOIN users u ON j.assigned_to = u.id
        """
        df = pd.read_sql_query(query, conn)
    else:
        query = """
            SELECT j.*, u.name as staff_name 
            FROM jobs j 
            LEFT JOIN users u ON j.assigned_to = u.id 
            WHERE j.assigned_to = ?
        """
        df = pd.read_sql_query(query, conn, params=(st.session_state.user_id,))

    # Filtreleme Alanı
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.multiselect("Duruma Göre Filtrele", options=STATUSES)
    with col2:
        city_filter = st.multiselect("Şehre Göre Filtrele", options=df['city'].unique() if not df.empty else [])

    if not df.empty:
        if status_filter:
            df = df[df['status'].isin(status_filter)]
        if city_filter:
            df = df[df['city'].isin(city_filter)]

        st.dataframe(df, use_container_width=True)

        # Durum Güncelleme Bölümü
        st.divider()
        st.subheader("İş Durumu Güncelle")
        
        selected_job_id = st.selectbox("Güncellenecek İş ID", options=df['id'].tolist())
        new_status = st.selectbox("Yeni Durum", options=STATUSES)
        
        if st.button("Durumu Güncelle"):
            c = conn.cursor()
            comp_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_status == "Tamamlandı" else None
            c.execute("""
                UPDATE jobs 
                SET status = ?, completed_at = ? 
                WHERE id = ?
            """, (new_status, comp_date, selected_job_id))
            conn.commit()
            st.success(f"İş ID {selected_job_id} başarıyla güncellendi.")
            st.rerun()

        # Dışa Aktar
        st.divider()
        download_button("jobs", "Tüm İşleri Excel Olarak İndir")
    else:
        st.info("Görüntülenecek iş kaydı bulunamadı.")
    
    conn.close()

if __name__ == "__main__":
    assigned_jobs_page()
