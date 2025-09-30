import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')

def init():
    if os.path.exists(DB_PATH):
        print('DB already exists at', DB_PATH)
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user TEXT,
        qid TEXT,
        answer TEXT
    )
    ''')
    conn.commit()
    conn.close()
    print('Created DB at', DB_PATH)

if __name__ == '__main__':
    init()
