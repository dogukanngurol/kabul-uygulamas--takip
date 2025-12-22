anatoli-bilisim-app/
├── 📄 index.html             # Uygulamanın ana giriş kapısı (Layout & Root Container)
├── 📂 css/
│   └── 📄 styles.css          # Tailwind entegrasyonu ve özel UI düzenlemeleri
├── 📂 js/
│   ├── 📄 app.js              # State yönetimi (currentUser), Router ve Init mantığı
│   ├── 📄 constants.js        # ROLES, TURKIYE_ILLER, MOCK_USERS gibi sabit veriler
│   ├── 📄 storage.js          # LocalStorage CRUD (Create, Read, Update, Delete) işlemleri
│   └── 📂 modules/            # Yazdığımız tüm ekranların logic ve UI fonksiyonları
│       ├── 📄 dashboard.js    # Saat bazlı karşılama ve Sayaçlar (Admin/Müdür/Yön.)
│       ├── 📄 jobAssignment.js# İş Atama Ekranı (İlişkilendirme ve Kayıt)
│       ├── 📄 assignedJobs.js # Atanan İşler Paneli (Yönetici İzleme & Filtreleme)
│       ├── 📄 approvals.js    # Giriş Onayları (Giriş Maili Akışı)
│       ├── 📄 ttApprovals.js  # TT Onayı Bekleyenler (Onay/Ret Karar Mekanizması)
│       ├── 📄 completed.js    # Tamamlanan İşler ve Arşiv (Fotoğraf/Not inceleme)
│       ├── 📄 payments.js     # Hak Ediş Ekranı (Finansal Takip)
│       ├── 📄 inventory.js    # Zimmet & Envanter (Personel Ekipman Takibi)
│       ├── 📄 userManager.js  # Kullanıcı Yönetimi (Ekleme/Silme/Yetkilendirme)
│       ├── 📄 profile.js      # Profilim ve Kullanıcı Ayarları
│       └── 📄 sahaPortal.js   # Saha Personeli Dashboard, İş Gönderimi ve Taslaklar
└── 📂 assets/                 # Logolar, ikonlar ve mock görseller
