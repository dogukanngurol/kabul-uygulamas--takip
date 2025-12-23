import sqlite3

def get_connection():
    return sqlite3.connect("app.db", check_same_thread=False)

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        phone TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        detail TEXT,
        city TEXT,
        assigned_to INTEGER,
        status TEXT,
        created_at TEXT,
        completed_at TEXT,
        tt_approved INTEGER DEFAULT 0,
        FOREIGN KEY(assigned_to) REFERENCES users(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT,
        assigned_to INTEGER,
        assigned_by INTEGER,
        created_at TEXT,
        FOREIGN KEY(assigned_to) REFERENCES users(id),
        FOREIGN KEY(assigned_by) REFERENCES users(id)
    )''')
    
    conn.commit()
    conn.close()
