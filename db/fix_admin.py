import sqlite3
import hashlib

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def fix_database_and_admin():
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    
    # Tabloyu en güncel haliyle garantiye al
    c.execute("DROP TABLE IF EXISTS users")
    c.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        phone TEXT
    )''')
    
    # Sabit Admin Bilgileri
    username = "admin"
    password = "123"
    hashed_pw = hash_password(password)
    
    c.execute("""
        INSERT INTO users (name, username, password, role, phone) 
        VALUES (?, ?, ?, ?, ?)
    """, ("Sistem Yöneticisi", username, hashed_pw, "Admin", "0000"))
    
    conn.commit()
    conn.close()
    print("Veritabanı sıfırlandı ve admin:123 hesabı tanımlandı.")

if __name__ == "__main__":
    fix_database_and_admin()
