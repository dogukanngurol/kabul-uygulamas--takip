import datetime
import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from io import BytesIO
import zipfile

app = Flask(__name__)
app.secret_key = "secret_key_logic_2025"

# --- MOCK DATA & CONFIG ---
CITIES = ["İstanbul", "Adana", "Ankara", "İzmir", "Bursa", "Antalya", "Konya", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"]

users = [
    {"email": "admin@sirket.com", "role": "ADMIN", "name": "Admin", "phone": "000", "password": "123"},
    {"email": "filiz@deneme.com", "role": "MUDUR", "name": "Filiz", "phone": "111", "password": "123"},
    {"email": "dogukan@deneme.com", "role": "PERSONEL", "name": "Doğukan", "phone": "222", "password": "123"},
    {"email": "doguscan@deneme.com", "role": "PERSONEL", "name": "Doğuşcan", "phone": "333", "password": "123"},
    {"email": "cuneyt@deneme.com", "role": "PERSONEL", "name": "Cüneyt", "phone": "444", "password": "123"}
]

jobs = [] # {id, assigned_to, city, status, notes, photos: [], tt_onay: bool, ret_sebebi: "", date: datetime, created_at: datetime}
inventory = [] # {id, user_email, item_name, serial}

# --- LOGIC HELPERS ---
def get_greeting(name):
    hour = datetime.datetime.now().hour
    if 8 <= hour < 12: return f"Günaydın {name} İyi Çalışmalar"
    elif 12 <= hour < 18: return f"İyi Günler {name} İyi Çalışmalar"
    elif 18 <= hour < 24: return f"İyi Akşamlar {name} İyi Çalışmalar"
    else: return f"İyi Geceler {name} İyi Çalışmalar"

def get_weekly_count():
    now = datetime.datetime.now()
    start_of_week = now - datetime.timedelta(days=now.weekday())
    return len([j for j in jobs if j['created_at'] >= start_of_week])

# --- ROUTES ---

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    pwd = request.form.get('password')
    user = next((u for u in users if u['email'] == email and u['password'] == pwd), None)
    if user:
        session['user'] = user['email']
        session['role'] = user['role']
        session['name'] = user['name']
        return redirect(url_for('dashboard'))
    return "Hatalı Giriş", 401

@app.route('/')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    u_role, u_email = session['role'], session['user']
    greeting = get_greeting(session['name'])
    
    context = {
        "greeting": greeting,
        "role": u_role,
        "weekly_total": get_weekly_count(),
        "completed_total": len([j for j in jobs if j['status'] == 'İŞ TAMAMLANDI']),
        "pending_total": len([j for j in jobs if j['status'] == 'ATANDI']),
        "my_jobs": [j for j in jobs if j['assigned_to'] == u_email],
        "assigned_jobs": [j for j in jobs if j['status'] == 'ATANDI']
    }
    return render_template('dashboard.html', **context)

@app.route('/user/manage', methods=['POST', 'DELETE'])
def manage_users():
    if session.get('role') not in ['ADMIN', 'MUDUR']: return "Yetkisiz", 403
    if request.method == 'POST':
        users.append({"email": request.form.get('email'), "role": request.form.get('role'), "name": request.form.get('name'), "phone": request.form.get('phone'), "password": "123"})
    return redirect(url_for('dashboard'))

@app.route('/profile/update', methods=['POST'])
def update_profile():
    if session.get('role') == 'MUDUR': return "Müdür bu yetkiye sahip değil", 403
    u_email = session['user']
    for u in users:
        if u['email'] == u_email:
            u['phone'] = request.form.get('phone')
            u['email'] = request.form.get('email')
            if request.form.get('password'): u['password'] = request.form.get('password')
            session['user'] = u['email']
    return redirect(url_for('dashboard'))

@app.route('/job/assign', methods=['POST'])
def assign_job():
    if session.get('role') not in ['ADMIN', 'MUDUR']: return "Yetkisiz", 403
    new_job = {
        "id": str(uuid.uuid4())[:8],
        "assigned_to": request.form.get('staff'),
        "city": request.form.get('city'),
        "status": "ATANDI",
        "notes": "",
        "photos": [],
        "ret_sebebi": "",
        "created_at": datetime.datetime.now()
    }
    jobs.append(new_job)
    return redirect(url_for('dashboard'))

@app.route('/job/process', methods=['POST'])
def process_job():
    job_id = request.form.get('job_id')
    action = request.form.get('action') # 'TASLAK' or 'GONDER'
    status = request.form.get('status') # 'İŞ TAMAMLANDI', 'GİRİŞ YAPILAMADI', etc.
    
    for j in jobs:
        if j['id'] == job_id:
            j['notes'] = request.form.get('notes')
            # DB OPTIMIZATION: Store only filenames/paths
            if 'files' in request.files:
                for file in request.files.getlist('files'):
                    filename = f"{uuid.uuid4()}_{file.filename}"
                    # file.save(os.path.join('storage', filename))
                    j['photos'].append(filename)
            
            if status == 'Giriş Mail Onayı Bekler':
                j['status'] = 'Giriş Mail Onayı Bekler'
            else:
                j['status'] = 'TASLAK' if action == 'TASLAK' else status
    return redirect(url_for('dashboard'))

@app.route('/job/list')
def list_jobs():
    f_status = request.args.get('filter_status')
    f_staff = request.args.get('staff')
    f_city = request.args.get('city')
    
    filtered = jobs
    if f_status == 'Tamamlanan İşler':
        filtered = [j for j in jobs if j['status'] == 'İŞ TAMAMLANDI']
    elif f_status == 'Tamamlanamayan İşler':
        filtered = [j for j in jobs if j['status'] in ['GİRİŞ YAPILAMADI', 'TEPKILI', 'MAL SAHİBİ GELMİYOR']]
    
    if f_staff: filtered = [j for j in filtered if j['assigned_to'] == f_staff]
    if f_city: filtered = [j for j in filtered if j['city'] == f_city]
    
    return render_template('list.html', jobs=filtered, cities=CITIES, staff=[u for u in users if u['role'] == 'PERSONEL'])

@app.route('/job/approval', methods=['POST'])
def job_approval():
    job_id = request.form.get('job_id')
    decision = request.form.get('decision') # 'KABUL', 'RET', 'TT_ONAY', 'HAK_EDIS_GONDER'
    
    for j in jobs:
        if j['id'] == job_id:
            if decision == 'RET':
                j['status'] = 'RET EDİLDİ'
                j['ret_sebebi'] = request.form.get('reason')
            elif decision == 'KABUL_YAPILABILIR':
                j['status'] = 'Kabul Yapılabilir'
            elif decision == 'TT_ONAY':
                j['status'] = 'Türk Telekom Onayında'
            elif decision == 'HAK_EDIS_GONDER':
                j['status'] = 'Hak Ediş Bekleniyor'
                j['assigned_to'] = 'filiz@deneme.com'
    return redirect(url_for('dashboard'))

@app.route('/hakedis/manage', methods=['POST'])
def hakedis_manage():
    job_id = request.form.get('job_id')
    for j in jobs:
        if j['id'] == job_id: j['status'] = 'Hak Edişi Alındı'
    return redirect(url_for('dashboard'))

@app.route('/inventory/manage', methods=['POST'])
def manage_inventory():
    if session.get('role') != 'MUDUR': return "Yetkisiz", 403
    inventory.append({
        "id": len(inventory)+1, 
        "user_email": request.form.get('staff'), 
        "item": request.form.get('item'),
        "serial": request.form.get('serial')
    })
    return redirect(url_for('dashboard'))

@app.route('/export/excel')
def export_excel():
    df = pd.DataFrame(jobs)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    output.seek(0)
    return send_file(output, download_name="is_raporu.xlsx", as_attachment=True)

@app.route('/export/inventory')
def export_inventory():
    if session.get('role') != 'ADMIN': return "Yetkisiz", 403
    df = pd.DataFrame(inventory)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="envanter.xlsx", as_attachment=True)

@app.route('/download/photos/<job_id>')
def download_photos(job_id):
    job = next((j for j in jobs if j['id'] == job_id), None)
    if not job: return "Bulunamadı", 404
    
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for photo_name in job['photos']:
            # zf.write(os.path.join('storage', photo_name), photo_name)
            zf.writestr(photo_name, b"photo_content_placeholder")
    memory_file.seek(0)
    return send_file(memory_file, download_name=f"{job_id}_fotograflar.rar", as_attachment=True)

if __name__ == '__main__':
    # if not os.path.exists('storage'): os.makedirs('storage')
    app.run(debug=True)
