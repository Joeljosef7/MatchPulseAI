import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect("matchpulse.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_date TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS followed_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            team_name TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect("matchpulse.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def follow_team(user_id, team_name):
    conn = sqlite3.connect("matchpulse.db")
    team_name = team_name.strip()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM followed_teams 
        WHERE user_id = ? AND team_name = ?
    ''', (user_id, team_name))
    exists = cursor.fetchone()
    if not exists:
        cursor.execute('''
            INSERT INTO followed_teams (user_id, team_name)
            VALUES (?, ?)
        ''', (user_id, team_name))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def unfollow_team(user_id, team_name):
    conn = sqlite3.connect("matchpulse.db")
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM followed_teams 
        WHERE user_id = ? AND team_name = ?
    ''', (user_id, team_name))
    conn.commit()
    conn.close()

def get_followed_teams(user_id):
    conn = sqlite3.connect("matchpulse.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT team_name FROM followed_teams 
        WHERE user_id = ?
    ''', (user_id,))
    teams = [row[0] for row in cursor.fetchall()]
    conn.close()
    return teams
