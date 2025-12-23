import pandas as pd
import io
import streamlit as st
from db.database import get_connection

def export_table_to_excel(table_name):
    conn = get_connection()
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=table_name)
    
    processed_data = output.getvalue()
    return processed_data

def download_button(table_name, label):
    data = export_table_to_excel(table_name)
    st.download_button(
        label=label,
        data=data,
        file_name=f"{table_name}_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
