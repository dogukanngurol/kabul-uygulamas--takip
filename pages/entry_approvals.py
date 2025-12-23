import streamlit as st
import pandas as pd
from db.database import get_connection
from utils.constants import STATUS_GIRIS_MAILI_BEKLIYOR, STATUS_ATANDI
from utils.export_excel import download_button

def entry_approvals_page():
    if st.session_state.user_role not in ["Admin", "Yönetici", "Müdür"]:
        st.error("Bu sayfayı görüntüleme yetkiniz yok.")
        return

    st.title("Giriş Onay Paneli")

    conn = get_connection()
    query = f"""
        SELECT j.id, j.title, j.city, u.name as staff_name, j.created_at, j.status
        FROM jobs j
        LEFT JOIN users u ON j.assigned_to = u.id
        WHERE j.status = '{STATUS_GIRIS_MAILI_BEKLIYOR}'
    """
    df = pd.read_sql_query(query, conn)

    if not df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            staff_filter = st.multiselect("Personel Filtrele", options=df['staff_name'].unique())
        with col2:
            city_filter = st.multiselect("Şehir Filtrele", options=df['city'].unique())
        with col3:
            df['created_at_dt'] = pd.to_datetime(df['created_at']).dt.date
            date_filter = st.date_input("Tarih Filtrele", value=None)

        if staff_filter:
            df = df[df['staff_name'].isin(staff_filter)]
        if city_filter:
            df = df[df['city'].isin(city_filter)]
        if date_filter:
            df = df[df['created_at_dt'] == date_filter]

        st.subheader("Onay Bekleyen İşler")
        for index, row in df.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 2])
                c1.write(f"ID: {row['id']}")
                c2.write(f"Başlık: {row['title']}")
                c3.write(f"Şehir: {row['city']}")
                c4.write(f"Personel: {row['staff_name']}")
                
                if c5.button(f"Kabul Yap - {row['id']}", key=f"btn_{row['id']}"):
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE jobs SET status = ? WHERE id = ?",
                        (STATUS_ATANDI, row['id'])
                    )
                    conn.commit()
                    st.success(f"İş ID {row['id']} tekrar atandı.")
                    st.rerun()
                st.divider()

        st.sidebar.divider()
        download_button("jobs", "Filtrelenmiş Listeyi Excel Yap")
    else:
        st.info("Giriş maili bekleyen iş bulunamadı.")
    
    conn.close()

if __name__ == "__main__":
    entry_approvals_page()
