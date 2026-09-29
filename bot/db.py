import sqlite3
import random
import uuid

DB_NAME = "lottery.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            candidate_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cur.execute("""
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('phase', 'registration')
    """)

    conn.commit()
    conn.close()


def register_member(user_id, username=None, first_name=None):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO users
        (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (user_id, username, first_name))

    conn.commit()

    cur.execute("""
        SELECT id FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()
    conn.close()

    return row[0] if row else None


def add_candidate(name):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO candidates (name)
        VALUES (?)
    """, (name,))

    conn.commit()
    conn.close()


def candidates():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name
        FROM candidates
        ORDER BY id
    """)

    rows = cur.fetchall()
    conn.close()

    return rows


def cast_vote(user_id, candidate_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM votes
        WHERE user_id = ?
    """, (user_id,))

    if cur.fetchone():
        conn.close()
        return False, "❌ شما قبلاً رأی داده‌اید."

    cur.execute("""
        SELECT id FROM candidates
        WHERE id = ?
    """, (candidate_id,))

    if not cur.fetchone():
        conn.close()
        return False, "❌ نامزد موردنظر پیدا نشد."

    cur.execute("""
        INSERT INTO votes (user_id, candidate_id)
        VALUES (?, ?)
    """, (user_id, candidate_id))

    conn.commit()
    conn.close()

    return True, "✅ رأی شما با موفقیت ثبت شد."


def start_vote():
    set_phase("voting")


def end_vote():
    set_phase("ended")


def set_phase(phase):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO settings (key, value)
        VALUES ('phase', ?)
    """, (phase,))

    conn.commit()
    conn.close()


def status():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT value FROM settings
        WHERE key = 'phase'
    """)
    phase_row = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM users")
    members = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM candidates")
    candidate_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM votes")
    vote_count = cur.fetchone()[0]

    conn.close()

    return {
        "phase": phase_row[0] if phase_row else "registration",
        "members": members,
        "candidates": candidate_count,
        "votes": vote_count
    }


def results_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            c.id,
            c.name,
            COUNT(v.id) AS vote_count
        FROM candidates c
        LEFT JOIN votes v
            ON c.id = v.candidate_id
        GROUP BY c.id, c.name
        ORDER BY vote_count DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return rows


def draw_winner():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            c.name,
            COUNT(v.id) AS votes
        FROM candidates c
        JOIN votes v
            ON c.id = v.candidate_id
        GROUP BY c.id, c.name
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return None

    # انتخاب تصادفی از بین نامزدهای دارای رأی
    winner = random.choice(rows)

    return {
        "name": winner[0],
        "votes": winner[1],
        "draw_id": str(uuid.uuid4())
    }
