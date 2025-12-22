import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. VERİ YAPILARI ---
if 'users' not in st.session_state:
    st.session_state['users'] = {
        "dogukan": {"sifre": "1234", "ad_soyad": "Doğukan Gürol", "yetki": "Admin / Müdür"},
        "saha01": {"sifre": "0000", "ad_soyad": "Mehmet Saha", "yetki": "Saha Personeli"}
    }

if 'is_verisi' not in st.session_state:
    # Başlangıçta örnek bir iş atayalım ki test edebilesin
    st.session_state['is_verisi'] = pd.DataFrame([
        {"İş ID": 1, "Tarih": "2023-10-27", "İş Başlığı": "Örnek Kurulum", "Personel": "Mehmet Saha", "Şehir": "İstanbul", "Durum": "Atandı", "Notlar": ""}
    ])

# --- 2. GİRİŞ KONTROLÜ ---
if 'auth' not in st.session_state: st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("Anatoli Bilişim Giriş")
    k_adi = st.text_input("Kullanıcı Adı")
    sifre = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if k_adi in st.session_state['users'] and st.session_state['users'][k_adi]["sifre"] == sifre:
            st.session_state['auth'] = True
            st.session_state['user_info'] = st.session_state['users'][k_adi]
            st.rerun()
        else: st.error("Hatalı giriş!")

else:
    user = st.session_state['user_info']
    
    with st.sidebar:
        st.subheader("Anatoli Bilişim")
        st.write(f"👤 {user['ad_soyad']}")
        st.caption(f"Yetki: {user['yetki']}")
        st.divider()
        
        if "Saha" in user['yetki']:
            menu = st.radio("Menü", ["Ana Sayfa", "Üzerime Atanan İşler", "Tamamladığım İşler", "Profilim", "Çıkış"])
        else:
            menu = st.radio("Menü", ["Ana Sayfa", "İş Ataması", "Atanan İşler", "Giriş Onayları", "TT Onayı Bekleyenler", "Kullanıcı Yönetimi", "Çıkış"])

    # --- 3. EKRANLAR ---
    
    # SAHA PERSONELİ ÖZEL EKRANI: ÜZERİME ATANAN İŞLER
    if menu == "Üzerime Atanan İşler":
        st.header("🛠️ Üzerime Atanan İşler")
        
        # Sadece giriş yapan personelin ismine ait olan ve henüz tamamlanmamış işleri filtrele
        df = st.session_state['is_verisi']
        personel_isleri = df[(df['Personel'] == user['ad_soyad']) & (df['Durum'] == "Atandı")]
        
        if personel_isleri.empty:
            st.info("Üzerinize atanan aktif bir görev bulunmamaktadır.")
        else:
            st.table(personel_isleri[["İş ID", "İş Başlığı", "Şehir", "Tarih"]])
            
            with st.form("is_bitirme_formu"):
                is_id = st.selectbox("İşlem Yapılacak İş ID", personel_isleri["İş ID"])
                detay = st.text_area("İş Detayı / Notlar (Zorunlu)")
                durum_secimi = st.selectbox("İşlem Tipi", ["Kabul Alındı", "Giriş Maili Gerekli"])
                yuklenenler = st.file_uploader("Fotoğraflar (Maks 65)", accept_multiple_files=True)
                
                if st.form_submit_button("İşi Gönder"):
                    if not detay:
                        st.error("Lütfen iş detayını doldurunuz!")
                    else:
                        # Veritabanında güncelleme yap
                        idx = st.session_state['is_verisi'].index[st.session_state['is_verisi']['İş ID'] == is_id].tolist()[0]
                        yeni_durum = "Tamamlandı" if durum_secimi == "Kabul Alındı" else "Giriş Maili Bekler"
                        
                        st.session_state['is_verisi'].at[idx, 'Durum'] = yeni_durum
                        st.session_state['is_verisi'].at[idx, 'Notlar'] = detay
                        st.success(f"İş durumu '{yeni_durum}' olarak güncellendi.")
                        st.rerun()

    elif menu == "Tamamladığım İşler":
        st.header("✅ Tamamladığım İşler")
        tamamlananlar = st.session_state['is_verisi'][(st.session_state['is_verisi']['Personel'] == user['ad_soyad']) & (st.session_state['is_verisi']['Durum'].isin(["Tamamlandı", "Giriş Maili Bekler"]))]
        st.dataframe(tamamlananlar)

    # DİĞER EKRANLAR (Admin/Müdür İçin)
    elif menu == "İş Ataması":
        st.header("📌 Yeni İş Ataması")
        with st.form("atama"):
            baslik = st.text_input("İş Başlığı")
            # Sadece saha personellerini listele
            saha_listesi = [u["ad_soyad"] for u in st.session_state['users'].values() if "Saha" in u["yetki"]]
            secilen_personel = st.selectbox("Personel", saha_listesi)
            if st.form_submit_button("Ata"):
                yeni = {"İş ID": len(st.session_state['is_verisi'])+1, "Tarih": str(datetime.now().date()), "İş Başlığı": baslik, "Personel": secilen_personel, "Şehir": "Belirtilmedi", "Durum": "Atandı", "Notlar": ""}
                st.session_state['is_verisi'] = pd.concat([st.session_state['is_verisi'], pd.DataFrame([yeni])], ignore_index=True)
                st.success(f"İş {secilen_personel} üzerine atandı!")

    elif menu == "Çıkış":
        st.session_state['auth'] = False
        st.rerun()
