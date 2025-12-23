import sqlite3
import hashlib

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

DB_NAME = "app.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

cursor.execute("""
INSERT INTO users (name, email, phone, password, role)
VALUES (?, ?, ?, ?, ?)
""", (
    "Admin",
    "admin@anatoli.com",
    "0000000000",
    hash_password("1234"),
    "Admin"
))

conn.commit()
conn.close()
print("Admin hashli olarak oluşturuldu.")
