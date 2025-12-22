// --- YENİ EKLENEN FONKSİYONLAR ---

function getGreeting() {
    const hour = new Date().getHours();
    if (hour >= 8 && hour < 12) return "Günaydın";
    if (hour >= 12 && hour < 18) return "İyi Günler";
    if (hour >= 18 && hour < 24) return "İyi Akşamlar";
    return "İyi Geceler";
}

function renderDashboard() {
    const greeting = getGreeting();
    
    // Mock Veriler (İleride LocalStorage'dan çekilecek)
    const stats = {
        daily: 8,
        pending: 14,
        weekly: 52,
        monthly: 210
    };

    return `
        <div class="space-y-6">
            <div class="bg-gradient-to-r from-blue-600 to-indigo-700 p-8 rounded-xl text-white shadow-lg">
                <h2 class="text-3xl font-bold">${greeting}, ${currentUser.name}</h2>
                <p class="mt-2 text-blue-100 italic">Anatoli Bilişim İş Takip Sistemine Hoş Geldiniz. Yetki Seviyeniz: ${currentUser.role}</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                
                <div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-green-500">
                    <p class="text-sm text-gray-500 font-medium uppercase">Günlük Tamamlanan</p>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-3xl font-bold text-gray-800">${stats.daily}</span>
                        <span class="p-2 bg-green-100 text-green-600 rounded-full text-xs">Bugün</span>
                    </div>
                </div>

                <div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-yellow-500">
                    <p class="text-sm text-gray-300 font-medium uppercase text-gray-500">Bekleyen Atamalar</p>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-3xl font-bold text-gray-800">${stats.pending}</span>
                        <span class="p-2 bg-yellow-100 text-yellow-600 rounded-full text-xs">Aktif</span>
                    </div>
                </div>

                <div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-blue-500">
                    <p class="text-sm text-gray-500 font-medium uppercase">Haftalık Toplam İş</p>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-3xl font-bold text-gray-800">${stats.weekly}</span>
                        <span class="p-2 bg-blue-100 text-blue-600 rounded-full text-xs">7 Gün</span>
                    </div>
                </div>

                <div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-purple-500">
                    <p class="text-sm text-gray-500 font-medium uppercase">Aylık Toplam İş</p>
                    <div class="flex items-center justify-between mt-2">
                        <span class="text-3xl font-bold text-gray-800">${stats.monthly}</span>
                        <span class="p-2 bg-purple-100 text-purple-600 rounded-full text-xs">30 Gün</span>
                    </div>
                </div>

            </div>

            <div class="bg-gray-50 p-4 border border-gray-200 rounded-lg">
                <p class="text-xs text-gray-400 font-mono italic">
                    * Sayaçlar rolünüze istinaden gerçek zamanlı verilerle güncellenmektedir. 
                    Saha personeli rollerinde bu detaylı istatistikler kısıtlanmıştır.
                </p>
            </div>
        </div>
    `;
}

// --- NAVIGATETO CASE GÜNCELLEMESİ ---
function navigateTo(pageId) {
    // ... (Önceki menü aktiflik kodları aynı kalacak)
    
    const content = document.getElementById('content');
    const title = document.getElementById('pageTitle');
    
    switch(pageId) {
        case 'home':
            title.innerText = "Yönetim Paneli";
            // Admin, Yönetici ve Müdür ise detaylı dashboard göster
            if ([ROLES.ADMIN, ROLES.YONETICI, ROLES.MUDUR].includes(currentUser.role)) {
                content.innerHTML = renderDashboard();
            } else {
                // Saha Personeli için sade ana sayfa
                content.innerHTML = `
                    <div class="bg-white p-6 rounded shadow">
                        <h2 class="text-lg font-bold">${getGreeting()}, ${currentUser.name}</h2>
                        <p class="text-gray-600">Lütfen yapmanız gereken işleri görmek için 'Atanan İşler' sekmesine bakınız.</p>
                    </div>`;
            }
            break;
        // ... (Diğer case'ler aynı kalacak)
    }
}
