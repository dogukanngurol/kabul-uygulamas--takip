import streamlit as st
import pandas as pd
from datetime import datetime
from db.database import get_connection
from utils.export_excel import download_button

def inventory_page():
    st.title("Envanter ve Zimmet Yönetimi")

    conn = get_connection()
    
    if st.session_state.user_role in ["Admin", "Yönetici", "Müdür"]:
        query = """
            SELECT i.id, i.item_name, u1.name as staff_name, u2.name as assigned_by, i.created_at 
            FROM inventory i
            LEFT JOIN users u1 ON i.assigned_to = u1.id
            LEFT JOIN users u2 ON i.assigned_by = u2.id
        """
        df = pd.read_sql_query(query, conn)
    else:
        query = """
            SELECT i.id, i.item_name, u2.name as assigned_by, i.created_at 
            FROM inventory i
            LEFT JOIN users u2 ON i.assigned_by = u2.id
            WHERE i.assigned_to = ?
        """
        df = pd.read_sql_query(query, conn, params=(st.session_state.user_id,))

    if st.session_state.user_role in ["Admin", "Yönetici"]:
        with st.expander("Yeni Zimmet Kaydı Oluştur", expanded=False):
            with st.form("inventory_form", clear_on_submit=True):
                item_name = st.text_input("Malzeme / Cihaz Adı")
                
                c = conn.cursor()
                c.execute("SELECT id, name FROM users WHERE role = 'Saha Personeli'")
                staff_members = c.fetchall()
                staff_options = {s[1]: s[0] for s in staff_members}
                
                assigned_to_name = st.selectbox("Zimmetlenecek Personel", options=list(staff_options.keys()))
                submit = st.form_submit_button("Zimmetle")

                if submit:
                    if item_name and assigned_to_name:
                        try:
                            c.execute("""
                                INSERT INTO inventory (item_name, assigned_to, assigned_by, created_at)
                                VALUES (?, ?, ?, ?)
                            """, (item_name, staff_options[assigned_to_name], st.session_state.user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                            conn.commit()
                            st.success(f"{item_name} başarıyla {assigned_to_name} üzerine zimmetlendi.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Hata: {e}")
                    else:
                        st.warning("Lütfen tüm alanları doldurun.")

    st.divider()

    st.subheader("Zimmet Listesi")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.divider()
        download_button("inventory", "Envanter Listesini Excel Olarak İndir")
    else:
        st.info("Henüz kayıtlı zimmet bulunmuyor.")

    conn.close()

if __name__ == "__main__":
    inventory_page()
