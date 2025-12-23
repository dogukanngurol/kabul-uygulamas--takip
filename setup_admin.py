import sqlite3
import hashlib

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

conn = sqlite3.connect("app.db")
c = conn.cursor()

# Varsayılan Admin Kullanıcısı
username = "admin"
password = "123"
hashed_pw = hash_password(password)

c.execute("INSERT OR IGNORE INTO users (name, username, password, role) VALUES (?, ?, ?, ?)", 
          ("Sistem Yöneticisi", username, hashed_pw, "Admin"))

conn.commit()
conn.close()

print(f"Kullanıcı: {username}")
print(f"Şifre: {password}")
