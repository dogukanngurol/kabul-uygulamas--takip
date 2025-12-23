import streamlit as st
from datetime import datetime
from utils.constants import (
    STATUS_ATANDI, 
    STATUS_GIRIS_MAILI_BEKLIYOR, 
    STATUS_TAMAMLANDI, 
    STATUS_TT_ONAY_BEKLIYOR, 
    STATUS_RET, 
    STATUS_HAK_EDIS_BEKLEMEDE, 
    STATUS_HAK_EDIS_ALINDI
)

def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Günaydın"
    elif 12 <= hour < 18:
        return "İyi Günler"
    elif 18 <= hour < 22:
        return "İyi Akşamlar"
    else:
        return "İyi Geceler"

def format_date(date_str):
    if not date_str:
        return "-"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return date_str

def get_status_color(status):
    colors = {
        STATUS_ATANDI: "blue",
        STATUS_GIRIS_MAILI_BEKLIYOR: "orange",
        STATUS_TAMAMLANDI: "green",
        STATUS_TT_ONAY_BEKLIYOR: "violet",
        STATUS_RET: "red",
        STATUS_HAK_EDIS_BEKLEMEDE: "gray",
        STATUS_HAK_EDIS_ALINDI: "rainbow"
    }
    return colors.get(status, "black")

def render_status_badge(status):
    color = get_status_color(status)
    st.markdown(f":{color}[**{status}**]")
