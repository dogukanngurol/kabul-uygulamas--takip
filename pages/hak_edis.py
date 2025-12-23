import streamlit as st
import pandas as pd
from db.database import get_connection
from utils.constants import STATUS_HAK_EDIS_BEKLEMEDE, STATUS_HAK_EDIS_ALINDI, STATUS_TAMAMLANDI
from utils.export_excel import download_button

def hak_edis_page():
    if st.session_state.user_role not in ["Admin", "Yönetici", "Müdür"]:
        st.error("Bu sayfayı görüntüleme yetkiniz yok.")
        return

    st.title("Hak Ediş Yönetimi")

    conn = get_connection()
    
    query = f"""
        SELECT j.id, j.title, j.city, u.name as staff_name, j.status, j.completed_at
        FROM jobs j
        LEFT JOIN users u ON j.assigned_to = u.id
        WHERE j.status IN ('{STATUS_HAK_EDIS_BEKLEMEDE}', '{STATUS_HAK_EDIS_ALINDI}', '{STATUS_TAMAMLANDI}')
    """
    df = pd.read_sql_query(query, conn)

    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.multiselect("Hak Ediş Durumu", options=[STATUS_HAK_EDIS_BEKLEMEDE, STATUS_HAK_EDIS_ALINDI])
        with col2:
            staff_filter = st.multiselect("Personel Filtrele", options=df['staff_name'].unique())

        if status_filter:
            df = df[df['status'].isin(status_filter)]
        if staff_filter:
            df = df[df['staff_name'].isin(staff_filter)]

        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("Durum Güncelle")
        
        with st.form("hakedis_update_form"):
            selected_id = st.selectbox("İş ID Seçin", options=df['id'].tolist())
            new_status = st.selectbox("Yeni Hak Ediş Durumu", options=[STATUS_HAK_EDIS_BEKLEMEDE, STATUS_HAK_EDIS_ALINDI])
            submit = st.form_submit_button("Güncelle")

            if submit:
                cursor = conn.cursor()
                cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (new_status, selected_id))
                conn.commit()
                st.success(f"İş ID {selected_id} durumu {new_status} olarak güncellendi.")
                st.rerun()

        st.sidebar.divider()
        download_button("jobs", "Hak Ediş Listesini Excel Olarak İndir")
    else:
        st.info("Hak ediş aşamasında olan iş bulunamadı.")
    
    conn.close()

if __name__ == "__main__":
    hak_edis_page()
