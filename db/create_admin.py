import sqlite3
import hashlib

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_initial_admin():
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    
    # Tabloyu kontrol et (Database.py ile aynı yapıda)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        phone TEXT
    )''')
    
    username = "admin"
    password = "123"
    hashed_pw = hash_password(password)
    
    try:
        c.execute("INSERT INTO users (name, username, password, role) VALUES (?, ?, ?, ?)", 
                  ("Sistem Yöneticisi", username, hashed_pw, "Admin"))
        conn.commit()
        print("Admin kullanıcısı başarıyla oluşturuldu.")
    except sqlite3.IntegrityError:
        # Kullanıcı varsa şifreyi güncelle (Hata almamak için)
        c.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_pw, username))
        conn.commit()
        print("Admin kullanıcısı zaten vardı, şifre '123' olarak güncellendi.")
    
    conn.close()

if __name__ == "__main__":
    create_initial_admin()
