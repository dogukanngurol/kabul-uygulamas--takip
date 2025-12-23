import datetime
import os
import uuid
import zipfile
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd

app = Flask(__name__)
app.secret_key = "gemini_flash_key_2025"

# --- CONFIG & MOCK DATA ---
CITIES = ["İstanbul", "Ankara", "İzmir", "Adana", "Bursa", "Antalya", "Konya", "Diyarbakır"] + [f"Şehir_{i}" for i in range(1, 74)]

users = [
    {"email": "admin@sirket.com", "role": "ADMIN", "name": "Admin", "phone": "0500", "password": "123"},
    {"email": "filiz@deneme.com", "role": "MUDUR", "name": "Filiz", "phone": "0501", "password": "123"},
    {"email": "dogukan@deneme.com", "role": "PERSONEL", "name": "Doğukan", "phone": "0502", "password": "123"},
    {"email": "doguscan@deneme.com", "role": "PERSONEL", "name": "Doğuşcan", "phone": "0503", "password": "123"},
    {"email": "cuneyt@deneme.com", "role": "PERSONEL", "name": "Cüneyt", "phone": "0504", "password": "123"}
]

jobs = [] 
inventory = []

# --- HELPERS ---
def get_greeting(name):
    hour = datetime.datetime.now().hour
    if 8 <= hour < 12: return f"Günaydın {name} İyi Çalışmalar"
    elif 12 <= hour < 18: return f"İyi Günler {name} İyi Çalışmalar"
    elif 18 <= hour < 24: return f"İyi Akşamlar {name} İyi Çalışmalar"
    else: return f"İyi Geceler {name} İyi Çalışmalar"

# --- ROUTES ---
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    pwd = request.form.get('password')
    user = next((u for u in users if u['email'] == email and u['password'] == pwd), None)
    if user:
        session['user'], session['role'], session['name'] = user['email'], user['role'], user['name']
        return redirect(url_for('dashboard'))
    return "Hata", 401

@app.route('/')
def dashboard():
    if 'user' not in session: return "Giriş Yapılmadı"
    u_role, u_email = session['role'], session['user']
    
    weekly_jobs = [j for j in jobs if j['created_at'] > (datetime.datetime.now() - datetime.timedelta(days=7))]
    
    context = {
        "greeting": get_greeting(session['name']),
        "role": u_role,
        "weekly_count": len(weekly_jobs),
        "completed": len([j for j in jobs if j['status'] == 'İŞ TAMAMLANDI']),
        "my_jobs": [j for j in jobs if j['assigned_to'] == u_email] if u_role == 'PERSONEL' else jobs,
        "assigned_count": len([j for j in jobs if j['status'] == 'ATANDI'])
    }
    return f"Hoşgeldiniz: {context['greeting']} | Rol: {u_role}"

@app.route('/user/action', methods=['POST'])
def user_action():
    if session.get('role') not in ['ADMIN', 'MUDUR']: return "Yetkisiz", 403
    action = request.form.get('type')
    if action == "add":
        users.append({"email": request.form.get('email'), "role": request.form.get('role'), "name": request.form.get('name'), "password": "123"})
    elif action == "delete":
        global users
        users = [u for u in users if u['email'] != request.form.get('email')]
    return redirect(url_for('dashboard'))

@app.route('/profile/update', methods=['POST'])
def profile_update():
    if session.get('role') == 'MUDUR': return "Müdür güncelleyemez", 403
    for u in users:
        if u['email'] == session['user']:
            u['phone'] = request.form.get('phone')
            u['email'] = request.form.get('email')
            u['password'] = request.form.get('password')
            session['user'] = u['email']
    return "Profil Kaydedildi"

@app.route('/job/assign', methods=['POST'])
def job_assign():
    if session.get('role') not in ['ADMIN', 'MUDUR']: return "Yetkisiz", 403
    job = {
        "id": str(uuid.uuid4())[:8],
        "assigned_to": request.form.get('staff'),
        "city": request.form.get('city'),
        "status": "Giriş Mail Onayı Bekler",
        "notes": "",
        "photos": [],
        "created_at": datetime.datetime.now()
    }
    jobs.append(job)
    return "İş Atandı"

@app.route('/job/worker_update', methods=['POST'])
def worker_update():
    job_id = request.form.get('job_id')
    action = request.form.get('action') # 'TASLAK' | 'GONDER'
    status = request.form.get('status')
    
    for j in jobs:
        if j['id'] == job_id:
            j['notes'] = request.form.get('notes')
            if 'photos' in request.files:
                for f in request.files.getlist('photos'):
                    fname = f"{uuid.uuid4()}_{f.filename}"
                    j['photos'].append(fname)
            
            j['status'] = 'TASLAK' if action == 'TASLAK' else status
    return "İşlem Başarılı"

@app.route('/job/manager_approval', methods=['POST'])
def manager_approval():
    if session.get('role') != 'MUDUR': return "Yetkisiz", 403
    job_id = request.form.get('job_id')
    decision = request.form.get('decision')
    
    for j in jobs:
        if j['id'] == job_id:
            if decision == 'RET':
                j['status'] = 'RET EDİLDİ'
                j['ret_reason'] = request.form.get('reason')
            elif decision == 'KABUL_YAPILABILIR':
                j['status'] = 'Kabul Yapılabilir'
            elif decision == 'TT_ONAY_BEKLE':
                j['status'] = 'Türk Telekom Onayında'
            elif decision == 'HAK_EDIS_GONDER':
                j['status'] = 'Hak Ediş Bekleniyor'
                j['assigned_to'] = 'filiz@deneme.com'
    return "Onay İşlemi Tamam"

@app.route('/hakedis/finalize', methods=['POST'])
def hakedis_finalize():
    if session.get('user') != 'filiz@deneme.com': return "Yetkisiz", 403
    job_id = request.form.get('job_id')
    for j in jobs:
        if j['id'] == job_id: j['status'] = 'Hak Edişi Alındı'
    return "Hak Ediş Tamamlandı"

@app.route('/export/excel')
def export_excel():
    f_status = request.args.get('status')
    data = jobs
    if f_status == 'TAMAMLANAN': data = [j for j in jobs if j['status'] == 'İŞ TAMAMLANDI']
    elif f_status == 'TAMAMLANAMAYAN': data = [j for j in jobs if j['status'] in ['GİRİŞ YAPILAMADI', 'TEPKILI', 'MAL SAHİBİ GELMİYOR']]
    
    df = pd.DataFrame(data)
    out = BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    out.seek(0)
    return send_file(out, download_name="rapor.xlsx", as_attachment=True)

@app.route('/export/zip/<job_id>')
def export_zip(job_id):
    job = next((j for j in jobs if j['id'] == job_id), None)
    mem = BytesIO()
    with zipfile.ZipFile(mem, 'w') as zf:
        for p in job['photos']: zf.writestr(p, b"data")
    mem.seek(0)
    return send_file(mem, download_name=f"{job_id}_photos.zip", as_attachment=True)

@app.route('/inventory/action', methods=['POST'])
def inventory_action():
    if session.get('role') == 'MUDUR':
        inventory.append({"id": len(inventory)+1, "user": request.form.get('staff'), "item": request.form.get('item')})
    return "Zimmetlendi"

if __name__ == '__main__':
    app.run(debug=True)
