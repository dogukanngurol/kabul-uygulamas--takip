import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Anatoli Bilişim", layout="wide")

# --- ÖRNEK VERİ SETİ (Veritabanı yerine şimdilik simülasyon) ---
if 'is_listesi' not in st.session_state:
    st.session_state['is_listesi'] = pd.DataFrame([
        {"İş Başlığı": "Saha Kurulumu", "Personel": "Ahmet Yılmaz", "Şehir": "İstanbul", "Durum": "Bekliyor", "Tarih": "2023-10-27"},
        {"İş Başlığı": "Arıza Onarımı", "Personel": "Mehmet Demir", "Şehir": "Ankara", "Durum": "Tamamlandı", "Tarih": "2023-10-26"}
    ])

# --- 81 İL LİSTESİ ---
sehirler = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
]

# --- EXCEL RAPOR FONKSİYONU ---
def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Rapor')
    writer.close()
    processed_data = output.getvalue()
    return processed_data

# --- GİRİŞ KONTROLÜ (Basitleştirilmiş) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("Anatoli Bilişim Yönetim Paneli")
    user = st.text_input("Kullanıcı Adı")
    pw = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        st.session_state['logged_in'] = True
        st.session_state['user'] = user
        st.rerun()
else:
    # --- YAN MENÜ ---
    with st.sidebar:
        st.title("Anatoli Bilişim")
        st.write(f"Kullanıcı: **{st.session_state['user']}**")
        menu = st.radio("Menü", ["Ana Sayfa", "İş Ataması", "Atanan İşler", "Çıkış"])

    # --- EKRANLAR ---
    if menu == "Ana Sayfa":
        st.header("Genel Durum")
        col1, col2 = st.columns(2)
        col1.metric("Toplam İş", len(st.session_state['is_listesi']))
        col2.metric("Tamamlanan", len(st.session_state['is_listesi'][st.session_state['is_listesi']['Durum'] == "Tamamlandı"]))

    elif menu == "İş Ataması":
        st.header("Yeni İş Emri Oluştur")
        with st.form("is_form"):
            baslik = st.text_input("İş Başlığı")
            pers = st.selectbox("Saha Personeli", ["Ahmet Yılmaz", "Mehmet Demir", "Caner Öz"])
            city = st.selectbox("Şehir", sehirler)
            submit = st.form_submit_button("İşi Ata")
            
            if submit:
                yeni_is = {"İş Başlığı": baslik, "Personel": pers, "Şehir": city, "Durum": "Bekliyor", "Tarih": str(datetime.now().date())}
                st.session_state['is_listesi'] = pd.concat([st.session_state['is_listesi'], pd.DataFrame([yeni_is])], ignore_index=True)
                st.success("İş başarıyla atandı!")

    elif menu == "Atanan İşler":
        st.header("Atanan İşler ve Raporlama")
        
        # Filtreleme Alanı
        df = st.session_state['is_listesi']
        f_sehir = st.multiselect("Şehre Göre Filtrele", options=df["Şehir"].unique())
        
        filtered_df = df[df["Şehir"].isin(f_sehir)] if f_sehir else df
        
        # Tabloyu Göster
        st.dataframe(filtered_df, use_container_width=True)
        
        # EXCEL İNDİRME BUTONU
        excel_data = to_excel(filtered_df)
        st.download_button(
            label="📊 Excel Raporu İndir",
            data=excel_data,
            file_name=f'anatoli_is_raporu_{datetime.now().strftime("%Y%m%d")}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    elif menu == "Çıkış":
        st.session_state['logged_in'] = False
        st.rerun()
