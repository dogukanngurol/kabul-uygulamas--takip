// --- 1. VERİTABANI VE MODEL YAPISI (SQL & SCHEMA) ---
/*
CREATE TYPE user_role AS ENUM ('ADMIN', 'MUDUR', 'PERSONEL');
CREATE TYPE job_status AS ENUM (
    'TASLAK', 'IS_TAMAMLANDI', 'GIRIS_YAPILAMADI', 'TEPKILI', 
    'MAL_SAHIBI_GELMIYOR', 'TT_ONAYINDA', 'HAK_EDIS_BEKLENIYOR', 'HAK_EDIS_ALINDI'
);

TABLE users (id, email, password, role, city, phone);
TABLE jobs (id, title, description, assigned_to, status, city, tt_onay, ret_sebebi, created_at);
TABLE job_photos (id, job_id, photo_url); -- DB Optimizasyonu için URL tutulur
TABLE inventory (id, user_id, item_name, serial_no);
*/

// --- 2. YETKİLENDİRME VE KULLANICI YÖNETİMİ ---
const roles = {
    ADMIN: 'ADMIN',
    MUDUR: 'MUDUR',
    PERSONEL: 'PERSONEL'
};

const checkAuth = (requiredRoles) => (req, res, next) => {
    if (requiredRoles.includes(req.user.role)) next();
    else res.status(403).send("Yetkisiz İşlem");
};

// --- 3. İŞ AKIŞI VE TASLAK MANTIĞI ---
async function saveJob(jobData, isDraft = false) {
    const status = isDraft ? 'TASLAK' : jobData.status;
    const query = `INSERT INTO jobs (assigned_to, description, status, city) VALUES ($1, $2, $3, $4)`;
    // Fotoğraflar S3/Cloudinary gibi harici storage'a yüklenip URL'i DB'ye kaydedilir
    return db.execute(query, [jobData.userId, jobData.notes, status, jobData.city]);
}

// --- 4. FİLTRELEME VE RAPORLAMA (EXCEL) ---
const cities81 = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"];

const getFilteredJobs = (filters, userRole) => {
    let baseQuery = "SELECT * FROM jobs WHERE 1=1";
    
    if (filters.status === 'TAMAMLANAN') baseQuery += " AND status = 'IS_TAMAMLANDI'";
    else if (filters.status === 'TAMAMLANAMAYAN') baseQuery += " AND status IN ('GIRIS_YAPILAMADI', 'TEPKILI', 'MAL_SAHIBI_GELMIYOR')";
    
    // Yetkiye özel durumlar
    if (![roles.ADMIN, roles.MUDUR].includes(userRole)) {
        baseQuery += " AND status NOT IN ('TT_ONAYINDA', 'HAK_EDIS_BEKLENIYOR', 'HAK_EDIS_ALINDI')";
    }
    
    return db.execute(baseQuery);
};

// --- 5. ONAY SÜREÇLERİ (TT & HAK EDİŞ) ---
const handleApproval = async (jobId, action, note = "") => {
    if (action === 'RET') {
        await db.execute("UPDATE jobs SET status = 'TASLAK', ret_sebebi = $1 WHERE id = $2", [note, jobId]);
    } else if (action === 'KABUL') {
        await db.execute("UPDATE jobs SET status = 'TT_ONAYINDA' WHERE id = $1", [jobId]);
    } else if (action === 'HAK_EDIS_GONDER') {
        await db.execute("UPDATE jobs SET status = 'HAK_EDIS_BEKLENIYOR' WHERE id = $1", [jobId]);
    }
};

// --- 6. ANASAYFA VE GÖRSEL BİLEŞENLER ---
const getGreeting = (name) => {
    const hour = new Date().getHours();
    if (hour >= 8 && hour < 12) return `Günaydın ${name} İyi Çalışmalar`;
    if (hour >= 12 && hour < 18) return `İyi Günler ${name} İyi Çalışmalar`;
    if (hour >= 18 && hour < 24) return `İyi Akşamlar ${name} İyi Çalışmalar`;
    return `İyi Geceler ${name} İyi Çalışmalar`;
};

// Gauge Gösterge Hesaplama
const calculateProgress = (completed, total) => {
    return total > 0 ? (completed / total) * 100 : 0;
};

// --- 7. ZİMMET VE ENVANTER ---
const getInventory = async (userId, userRole) => {
    if (userRole === roles.PERSONEL) {
        return db.execute("SELECT * FROM inventory WHERE user_id = $1", [userId]);
    }
    return db.execute("SELECT * FROM inventory");
};

// --- 8. FRONTEND UI MANTIĞI (PSEUDO) ---
/*
  {jobs.length === 0 ? (
      <div className="empty-state">
          <Filters />
          <p>Gösterilecek Tamamlanmış İş Bulunmamaktadır</p>
      </div>
  ) : (
      <DataTable data={jobs} onExportExcel={handleExport} />
  )}
*/
