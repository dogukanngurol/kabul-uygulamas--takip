import sqlite3
import hashlib

DB_NAME = "app.db"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (name, email, phone, password, role)
        VALUES (?, ?, ?, ?, ?)
    """, (
        "Admin",
        "admin@sirket",
        "0000000000",
        hash_password("1234"),
        "Admin"
    ))

    conn.commit()
    conn.close()
    print("Admin (admin@sirket) başarıyla oluşturuldu.")

if __name__ == "__main__":
    create_admin()
