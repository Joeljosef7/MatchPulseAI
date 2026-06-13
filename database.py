import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_date TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS followed_teams (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            team_name TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_alerts (
            user_id BIGINT,
            match_id BIGINT,
            PRIMARY KEY (user_id, match_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fulltime_alerts (
            user_id BIGINT,
            match_id BIGINT,
            PRIMARY KEY (user_id, match_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_events_sent (
            user_id BIGINT,
            match_id BIGINT,
            event_type TEXT,
            event_value TEXT,
            PRIMARY KEY (user_id, match_id, event_type, event_value)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            action TEXT,
            logged_at DATE DEFAULT CURRENT_DATE
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()

def add_user(user_id, username, first_name):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, username, first_name, joined_date)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    ''', (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    cursor.close()
    conn.close()

def follow_team(user_id, team_name):
    team_name = team_name.strip()
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO users (user_id, username, first_name, joined_date)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    ''', (user_id, None, None, datetime.now().strftime("%Y-%m-%d")))

    cursor.execute('''
        SELECT 1 FROM followed_teams
        WHERE user_id = %s AND team_name = %s
    ''', (user_id, team_name))
    exists = cursor.fetchone()
    if not exists:
        cursor.execute('''
            INSERT INTO followed_teams (user_id, team_name)
            VALUES (%s, %s)
        ''', (user_id, team_name))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    cursor.close()
    conn.close()
    return False

def unfollow_team(user_id, team_name):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM followed_teams
        WHERE user_id = %s AND team_name = %s
    ''', (user_id, team_name))
    conn.commit()
    cursor.close()
    conn.close()

def get_followed_teams(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT team_name FROM followed_teams
        WHERE user_id = %s
    ''', (user_id,))
    teams = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return teams

def get_all_follows():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, team_name FROM followed_teams
    ''')
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def alert_already_sent(user_id, match_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM sent_alerts
        WHERE user_id = %s AND match_id = %s
    ''', (user_id, match_id))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

def mark_alert_sent(user_id, match_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sent_alerts (user_id, match_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    ''', (user_id, match_id))
    conn.commit()
    cursor.close()
    conn.close()

def fulltime_alert_sent(user_id, match_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM fulltime_alerts
        WHERE user_id = %s AND match_id = %s
    ''', (user_id, match_id))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

def mark_fulltime_alert_sent(user_id, match_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO fulltime_alerts (user_id, match_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    ''', (user_id, match_id))
    conn.commit()
    cursor.close()
    conn.close()

def event_already_sent(user_id, match_id, event_type, event_value):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM match_events_sent
        WHERE user_id = %s AND match_id = %s
        AND event_type = %s AND event_value = %s
    ''', (user_id, match_id, event_type, event_value))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

def mark_event_sent(user_id, match_id, event_type, event_value):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO match_events_sent
        (user_id, match_id, event_type, event_value)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    ''', (user_id, match_id, event_type, event_value))
    conn.commit()
    cursor.close()
    conn.close()

def log_activity(user_id, action):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_log (user_id, action)
        VALUES (%s, %s)
    ''', (user_id, action))
    conn.commit()
    cursor.close()
    conn.close()

def get_stats():
    conn = get_conn()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(DISTINCT user_id) FROM activity_log WHERE logged_at = %s",
        (today,)
    )
    dau = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM users WHERE joined_date = %s",
        (today,)
    )
    new_today = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(DISTINCT user_id) FROM followed_teams"
    )
    active_users = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM followed_teams"
    )
    total_follows = cursor.fetchone()[0]

    cursor.execute(
        "SELECT team_name, COUNT(*) as count FROM followed_teams GROUP BY team_name ORDER BY count DESC LIMIT 5"
    )
    top_teams = cursor.fetchall()

    cursor.execute(
        "SELECT action, COUNT(*) as count FROM activity_log WHERE logged_at = %s GROUP BY action ORDER BY count DESC LIMIT 5",
        (today,)
    )
    top_commands = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(*) FROM activity_log WHERE action = 'ai_question' AND logged_at = %s",
        (today,)
    )
    ai_today = cursor.fetchone()[0]

    cursor.close()
    conn.close()
    return total_users, dau, new_today, active_users, total_follows, top_teams, top_commands, ai_today

