import datetime
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = "gizli_anahtar_123"

# --- VERİ SETLERİ VE TANIMLAMALAR ---
CITIES = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"]

users = [
    {"email": "admin@sirket.com", "role": "ADMIN", "name": "Admin", "phone": "5551111"},
    {"email": "filiz@deneme.com", "role": "MUDUR", "name": "Filiz", "phone": "5552222"},
    {"email": "dogukan@deneme.com", "role": "PERSONEL", "name": "Doğukan", "phone": "5553333"},
    {"email": "doguscan@deneme.com", "role": "PERSONEL", "name": "Doğuşcan", "phone": "5554444"},
    {"email": "cuneyt@deneme.com", "role": "PERSONEL", "name": "Cüneyt", "phone": "5555555"}
]

jobs = [] # {id, assigned_to, city, status, notes, photos: [], tt_onay: bool, ret_sebebi: "", date: datetime}
inventory = [] # {id, user_email, item_name}

# --- YARDIMCI MANTIK ÜNİTELERİ ---
def get_greeting(name):
    hour = datetime.datetime.now().hour
    if 8 <= hour < 12: return f"Günaydın {name} İyi Çalışmalar"
    elif 12 <= hour < 18: return f"İyi Günler {name} İyi Çalışmalar"
    elif 18 <= hour < 24: return f"İyi Akşamlar {name} İyi Çalışmalar"
    else: return f"İyi Geceler {name} İyi Çalışmalar"

# --- ROUTERLAR ---

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    user = next((u for u in users if u['email'] == email), None)
    if user:
        session['user'] = user['email']
        session['role'] = user['role']
        session['name'] = user['name']
        return redirect(url_for('dashboard'))
    return "Hatalı Giriş"

@app.route('/')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    user_role = session['role']
    user_email = session['user']
    
    greeting = get_greeting(session['name'])
    
    # İbre Göstergeleri (Gauge) Verisi
    stats = {"daily": 0, "weekly": 0, "monthly": 0} 
    
    # Admin & Personel Anasayfa Verileri
    my_jobs = [j for j in jobs if j['assigned_to'] == user_email]
    completed_jobs = [j for j in jobs if j['status'] == 'IS_TAMAMLANDI']
    pending_jobs = [j for j in jobs if j['status'] != 'IS_TAMAMLANDI']
    
    return render_template('dashboard.html', greeting=greeting, stats=stats, role=user_role, jobs=my_jobs if user_role == 'PERSONEL' else jobs)

@app.route('/kullanici-yonetimi', methods=['GET', 'POST', 'DELETE'])
def manage_users():
    if session.get('role') not in ['ADMIN', 'MUDUR']: return "Yetkisiz", 403
    if request.method == 'POST':
        new_user = {"email": request.form.get('email'), "role": request.form.get('role'), "name": request.form.get('name')}
        users.append(new_user)
    return render_template('users.html', users=users)

@app.route('/profil-guncelle', methods=['POST'])
def update_profile():
    if session.get('role') == 'MUDUR': return "Müdür profil güncelleyemez", 403
    user_email = session.get('user')
    for u in users:
        if u['email'] == user_email:
            u['phone'] = request.form.get('phone')
            u['email'] = request.form.get('email')
            session['user'] = u['email']
    return redirect(url_for('dashboard'))

@app.route('/is-atama', methods=['GET', 'POST'])
def assign_job():
    if request.method == 'POST':
        new_job = {
            "id": len(jobs) + 1,
            "assigned_to": request.form.get('staff'),
            "city": request.form.get('city'),
            "status": "ATANDI",
            "notes": "",
            "photos": [],
            "date": datetime.datetime.now()
        }
        jobs.append(new_job)
    staff_list = [u for u in users if u['role'] == 'PERSONEL'] # Müdür listede görünmez
    return render_template('assign.html', staff=staff_list, cities=CITIES, jobs=jobs)

@app.route('/is-islemleri', methods=['POST'])
def process_job():
    job_id = int(request.form.get('job_id'))
    action = request.form.get('action') # 'TASLAK', 'GÖNDER'
    status = request.form.get('status')
    
    for j in jobs:
        if j['id'] == job_id:
            j['notes'] = request.form.get('notes')
            j['status'] = 'TASLAK' if action == 'TASLAK' else status
            # Fotoğraf URL metadata olarak kaydedilmeli (Storage Optimizasyonu)
            if 'photo' in request.files:
                j['photos'].append(f"storage_url_path/{request.files['photo'].filename}")
    return redirect(url_for('dashboard'))

@app.route('/tamamlanan-isler')
def completed_jobs():
    filter_status = request.args.get('filter_type') # 'TAMAMLANAN' veya 'TAMAMLANAMAYAN'
    staff_filter = request.args.get('staff')
    city_filter = request.args.get('city')
    
    filtered = jobs
    if filter_status == 'TAMAMLANAN':
        filtered = [j for j in jobs if j['status'] == 'IS_TAMAMLANDI']
    elif filter_status == 'TAMAMLANAMAYAN':
        filtered = [j for j in jobs if j['status'] in ['GIRIS_YAPILAMADI', 'TEPKILI', 'MAL_SAHIBI_GELMIYOR']]
    
    if staff_filter: filtered = [j for j in filtered if j['assigned_to'] == staff_filter]
    if city_filter: filtered = [j for j in filtered if j['city'] == city_filter]
    
    return render_template('list.html', jobs=filtered, empty_msg="Gösterilecek Tamamlanmış İş Bulunmamaktadır", cities=CITIES, staff=users)

@app.route('/hak-edish', methods=['GET', 'POST'])
def hak_edish():
    if session.get('user') != 'filiz@deneme.com' and session.get('role') != 'ADMIN': return "Yetkisiz", 403
    
    if request.method == 'POST':
        job_id = int(request.form.get('job_id'))
        for j in jobs:
            if j['id'] == job_id: j['status'] = 'HAK_EDIS_ALINDI'
            
    hak_edish_jobs = [j for j in jobs if j['status'] in ['HAK_EDIS_BEKLENIYOR', 'HAK_EDIS_ALINDI']]
    return render_template('hakedis.html', jobs=hak_edish_jobs)

@app.route('/onay-merkezi', methods=['POST'])
def approval_center():
    if session.get('role') != 'MUDUR': return "Yetkisiz", 403
    job_id = int(request.form.get('job_id'))
    decision = request.form.get('decision') # 'KABUL', 'RET', 'TT_BEKLE'
    
    for j in jobs:
        if j['id'] == job_id:
            if decision == 'RET':
                j['status'] = 'RET_EDILDI'
                j['ret_sebebi'] = request.form.get('reason')
            elif decision == 'TT_BEKLE':
                j['status'] = 'TT_ONAYINDA'
            elif decision == 'HAK_EDIS_GONDER':
                j['status'] = 'HAK_EDIS_BEKLENIYOR'
    return redirect(url_for('dashboard'))

@app.route('/zimmet-yonetimi', methods=['GET', 'POST'])
def inventory_manage():
    role = session.get('role')
    user = session.get('user')
    if request.method == 'POST' and role == 'MUDUR':
        inventory.append({"id": len(inventory)+1, "user_email": request.form.get('staff'), "item": request.form.get('item')})
    
    if role == 'PERSONEL':
        display_items = [i for i in inventory if i['user_email'] == user]
    else:
        display_items = inventory
    return render_template('inventory.html', items=display_items)

@app.route('/export-excel')
def export_excel():
    df = pd.DataFrame(jobs)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="rapor.xlsx", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
