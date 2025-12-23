import sqlite3
import hashlib
from datetime import datetime
from db.database import get_connection
from utils.constants import STATUSES

def add_user(name, email, phone, password, role):
    conn = get_connection()
    c = conn.cursor()
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("""
            INSERT INTO users (name, email, phone, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, phone, pwd_hash, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def assign_job(title, detail, city, assigned_to, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO jobs (title, detail, city, assigned_to, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, detail, city, assigned_to, status, datetime.now()))
    conn.commit()
    conn.close()

def update_job_status(job_id, status, tt_approved=0):
    conn = get_connection()
    c = conn.cursor()
    completed_at = datetime.now() if status == "TAMAMLANDI" else None
    c.execute("""
        UPDATE jobs 
        SET status = ?, tt_approved = ?, completed_at = ?
        WHERE id = ?
    """, (status, tt_approved, completed_at, job_id))
    conn.commit()
    conn.close()

def list_jobs(user_id=None, role=None):
    conn = get_connection()
    c = conn.cursor()
    if role in ["Admin", "Yönetici", "Müdür"]:
        c.execute("SELECT * FROM jobs")
    else:
        c.execute("SELECT * FROM jobs WHERE assigned_to = ?", (user_id,))
    jobs = c.fetchall()
    conn.close()
    return jobs

def update_hak_edis(job_id, hak_edis_status):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE jobs SET hak_edis_status = ? WHERE id = ?", (hak_edis_status, job_id))
    conn.commit()
    conn.close()

def add_inventory_assignment(item_name, assigned_to, assigned_by):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO inventory (item_name, assigned_to, assigned_by, created_at)
        VALUES (?, ?, ?, ?)
    """, (item_name, assigned_to, assigned_by, datetime.now()))
    conn.commit()
    conn.close()

def list_inventory():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT i.id, i.item_name, u1.name as staff, u2.name as assigner, i.created_at
        FROM inventory i
        LEFT JOIN users u1 ON i.assigned_to = u1.id
        LEFT JOIN users u2 ON i.assigned_by = u2.id
    """)
    items = c.fetchall()
    conn.close()
    return items
