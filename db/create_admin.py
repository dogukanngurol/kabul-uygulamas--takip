import sqlite3

DB_NAME = "app.db"

def create_admin():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (name, email, phone, password, role)
        VALUES (?, ?, ?, ?, ?)
    """, (
        "Admin",
        "admin@anatoli.com",
        "0000000000",
        "1234",
        "Admin"
    ))

    conn.commit()
    conn.close()
    print("Admin kullanıcı oluşturuldu.")

if __name__ == "__main__":
    create_admin()
