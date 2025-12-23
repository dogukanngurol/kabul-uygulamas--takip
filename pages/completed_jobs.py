import streamlit as st
import pandas as pd
from db.database import get_connection
from utils.constants import STATUS_TAMAMLANDI, STATUS_HAK_EDIS_ALINDI
from utils.export_excel import download_button

def completed_jobs_page():
    st.title("Tamamlanan İşler")

    conn = get_connection()
    
    query = f"""
        SELECT j.id, j.title, j.city, u.name as staff_name, j.created_at, j.completed_at, j.status
        FROM jobs j
        LEFT JOIN users u ON j.assigned_to = u.id
        WHERE j.status IN ('{STATUS_TAMAMLANDI}', '{STATUS_HAK_EDIS_ALINDI}')
    """
    df = pd.read_sql_query(query, conn)

    if not df.empty:
        # Filtreler
        col1, col2, col3 = st.columns(3)
        with col1:
            staff_filter = st.multiselect("Personel", options=df['staff_name'].unique())
        with col2:
            city_filter = st.multiselect("Şehir", options=df['city'].unique())
        with col3:
            df['date_only'] = pd.to_datetime(df['completed_at']).dt.date
            date_filter = st.date_input("Tamamlama Tarihi", value=None)

        if staff_filter:
            df = df[df['staff_name'].isin(staff_filter)]
        if city_filter:
            df = df[df['city'].isin(city_filter)]
        if date_filter:
            df = df[df['date_only'] == date_filter]

        # Tablo Görünümü
        st.dataframe(df.drop(columns=['date_only']), use_container_width=True)

        st.subheader("İş Detayları ve Dosyalar")
        selected_job_id = st.selectbox("Detayını görmek istediğiniz İş ID seçin", options=df['id'].tolist())
        
        if selected_job_id:
            # Örnek dosya/fotoğraf listeleme mantığı (DB'de dosya yolu saklandığı varsayımıyla)
            c = conn.cursor()
            c.execute("SELECT detail FROM jobs WHERE id = ?", (selected_job_id,))
            job_detail = c.fetchone()[0]
            
            st.info(f"İş Detayı: {job_detail}")
            
            # Statik klasör yapısı veya DB'den gelen yollar için placeholder
            st.write("📁 **İlgili Fotoğraflar ve Belgeler**")
            st.caption("Bu bölümdeki dosyalar sunucu üzerindeki /uploads/ klasöründen eşleştirilir.")
            
            # Örnek görsel gösterimi (Eğer saha personeli yüklediyse)
            # st.image(f"uploads/{selected_job_id}_photo.jpg", caption="Saha Fotoğrafı")

        st.divider()
        download_button("jobs", "Tamamlanan Tüm İşleri Excel Olarak İndir")
    else:
        st.info("Henüz tamamlanmış bir iş bulunmuyor.")
    
    conn.close()

if __name__ == "__main__":
    completed_jobs_page()
