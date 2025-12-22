<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anatoli Bilişim - İş Takip</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .active-menu { background-color: #374151; border-left: 4px solid #3b82f6; }
    </style>
</head>
<body class="bg-gray-100 font-sans">

<div id="app" class="flex h-screen overflow-hidden">
    <aside class="w-64 bg-gray-900 text-white flex flex-col">
        <div class="p-6">
            <h1 class="text-xl font-bold text-blue-400">Anatoli Bilişim</h1>
            <div class="mt-4 pb-4 border-b border-gray-700">
                <p id="userName" class="text-sm font-medium"></p>
                <p id="userRole" class="text-xs text-gray-400 italic"></p>
            </div>
        </div>
        
        <nav id="menuList" class="flex-1 px-4 space-y-2 overflow-y-auto">
            </nav>

        <div class="p-4 border-t border-gray-700">
            <button onclick="logout()" class="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-gray-800 rounded">Çıkış</button>
        </div>
    </aside>

    <main class="flex-1 flex flex-col overflow-hidden">
        <header class="bg-white shadow-sm p-4 text-xl font-semibold text-gray-700" id="pageTitle">
            Yükleniyor...
        </header>
        <section id="content" class="p-6 overflow-auto flex-1">
            </section>
    </main>
</div>

<script>
// 1. MOCK VERİLER VE ROLLER
const ROLES = {
    ADMIN: 'Admin',
    YONETICI: 'Yönetici',
    MUDUR: 'Müdür',
    SAHA: 'Saha Personeli'
};

const menuConfig = [
    { id: 'home', label: 'Ana Sayfa', roles: [ROLES.ADMIN, ROLES.YONETICI, ROLES.MUDUR, ROLES.SAHA] },
    { id: 'assign', label: 'İş Ataması', roles: [ROLES.ADMIN, ROLES.YONETICI] },
    { id: 'jobs', label: 'Atanan İşler', roles: [ROLES.ADMIN, ROLES.YONETICI, ROLES.MUDUR, ROLES.SAHA] },
    { id: 'approvals', label: 'Giriş Onayları', roles: [ROLES.ADMIN, ROLES.YONETICI, ROLES.MUDUR] },
    { id: 'tt_pending', label: 'TT Onayı Bekleyenler', roles: [ROLES.ADMIN, ROLES.MUDUR] },
    { id: 'completed', label: 'Tamamlanan İşler', roles: [ROLES.ADMIN, ROLES.YONETICI, ROLES.MUDUR, ROLES.SAHA] },
    { id: 'payments', label: 'Hak Ediş', roles: [ROLES.ADMIN, ROLES.YONETICI] },
    { id: 'inventory', label: 'Zimmet & Envanter', roles: [ROLES.ADMIN, ROLES.YONETICI, ROLES.MUDUR] },
    { id: 'users', label: 'Kullanıcı Yönetimi', roles: [ROLES.ADMIN, ROLES.YONETICI] },
    { id: 'profile', label: 'Profilim', roles: [ROLES.ADMIN, ROLES.YONETICI, ROLES.MUDUR, ROLES.SAHA] },
];

// 2. GLOBAL STATE (In-Memory)
let currentUser = {
    name: "Doğukan Gürol",
    role: ROLES.ADMIN
};

// 3. UYGULAMA MANTIĞI
function initApp() {
    renderMenu();
    navigateTo('home');
    updateUserInfo();
}

function updateUserInfo() {
    document.getElementById('userName').innerText = currentUser.name;
    document.getElementById('userRole').innerText = currentUser.role;
}

function renderMenu() {
    const menuNav = document.getElementById('menuList');
    menuNav.innerHTML = '';
    
    menuConfig.forEach(item => {
        if (item.roles.includes(currentUser.role)) {
            const btn = document.createElement('button');
            btn.innerText = item.label;
            btn.className = "w-full text-left px-4 py-3 rounded-lg text-sm transition-colors hover:bg-gray-800";
            btn.onclick = () => navigateTo(item.id);
            btn.setAttribute('data-id', item.id);
            menuNav.appendChild(btn);
        }
    });
}

function navigateTo(pageId) {
    // Menü rengini güncelle
    document.querySelectorAll('#menuList button').forEach(btn => {
        btn.classList.remove('active-menu');
        if(btn.getAttribute('data-id') === pageId) btn.classList.add('active-menu');
    });

    const content = document.getElementById('content');
    const title = document.getElementById('pageTitle');
    
    // Basit Router mantığı
    switch(pageId) {
        case 'home':
            title.innerText = "Ana Sayfa";
            content.innerHTML = `<div class="bg-white p-6 rounded shadow">
                <h2 class="text-lg font-bold">Hoş geldiniz, ${currentUser.name}</h2>
                <p class="text-gray-600">Sistemdeki güncel işlerin özeti burada yer alacak.</p>
                <div class="grid grid-cols-3 gap-4 mt-4">
                    <div class="p-4 bg-blue-100 text-blue-800 rounded">Bekleyen İşler: 12</div>
                    <div class="p-4 bg-green-100 text-green-800 rounded">Tamamlanan: 45</div>
                    <div class="p-4 bg-yellow-100 text-yellow-800 rounded">Onay Bekleyen: 5</div>
                </div>
            </div>`;
            break;
        case 'users':
            title.innerText = "Kullanıcı Yönetimi";
            content.innerHTML = `<p>Sadece Admin ve Yöneticiler bu alanı görebilir.</p>`;
            break;
        default:
            title.innerText = menuConfig.find(m => m.id === pageId).label;
            content.innerHTML = `<p class="text-gray-500">${title.innerText} modülü henüz hazır değil, demo aşamasında.</p>`;
    }
}

function logout() {
    alert("Çıkış yapılıyor... (Demo)");
    location.reload();
}

// Başlat
initApp();
</script>
</body>
</html>
