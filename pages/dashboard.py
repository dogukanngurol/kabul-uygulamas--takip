import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db.database import get_connection
from utils.helpers import get_greeting
from utils.constants import STATUS_TAMAMLANDI

def dashboard_page():
    if st.session_state.user_role not in ["Admin", "Yönetici", "Müdür"]:
        st.error("Bu sayfayı görüntüleme yetkiniz yok.")
        return

    st.title(f"{get_greeting()}, {st.session_state.user_name}")
    st.subheader("Genel Performans Göstergeleri")

    conn = get_connection()
    
    # Veri Çekme
    df_jobs = pd.read_sql_query("SELECT * FROM jobs", conn)
    df_users = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()

    if df_jobs.empty:
        st.info("Henüz analiz edilecek veri bulunmuyor.")
        return

    df_jobs['created_at'] = pd.to_datetime(df_jobs['created_at'])
    now = datetime.now()
    
    # Filtreler
    today = df_jobs[df_jobs['created_at'].dt.date == now.date()]
    this_week = df_jobs[df_jobs['created_at'] > (now - timedelta(days=7))]
    this_month = df_jobs[df_jobs['created_at'] > (now - timedelta(days=30))]

    # Metric Satırı 1
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Toplam İş", len(df_jobs))
    with col2:
        completed_count = len(df_jobs[df_jobs['status'] == STATUS_TAMAMLANDI])
        st.metric("Tamamlanan", completed_count)
    with col3:
        st.metric("Aktif Personel", len(df_users))
    with col4:
        pending_count = len(df_jobs[df_jobs['status'] != STATUS_TAMAMLANDI])
        st.metric("Bekleyen İş", pending_count)

    st.divider()

    # Metric Satırı 2 (Zaman Bazlı)
    st.write("### İş Akış İstatistikleri")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Bugün Açılan", len(today))
    with c2:
        st.metric("Bu Hafta Açılan", len(this_week))
    with c3:
        st.metric("Bu Ay Açılan", len(this_month))

    # Basit Grafik
    if not df_jobs.empty:
        st.write("### Şehirlere Göre İş Dağılımı")
        city_counts = df_jobs['city'].value_counts()
        st.bar_chart(city_counts)

if __name__ == "__main__":
    dashboard_page()
