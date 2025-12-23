import sqlite3
import hashlib
from datetime import datetime
import streamlit as st
from utils.constants import STATUSES, ROLES

DB_NAME = "app.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def create_tables():
    conn = get_connection()
    c = conn.cursor()

    # users tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # jobs tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            detail TEXT,
            city TEXT,
            assigned_to INTEGER,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            tt_approved BOOLEAN DEFAULT 0,
            hak_edis_status TEXT,
            FOREIGN KEY(assigned_to) REFERENCES users(id)
        )
    ''')

    # job_files tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )
    ''')

    # inventory tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            assigned_to INTEGER,
            assigned_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(assigned_to) REFERENCES users(id),
            FOREIGN KEY(assigned_by) REFERENCES users(id)
        )
    ''')

    # Varsayılan Admin Hesabı
    try:
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("""
            INSERT INTO users (name, email, phone, password, role) 
            VALUES (?, ?, ?, ?, ?)
        """, ("Sistem Admin", "admin@isletme.com", "0000", admin_pass, "Admin"))
    except sqlite3.IntegrityError:
        pass

    conn.commit()
    conn.close()

def login_user(email, password):
    conn = get_connection()
    c = conn.cursor()
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    c.execute("""
        SELECT id, name, role FROM users 
        WHERE email = ? AND password = ?
    """, (email, pwd_hash))
    user = c.fetchone()
    conn.close()
    
    if user:
        st.session_state.logged_in = True
        st.session_state.user_id = user[0]
        st.session_state.user_name = user[1]
        st.session_state.user_role = user[2]
        return True
    return False

def get_users_by_role(role_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name FROM users WHERE role = ?", (role_name,))
    data = c.fetchall()
    conn.close()
    return data
