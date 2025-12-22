# --- ANA SAYFA EKRANI ---
    if menu == "Ana Sayfa":
        # 1. Saat Bazlı Karşılama Mesajı (3. Madde Uygulaması)
        saat = datetime.now().hour
        kullanici_adi = user['ad_soyad']
        
        if 8 <= saat < 12:
            selam = f"Günaydın {kullanici_adi}, İyi Çalışmalar"
        elif 12 <= saat < 18:
            selam = f"İyi Günler {kullanici_adi}, İyi Çalışmalar"
        elif 18 <= saat < 24:
            selam = f"İyi Akşamlar {kullanici_adi}, İyi Çalışmalar"
        else:
            selam = f"İyi Geceler {kullanici_adi}, İyi Çalışmalar"
            
        st.title(f"👋 {selam}")
        st.markdown(f"**Yetki Seviyesi:** {user['yetki']}")
        st.divider()

        # Verileri kolay işlemek için DataFrame'i alalım
        df = st.session_state['is_verisi']

        # 2. YÖNETİCİ PANELİ SAYAÇLARI (Admin, Yönetici ve Müdür için)
        if any(rol in user['yetki'] for rol in ["Admin", "Yönetici", "Müdür"]):
            st.subheader("📊 Genel Operasyon Takibi")
            
            # Günlük, Haftalık, Aylık verileri filtreleme (Simüle edilmiş)
            bugun = str(datetime.now().date())
            tamamlanan_gunluk = len(df[(df['Durum'] == "Tamamlandı") & (df['Tarih'] == bugun)])
            bekleyen_atamalar = len(df[df['Durum'] == "Atandı"])
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Günlük Tamamlanan", tamamlanan_gunluk, help="Bugün içinde bitirilen işler")
            with col2:
                st.metric("Bekleyen Atamalar", bekleyen_atamalar, delta_color="inverse", help="Atanan ama henüz işlem görmemiş işler")
            with col3:
                st.metric("Haftalık Toplam İş", len(df), help="Bu hafta içinde açılan tüm işler")
            with col4:
                st.metric("Aylık Toplam İş", len(df) * 4, help="Bu ay içinde açılan tüm işler") # Örnek çarpı 4
            
            st.divider()
            
            # Hızlı Durum Grafiği veya Tablosu
            st.write("### Son Atanan 5 İş")
            st.table(df.tail(5)[["Tarih", "İş Başlığı", "Personel", "Durum"]])

        # 3. SAHA PERSONELİ PANELİ SAYAÇLARI (Sadece Saha Personeli için)
        else:
            st.subheader("📋 Görev Özetim")
            
            # Personelin kendi verileri
            uzerimdeki_isler = len(df[(df['Personel'] == kullanici_adi) & (df['Durum'] == "Atandı")])
            tamamladigim_isler = len(df[(df['Personel'] == kullanici_adi) & (df['Durum'] == "Tamamlandı")])
            
            c1, c2 = st.columns(2)
            
            with c1:
                st.info(f"🚀 **Üzerime Atanan İşler:** {uzerimdeki_isler}")
            with c2:
                st.success(f"✅ **Tamamladığım İşler:** {tamamladigim_isler}")
            
            st.divider()
            st.write("📢 *Not: Yeni iş atamalarını 'Üzerime Atanan İşler' sekmesinden kontrol edebilirsiniz.*")
