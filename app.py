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
        p = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            if u in st.session_state.user_db and st.session_state.user_db[u]["sifre"] == p:
                st.session_state.logged_in = True
                st.session_state.role = st.session_state.user_db[u]["rol"]
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")

# --- 4. ANA PANEL ---
else:
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
        c2.metric("İzin Bekleyen", len(df[df["Durum"] == "İzin Maili Atılmalı"]))
        c3.metric("Geri Gelen", len(df[df["Durum"].isin(["Giriş Yapılamadı", "Mal Sahibi Tepkili"])]))
        c4.metric("TT Onay", len(df[df["Durum"] == "TT Onay Bekler"]))
        c5.metric("Tamamlanan", len(df[df["Durum"] == "Çalışma Tamamlandı"]))

    # --- SAHA PERSONELİ: ÜZERİME ATANAN İŞLER ---
    elif choice == "Üzerime Atanan İşler":
        st.subheader("Üzerime Atanan İşler")
        # Filtreleme: Personel eşleşmesi ve tamamlanmamış statü
        my_jobs = st.session_state.db_jobs[
            (st.session_state.db_jobs["Personel"] == st.session_state.username) & 
            (~st.session_state.db_jobs["Durum"].isin(["Çalışma Tamamlandı", "TT Onay Bekler", "Hak Ediş Bekliyor", "Hak Ediş Alındı"]))
        ]
        
        if not my_jobs.empty:
            st.dataframe(my_jobs[["Saha ID", "Acıklama", "Durum", "Tarih"]], use_container_width=True)
            target = st.selectbox("İşlem Yapılacak İş (Saha ID)", my_jobs["Saha ID"].tolist())
            status = st.selectbox("Yeni Durum Seçin", ["Giriş Yapılamadı", "İzin Maili Atılmalı", "Çalışma Tamamlandı", "Mal Sahibi Tepkili"])
            desc = st.text_area("İş Detayı / Notlar")
            file = st.file_uploader("Fotoğrafları RAR Olarak Yükleyin", type=["rar"])
            
            if st.button("Atamayı Gönder"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == target].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = status
                st.session_state.db_jobs.at[idx[0], "Acıklama"] = desc
                st.success(f"{target} numaralı iş güncellendi ve gönderildi.")
                st.rerun()
        else:
            st.info("Üzerinize atanmış aktif bir iş bulunmamaktadır.")

    elif choice == "İş Geçmişi":
        st.subheader("İş Geçmişim")
        hist = st.session_state.db_jobs[st.session_state.db_jobs["Personel"] == st.session_state.username]
        st.dataframe(hist.head(10), use_container_width=True)
        st.download_button("Excel Raporu İndir", get_excel(hist), "is_gecmisim.xlsx")

    # --- YÖNETİM: İŞ ATAMASI ---
    elif choice == "İş Ataması":
        st.subheader("Saha Personeline İş Atama")
        sid = st.text_input("Saha ID (Örn: Saha-001)")
        det = st.text_area("İş Detayı ve Talimatlar")
        saha_staff = [u for u, d in st.session_state.user_db.items() if d["rol"] == "Saha Personeli"]
        per = st.selectbox("Atanacak Personel", saha_staff)
        
        if st.button("Atamayı Yap"):
            if sid:
                new_job = {
                    "Saha ID": sid, "Personel": per, "Acıklama": det, 
                    "Durum": "Yeni Atama", "Tarih": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                st.session_state.db_jobs = pd.concat([st.session_state.db_jobs, pd.DataFrame([new_job])], ignore_index=True)
                st.success(f"İş başarıyla {per} kullanıcısına atandı.")
            else:
                st.error("Lütfen bir Saha ID giriniz.")

    elif choice == "İzin Maili Bekleyenler":
        df_izin = st.session_state.db_jobs[st.session_state.db_jobs["Durum"] == "İzin Maili Atılmalı"]
        st.table(df_izin.head(10))
        if not df_izin.empty:
            sid = st.selectbox("Saha ID", df_izin["Saha ID"])
            if st.button("Kabul Alınabilir"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "Yeni Atama"
                st.rerun()
        st.download_button("Excel İndir", get_excel(df_izin), "izin_bekleyenler.xlsx")

    elif choice == "Geri Gelen Atamalar":
        df_geri = st.session_state.db_jobs[st.session_state.db_jobs["Durum"].isin(["Giriş Yapılamadı", "Mal Sahibi Tepkili"])]
        st.table(df_geri.head(10))
        if not df_geri.empty:
            sid = st.selectbox("Saha ID Seç", df_geri["Saha ID"])
            if st.button("Kabul Alınabilir (Yeniden Ata)"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "Yeni Atama"
                st.rerun()
        st.download_button("Excel İndir", get_excel(df_geri), "geri_gelenler.xlsx")

    elif choice == "Tamamlanan İşler":
        df_tamam = st.session_state.db_jobs[st.session_state.db_jobs["Durum"] == "Çalışma Tamamlandı"]
        st.table(df_tamam.head(10))
        if not df_tamam.empty:
            sid = st.selectbox("Onay İşlemi", df_tamam["Saha ID"])
            reason = st.text_input("Red Nedeni (Sadece Red durumunda)")
            ca, cb = st.columns(2)
            if ca.button("Kabul OK"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "TT Onay Bekler"
                st.rerun()
            if cb.button("Kabul RET"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "Yeni Atama"
                st.session_state.db_jobs.at[idx[0], "Red_Nedeni"] = reason
                st.rerun()

    elif choice == "TT Onayı Bekleyen İşler":
        df_tt = st.session_state.db_jobs[st.session_state.db_jobs["Durum"] == "TT Onay Bekler"]
        st.table(df_tt.head(10))
        if not df_tt.empty:
            sid = st.selectbox("Onaylanan Saha", df_tt["Saha ID"])
            if st.button("TT Onay Alındı"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "Hak Ediş Bekliyor"
                st.rerun()

    elif choice == "Hak Ediş":
        df_hak = st.session_state.db_jobs[st.session_state.db_jobs["Durum"] == "Hak Ediş Bekliyor"]
        st.table(df_hak.head(10))
        if not df_hak.empty:
            sid = st.selectbox("Saha ID", df_hak["Saha ID"])
            if st.button("Hak Ediş Alındı"):
                idx = st.session_state.db_jobs[st.session_state.db_jobs["Saha ID"] == sid].index
                st.session_state.db_jobs.at[idx[0], "Durum"] = "Hak Ediş Alındı"
                st.rerun()

    elif choice == "Kullanıcı Kontrol":
        if st.session_state.role in ["Admin", "Yönetici"]:
            st.subheader("Sistem Kullanıcıları")
            with st.form("user_add"):
                nu, np = st.text_input("Kullanıcı Adı"), st.text_input("Şifre")
                nr = st.selectbox("Rol", ["Saha Personeli", "Müdür", "Yönetici"])
                if st.form_submit_button("Ekle"):
                    st.session_state.user_db[nu] = {"sifre": np, "rol": nr}
                    st.success("Kullanıcı eklendi.")
            st.write(pd.DataFrame.from_dict(st.session_state.user_db, orient='index'))
        else: st.error("Yetkiniz yok.")

    elif choice == "Profil":
        st.subheader("Profilim")
        st.info(f"Kullanıcı: {st.session_state.username} | Yetki: {st.session_state.role}")
        new_p = st.text_input("Yeni Şifre", type="password")
        if st.button("Güncelle"):
            st.session_state.user_db[st.session_state.username]["sifre"] = new_p
            st.success("Şifre güncellendi.")

    elif choice == "Çıkış":
        st.session_state.logged_in = False
        st.rerun()
