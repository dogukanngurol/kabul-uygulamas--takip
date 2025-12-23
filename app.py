import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. SİSTEM YAPILANDIRMASI ---
st.set_page_config(page_title="Saha İş Takip Sistemi", layout="wide")

if 'db_jobs' not in st.session_state:
    st.session_state.db_jobs = pd.DataFrame(columns=[
        "Saha ID", "Personel", "Acıklama", "Durum", "Tarih", "Red_Nedeni"
    ])

if 'user_db' not in st.session_state:
    st.session_state.user_db = {
        "admin": {"sifre": "1234", "rol": "Admin"},
        "saha1": {"sifre": "4321", "rol": "Saha Personeli"},
        "mudur1": {"sifre": "0000", "rol": "Müdür"}
    }

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""

# --- 2. FONKSİYONLAR ---
def get_greeting(name):
    hour = datetime.now().hour
    if 8 <= hour < 12:
        return f"Günaydın {name} İyi Çalışmalar"
    elif 12 <= hour < 18:
        return f"İyi Günler {name} İyi Çalışmalar"
    elif 18 <= hour < 24:
        return f"İyi Akşamlar {name} İyi Çalışmalar"
    else:
        return f"İyi Geceler {name} İyi Çalışmalar"

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 3. GİRİŞ ---
if not st.session_state.logged_in:
    st.title("Saha Operasyon Girişi")
    u = st.text_input("Kullanıcı Adı")
    p = st.text_input("Şifre", type="password")

    if st.button("Giriş Yap"):
        if u in st.session_state.user_db and st.session_state.user_db[u]["sifre"] == p:
            st.session_state.logged_in = True
            st.session_state.role = st.session_state.user_db[u]["rol"]
            st.session_state.username = u
            st.rerun()
        else:
            st.error("Hatalı kullanıcı adı veya şifre")

# --- 4. ANA PANEL ---
else:
    st.sidebar.title(f"Kullanıcı: {st.session_state.username}")

    if st.session_state.role == "Saha Personeli":
        menu = ["Anasayfa", "Üzerime Atanan İşler", "İş Geçmişi", "Profil", "Çıkış"]
    else:
        menu = [
            "Anasayfa", "İş Ataması", "İzin Maili Bekleyenler",
            "Geri Gelen Atamalar", "Tamamlanan İşler",
            "TT Onayı Bekleyen İşler", "Hak Ediş",
            "Kullanıcı Kontrol", "Profil", "Çıkış"
        ]

    choice = st.sidebar.radio("Menü", menu)

    # --- ANASAYFA ---
    if choice == "Anasayfa":
        st.header(get_greeting(st.session_state.username))
        df = st.session_state.db_jobs

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Toplam İş", len(df))
        c2.metric("Atanan İşler", len(df[df["Durum"] == "Yeni Atama"]))
        c3.metric("İzin Bekleyen", len(df[df["Durum"] == "İzin Maili Atılmalı"]))
        c4.metric("Geri Gelen", len(df[df["Durum"].isin(["Giriş Yapılamadı", "Mal Sahibi Tepkili"])]))
        c5.metric("TT Onay", len(df[df["Durum"] == "TT Onay Bekler"]))

    # --- SAHA PERSONELİ: ÜZERİME ATANAN İŞLER ---
    elif choice == "Üzerime Atanan İşler":
        my_active_jobs = st.session_state.db_jobs[
            (st.session_state.db_jobs["Personel"].str.strip() == st.session_state.username.strip()) &
            (st.session_state.db_jobs["Durum"].isin(["Yeni Atama", "Bekleniyor"]))
        ]

        if not my_active_jobs.empty:
            st.dataframe(my_active_jobs[["Saha ID", "Acıklama", "Durum", "Tarih"]], use_container_width=True)

            target = st.selectbox("İş Seç", my_active_jobs["Saha ID"].unique())
            status = st.selectbox(
                "Yeni Durum",
                ["Giriş Yapılamadı", "İzin Maili Atılmalı", "Çalışma Tamamlandı", "Mal Sahibi Tepkili"]
            )
            desc = st.text_area("Açıklama")
            st.file_uploader("Fotoğrafları RAR olarak yükleyin", type=["rar"])

            if st.button("Atamayı Gönder"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == target].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = status
                st.session_state.db_jobs.at[idx[0], "Acıklama"] = desc
                st.rerun()
        else:
            st.info("Üzerinize atanmış aktif iş yok")

    # --- İŞ ATAMASI ---
    elif choice == "İş Ataması":
        sid = st.text_input("Saha ID")
        det = st.text_area("İş Detayı")

        saha_list = [
            u for u, d in st.session_state.user_db.items()
            if d["rol"] == "Saha Personeli"
        ]

        per = st.selectbox("Personel Seç", saha_list)

        if st.button("Atamayı Yap"):
            if sid and per:
                new_job = pd.DataFrame([{
                    "Saha ID": sid.strip(),
                    "Personel": per.strip(),
                    "Acıklama": det,
                    "Durum": "Yeni Atama",
                    "Tarih": datetime.now().strftime("%d-%m-%Y %H:%M"),
                    "Red_Nedeni": ""
                }])
                st.session_state.db_jobs = pd.concat(
                    [st.session_state.db_jobs, new_job],
                    ignore_index=True
                )
                st.rerun()

    # --- İŞ GEÇMİŞİ ---
    elif choice == "İş Geçmişi":
        hist = st.session_state.db_jobs[
            st.session_state.db_jobs["Personel"] == st.session_state.username
        ]
        st.dataframe(hist, use_container_width=True)
        st.download_button("Excel", to_excel(hist), "is_gecmisi.xlsx")

    # --- İZİN MAİLİ ---
    elif choice == "İzin Maili Bekleyenler":
        df_izin = st.session_state.db_jobs[
            st.session_state.db_jobs["Durum"] == "İzin Maili Atılmalı"
        ]
        st.dataframe(df_izin)
        if not df_izin.empty:
            sid = st.selectbox("İş Seç", df_izin["Saha ID"])
            if st.button("Kabul Alınabilir"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "Yeni Atama"
                st.rerun()

    # --- GERİ GELEN ATAMALAR ---
    elif choice == "Geri Gelen Atamalar":
        df_geri = st.session_state.db_jobs[
            st.session_state.db_jobs["Durum"].isin(["Giriş Yapılamadı", "Mal Sahibi Tepkili"])
        ]
        st.dataframe(df_geri)
        if not df_geri.empty:
            sid = st.selectbox("İş Seç", df_geri["Saha ID"])
            if st.button("Kabul Alınabilir"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "Yeni Atama"
                st.rerun()

    # --- TAMAMLANAN ---
    elif choice == "Tamamlanan İşler":
        df_tamam = st.session_state.db_jobs[
            st.session_state.db_jobs["Durum"] == "Çalışma Tamamlandı"
        ]
        st.dataframe(df_tamam)
        if not df_tamam.empty:
            sid = st.selectbox("İş Seç", df_tamam["Saha ID"])
            reason = st.text_input("Red Nedeni")
            c1, c2 = st.columns(2)
            if c1.button("Kabul OK"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "TT Onay Bekler"
                st.rerun()
            if c2.button("Kabul RET"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "Yeni Atama"
                st.session_state.db_jobs.at[idx[0], "Red_Nedeni"] = reason
                st.rerun()

    # --- TT ONAY ---
    elif choice == "TT Onayı Bekleyen İşler":
        df_tt = st.session_state.db_jobs[
            st.session_state.db_jobs["Durum"] == "TT Onay Bekler"
        ]
        st.dataframe(df_tt)
        if not df_tt.empty:
            sid = st.selectbox("İş Seç", df_tt["Saha ID"])
            if st.button("TT Onay Alındı"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "Hak Ediş Bekliyor"
                st.rerun()

    # --- HAK EDİŞ ---
    elif choice == "Hak Ediş":
        df_hak = st.session_state.db_jobs[
            st.session_state.db_jobs["Durum"] == "Hak Ediş Bekliyor"
        ]
        st.dataframe(df_hak)
        if not df_hak.empty:
            sid = st.selectbox("İş Seç", df_hak["Saha ID"])
            if st.button("Hak Ediş Alındı"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "Hak Ediş Alındı"
                st.rerun()

    # --- KULLANICI KONTROL ---
    elif choice == "Kullanıcı Kontrol":
        if st.session_state.role in ["Admin", "Yönetici"]:
            nu = st.text_input("Yeni Kullanıcı")
            np = st.text_input("Şifre")
            nr = st.selectbox("Rol", ["Saha Personeli", "Müdür", "Yönetici"])
            if st.button("Oluştur"):
                st.session_state.user_db[nu] = {"sifre": np, "rol": nr}
                st.rerun()
            st.dataframe(pd.DataFrame.from_dict(st.session_state.user_db, orient="index"))

    # --- PROFİL ---
    elif choice == "Profil":
        st.write(f"Kullanıcı: {st.session_state.username}")
        st.text_input("Yeni Şifre", type="password")
        st.button("Güncelle")

    # --- ÇIKIŞ ---
    elif choice == "Çıkış":
        st.session_state.logged_in = False
        st.rerun()
