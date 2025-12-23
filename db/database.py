import sqlite3
import hashlib

DB_NAME = "app.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    
    # Kullanıcılar Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Görevler Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            assigned_to INTEGER,
            status TEXT NOT NULL,
            created_by INTEGER,
            FOREIGN KEY(assigned_to) REFERENCES users(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        )
    ''')
    
    # Varsayılan Admin Kullanıcısı (Şifre: admin123)
    # Gerçek uygulamada şifreleme (hash) daha güvenli yapılmalıdır.
    try:
        default_pass = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                  ("admin", default_pass, "Admin"))
    except sqlite3.IntegrityError:
        pass # Admin zaten var

    conn.commit()
    conn.close()

def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT id, username, role FROM users WHERE username = ? AND password = ?", (username, pwd_hash))
    user = c.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users")
    data = c.fetchall()
    conn.close()
    return data

def add_task(title, description, assigned_to, created_by, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (title, description, assigned_to, created_by, status) VALUES (?, ?, ?, ?, ?)",
              (title, description, assigned_to, created_by, status))
    conn.commit()
    conn.close()

def get_tasks_for_user(user_id, role):
    conn = get_connection()
    c = conn.cursor()
    if role in ["Admin", "Yönetici", "Müdür"]:
        # Yöneticiler tüm görevleri görür
        query = """
            SELECT t.id, t.title, t.description, t.status, u.username as assigned_user 
            FROM tasks t 
            LEFT JOIN users u ON t.assigned_to = u.id
        """
        c.execute(query)
    else:
        # Saha personeli sadece kendine atananları görür
        query = """
            SELECT t.id, t.title, t.description, t.status, u.username as assigned_user 
            FROM tasks t 
            LEFT JOIN users u ON t.assigned_to = u.id 
            WHERE t.assigned_to = ?
        """
        c.execute(query, (user_id,))
    
    data = c.fetchall()
    conn.close()
    return data
