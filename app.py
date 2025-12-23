import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. SİSTEM YAPILANDIRMASI VE VERİ SETİ ---
st.set_page_config(page_title="Saha İş Takip Otomasyonu", layout="wide")

if 'db_jobs' not in st.session_state:
    st.session_state.db_jobs = pd.DataFrame(columns=[
        "Saha ID", "Personel", "Acıklama", "Durum", "Tarih", "Foto_RAR", "Red_Nedeni"
    ])

if 'users' not in st.session_state:
    st.session_state.users = pd.DataFrame([
        {"İsim": "Admin", "Mail": "admin@sirket.com", "Rol": "Admin"},
        {"İsim": "Saha1", "Mail": "saha1@sirket.com", "Rol": "Saha Personeli"}
    ])

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""

# --- 2. YARDIMCI FONKSİYONLAR ---
def get_greeting(name):
    hour = datetime.now().hour
    if 8 <= hour < 12: return f"Günaydın {name} İyi Çalışmalar"
    elif 12 <= hour < 18: return f"İyi Günler {name} İyi Çalışmalar"
    elif 18 <= hour < 24: return f"İyi Akşamlar {name} İyi Çalışmalar"
    else: return f"İyi Geceler {name} İyi Çalışmalar"

def get_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 3. GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.title("Saha Operasyon Girişi")
    with st.form("login_form"):
        u = st.text_input("Kullanıcı Adı")
        r = st.selectbox("Rolünüz", ["Admin", "Yönetici", "Müdür", "Saha Personeli"])
        if st.form_submit_button("Giriş Yap"):
            st.session_state.logged_in = True
            st.session_state.role = r
            st.session_state.username = u
            st.rerun()

# --- 4. ANA PANEL ---
else:
    # Sidebar Menü Tasarımı
    st.sidebar.title("MENÜ")
    if st.session_state.role == "Saha Personeli":
        menu = ["Anasayfa", "Üzerime Atanan İşler", "İş Geçmişi", "Profil", "Çıkış"]
    else:
        menu = ["Anasayfa", "İş Ataması", "İzin Maili Bekleyenler", "Geri Gelen Atamalar", 
                "Tamamlanan İşler", "TT Onayı Bekleyen İşler", "Hak Ediş", "Kullanıcı Kontrol", "Profil", "Çıkış"]
    
    choice = st.sidebar.radio("Sayfa Seçin", menu)

    # --- ANASAYFA ---
    if choice == "Anasayfa":
        st.header(get_greeting(st.session_state.username))
        df = st.session_state.db_jobs
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Toplam İş", len(df))
        c2.metric("Atanan İş", len(df[df["Durum"] == "Yeni Atama"]))
        c3.metric("İzin Bekleyen", len(df[df["Durum"] == "İzin Maili Atılmalı"]))
        c4.metric("Geri Gelen", len(df[df["Durum"].isin(["Giriş Yapılamadı", "Mal Sahibi Tepkili"])]))
        c5.metric("TT Onay", len(df[df["Durum"] == "TT Onay Bekler"]))

    # --- SAHA PERSONELİ EKRANLARI ---
    elif choice == "Üzerime Atanan İşler":
        st.subheader("Üzerime Atanan İşler")
        my_jobs = st.session_state.db_jobs[st.session_state.db_jobs["Personel"] == st.session_state.username]
        active = my_jobs[~my_jobs["Durum"].isin(["Çalışma Tamamlandı", "Hak Ediş Alındı"])]
        
        if not active.empty:
            target = st.selectbox("İş Seç", active["Saha ID"])
            status = st.selectbox("Durum", ["Giriş Yapılamadı", "İzin Maili Atılmalı", "Çalışma Tamamlandı", "Mal Sahibi Tepkili"])
            desc = st.text_area("Açıklama")
            file = st.file_uploader("Fotoğraflar (RAR)", type="rar")
            if st.button("Atamayı Gönder"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == target].index
                st.session_state.db_jobs.loc[idx, "Durum"] = status
                st.session_state.db_jobs.loc[idx, "Acıklama"] = desc
                st.success("İş başarıyla güncellendi.")
        else: st.info("Bekleyen işiniz yok.")

    elif choice == "İş Geçmişi":
        st.subheader("İş Geçmişim")
        hist = st.session_state.db_jobs[st.session_state.db_jobs["Personel"] == st.session_state.username]
        st.dataframe(hist.head(10))
        st.download_button("Excel İndir", get_excel(hist), "gecmis.xlsx")

    # --- YÖNETİM EKRANLARI ---
    elif choice == "İş Ataması":
        st.subheader("Yeni İş Atama")
        sid = st.text_input("Saha ID")
        det = st.text_area("İş Detayı")
        per = st.selectbox("Personel", st.session_state.users[st.session_state.users["Rol"]=="Saha Personeli"]["İsim"])
        if st.button("Atamayı Yap"):
            new = {"Saha ID": sid, "Personel": per, "Acıklama": det, "Durum": "Yeni Atama", "Tarih": datetime.now()}
            st.session_state.db_jobs = pd.concat([st.session_state.db_jobs, pd.DataFrame([new])], ignore_index=True)
            st.success("Atama yapıldı.")

    elif choice == "İzin Maili Bekleyenler":
        df_izin = st.session_state.db_jobs[st.session_state.db_jobs["Durum"] == "İzin Maili Atılmalı"]
        st.table(df_izin.head(10))
        if not df_izin.empty:
            sid = st.selectbox("Saha ID", df_izin["Saha ID"])
            if st.button("Kabul Alınabilir"):
                st.session_state.db_jobs.loc[st.session_state.db_jobs["Saha ID"] == sid, "Durum"] = "Yeni Atama"
                st.rerun()

    elif choice == "Geri Gelen Atamalar":
        df_geri = st.session_state.db_jobs[st.session_state.db_jobs["Durum"].isin(["Giriş Yapılamadı", "Mal Sahibi Tepkili"])]
        st.table(df_geri.head(10))
        if not df_geri.empty:
            sid = st.selectbox("Saha ID", df_geri["Saha ID"])
            if st.button("Kabul Alınabilir (Yeniden Ata)"):
                st.session_state.db_jobs.loc[st.session_state.db_jobs["Saha ID"] == sid, "Durum"] = "Yeni Atama"
                st.rerun()

    elif choice == "Tamamlanan İşler":
        df_tamam = st.session_state.db_jobs[st.session_state.db_jobs["Durum"] == "Çalışma Tamamlandı"]
        st.table(df_tamam.head(10))
        if not df_tamam.empty:
            sid = st.selectbox("İş Onayla/Reddet", df_tamam["Saha ID"])
            reason = st.text_input("Red Nedeni (Sadece Red için)")
            col_a, col_b = st.columns(2)
            if col_a.button("Kabul OK"):
                st.session_state.db_jobs.loc[st.session_state.db_jobs["Saha ID"] == sid, "Durum"] = "TT Onay Bekler"
                st.rerun()
            if col_b.button("Kabul RET"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.loc[idx, "Durum"] = "Yeni Atama"
                st.session_state.db_jobs.loc[idx, "Red_Nedeni"] = reason
                st.rerun()

    elif choice == "TT Onayı Bekleyen İşler":
        df_tt = st.session_state.db_jobs[st.session_state.db_jobs["Durum"] == "TT Onay Bekler"]
        st.table(df_tt.head(10))
        if not df_tt.empty:
            sid = st.selectbox("TT Onay Seç", df_tt["Saha ID"])
            if st.button("TT Onay Alındı"):
                st.session_state.db_jobs.loc[st.session_state.db_jobs["Saha ID"] == sid, "Durum"] = "Hak Ediş Bekliyor"
                st.rerun()

    elif choice == "Hak Ediş":
        df_hak = st.session_state.db_jobs[st.session_state.db_jobs["Durum"] == "Hak Ediş Bekliyor"]
        st.table(df_hak.head(10))
        if not df_hak.empty:
            sid = st.selectbox("Hak Ediş Onay", df_hak["Saha ID"])
            if st.button("Hak Ediş Alındı"):
                st.session_state.db_jobs.loc[st.session_state.db_jobs["Saha ID"] == sid, "Durum"] = "Hak Ediş Alındı"
                st.rerun()

    elif choice == "Kullanıcı Kontrol":
        if st.session_state.role in ["Admin", "Yönetici"]:
            st.subheader("Yeni Kullanıcı Ekle")
            name = st.text_input("İsim Soyisim")
            mail = st.text_input("Şirket Maili")
            role = st.selectbox("Rol", ["Saha Personeli", "Müdür", "Yönetici"])
            if st.button("Kullanıcı Oluştur"):
                new_u = {"İsim": name, "Mail": mail, "Rol": role}
                st.session_state.users = pd.concat([st.session_state.users, pd.DataFrame([new_u])], ignore_index=True)
                st.success("Kullanıcı eklendi.")
            st.dataframe(st.session_state.users)
        else: st.error("Yetkiniz yok.")

    elif choice == "Profil":
        st.subheader("Profil Bilgileri")
        st.text(f"Kullanıcı: {st.session_state.username}")
        st.text(f"Mail: {st.session_state.username}@sirket.com")
        st.text_input("Telefon Numarası", value="05xx")
        st.text_input("Yeni Şifre", type="password")
        st.button("Güncelle")

    elif choice == "Çıkış":
        st.session_state.logged_in = False
        st.rerun()
