import sqlite3
import bcrypt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH


def seed():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    users = [
        ('admin', 'admin123', 'admin', 'IT Security'),
        ('hr_manager', 'hr123', 'hr', 'Human Resources'),
        ('developer', 'dev123', 'employee', 'Engineering'),
    ]
    for username, password, role, dept in users:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            c.execute(
                'INSERT INTO users (username, password_hash, role, department) VALUES (?, ?, ?, ?)',
                (username, pw_hash, role, dept)
            )
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    print('[FIREWALL][SEED] Database seeded successfully.')


if __name__ == '__main__':
    seed()
