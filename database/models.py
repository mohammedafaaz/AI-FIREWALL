import sqlite3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH


def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Users ──────────────────────────────────────────────────────────────────

def get_user_by_username(username):
    conn = get_conn()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id):
    conn = get_conn()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def create_user(username, password_hash, role='employee', department=None):
    conn = get_conn()
    conn.execute(
        'INSERT INTO users (username, password_hash, role, department) VALUES (?, ?, ?, ?)',
        (username, password_hash, role, department)
    )
    conn.commit()
    conn.close()


# ── Prompt Events ──────────────────────────────────────────────────────────

def log_prompt_event(session_id, user_id, prompt_text, blocked, reason, score, module):
    conn = get_conn()
    conn.execute(
        '''INSERT INTO prompt_events
           (session_id, user_id, prompt_text, blocked, reason, score, module)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (session_id, user_id, prompt_text, 1 if blocked else 0, reason, score, module)
    )
    conn.commit()
    conn.close()


def get_recent_prompt_events(limit=20, user_id=None):
    conn = get_conn()
    if user_id:
        rows = conn.execute(
            '''SELECT pe.*, u.username 
               FROM prompt_events pe 
               LEFT JOIN users u ON pe.user_id = u.id 
               WHERE pe.user_id = ? 
               ORDER BY pe.timestamp DESC LIMIT ?''', 
            (user_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            '''SELECT pe.*, u.username 
               FROM prompt_events pe 
               LEFT JOIN users u ON pe.user_id = u.id 
               ORDER BY pe.timestamp DESC LIMIT ?''', 
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_blocked_events(limit=50):
    """Returns only blocked events — used by Threat Replay page."""
    conn = get_conn()
    rows = conn.execute(
        '''SELECT pe.*, u.username
           FROM prompt_events pe
           LEFT JOIN users u ON pe.user_id = u.id
           WHERE pe.blocked = 1
           ORDER BY pe.timestamp DESC LIMIT ?''',
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats_today():
    conn = get_conn()
    blocked = conn.execute(
        "SELECT COUNT(*) as cnt FROM prompt_events WHERE blocked=1 AND date(timestamp)=date('now')"
    ).fetchone()['cnt']
    conn.close()
    return blocked


def get_total_threats():
    conn = get_conn()
    total = conn.execute(
        "SELECT COUNT(*) as cnt FROM prompt_events WHERE blocked=1"
    ).fetchone()['cnt']
    conn.close()
    return total


def get_threats_per_module():
    conn = get_conn()
    rows = conn.execute(
        "SELECT module, COUNT(*) as cnt FROM prompt_events WHERE blocked=1 GROUP BY module"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_threats_per_hour_7days():
    conn = get_conn()
    rows = conn.execute(
        """SELECT strftime('%Y-%m-%d %H:00', timestamp) as hour, COUNT(*) as cnt
           FROM prompt_events
           WHERE timestamp >= datetime('now', '-7 days')
           GROUP BY hour ORDER BY hour"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_threats_per_day_10days():
    conn = get_conn()
    rows = conn.execute(
        """SELECT strftime('%Y-%m-%d', timestamp) as day, COUNT(*) as cnt
           FROM prompt_events
           WHERE timestamp >= datetime('now', '-7 days')
           GROUP BY day ORDER BY day"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_threats_by_type():
    conn = get_conn()
    rows = conn.execute(
        "SELECT module, COUNT(*) as cnt FROM prompt_events GROUP BY module"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Session Messages ───────────────────────────────────────────────────────

def save_session_message(session_id, user_id, message, role, threat_score=0.0):
    conn = get_conn()
    conn.execute(
        '''INSERT INTO session_messages (session_id, user_id, message, role, threat_score)
           VALUES (?, ?, ?, ?, ?)''',
        (session_id, user_id, message, role, threat_score)
    )
    conn.commit()
    conn.close()


def get_session_messages(session_id):
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM session_messages WHERE session_id = ? ORDER BY timestamp ASC',
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_last_threat_scores(session_id, limit=5):
    conn = get_conn()
    rows = conn.execute(
        '''SELECT threat_score FROM session_messages
           WHERE session_id = ? AND role = 'user'
           ORDER BY timestamp DESC LIMIT ?''',
        (session_id, limit)
    ).fetchall()
    conn.close()
    return [r['threat_score'] for r in rows]


def get_active_sessions_count():
    conn = get_conn()
    result = conn.execute(
        "SELECT COUNT(DISTINCT session_id) as cnt FROM session_messages WHERE timestamp >= datetime('now', '-1 hour')"
    ).fetchone()['cnt']
    conn.close()
    return result


# ── Action Queue ───────────────────────────────────────────────────────────

def add_action_to_queue(action_text, requested_by, risk_level):
    conn = get_conn()
    conn.execute(
        'INSERT INTO action_queue (action_text, requested_by, risk_level) VALUES (?, ?, ?)',
        (action_text, requested_by, risk_level)
    )
    conn.commit()
    conn.close()


def get_action_by_id(action_id):
    conn = get_conn()
    action = conn.execute('SELECT * FROM action_queue WHERE id = ?', (action_id,)).fetchone()
    conn.close()
    return dict(action) if action else None


def delegate_action_to_hr(action_id, delegated_by):
    conn = get_conn()
    conn.execute(
        "UPDATE action_queue SET delegated_to='hr', delegated_by=?, delegated_at=datetime('now') WHERE id=?",
        (delegated_by, action_id)
    )
    conn.commit()
    conn.close()


def get_pending_actions():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM action_queue WHERE status = 'PENDING' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_actions():
    conn = get_conn()
    rows = conn.execute(
        '''SELECT aq.*, u.username 
           FROM action_queue aq
           LEFT JOIN users u ON aq.requested_by = u.id
           ORDER BY aq.created_at DESC'''
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def approve_action(action_id, reviewed_by):
    conn = get_conn()
    conn.execute(
        "UPDATE action_queue SET status='APPROVED', reviewed_by=?, reviewed_at=datetime('now') WHERE id=?",
        (reviewed_by, action_id)
    )
    conn.commit()
    conn.close()


def reject_action(action_id, reviewed_by):
    conn = get_conn()
    conn.execute(
        "UPDATE action_queue SET status='REJECTED', reviewed_by=?, reviewed_at=datetime('now') WHERE id=?",
        (reviewed_by, action_id)
    )
    conn.commit()
    conn.close()


def get_pending_count():
    conn = get_conn()
    result = conn.execute(
        "SELECT COUNT(*) as cnt FROM action_queue WHERE status='PENDING'"
    ).fetchone()['cnt']
    conn.close()
    return result


# ── Blocklist ──────────────────────────────────────────────────────────────

def add_blocklist_entry(pattern, source='mutation_engine', added_by='auto'):
    conn = get_conn()
    conn.execute(
        'INSERT INTO blocklist_entries (pattern, source, added_by) VALUES (?, ?, ?)',
        (pattern, source, added_by)
    )
    conn.commit()
    conn.close()


def get_blocklist():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM blocklist_entries ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Admin Alerts ───────────────────────────────────────────────────────────

def add_admin_alert(alert_type, message, severity):
    conn = get_conn()
    conn.execute(
        'INSERT INTO admin_alerts (type, message, severity) VALUES (?, ?, ?)',
        (alert_type, message, severity)
    )
    conn.commit()
    conn.close()


def get_unread_alerts():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM admin_alerts WHERE read=0 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_alerts_read():
    conn = get_conn()
    conn.execute("UPDATE admin_alerts SET read=1")
    conn.commit()
    conn.close()


# ── Fingerprints ───────────────────────────────────────────────────────────

def save_fingerprint(session_id, user_id, embedding_json, features_json, anomaly_score):
    conn = get_conn()
    conn.execute(
        '''INSERT INTO fingerprints (session_id, user_id, embedding, features, anomaly_score)
           VALUES (?, ?, ?, ?, ?)''',
        (session_id, user_id, embedding_json, features_json, anomaly_score)
    )
    conn.commit()
    conn.close()


def get_session_fingerprints(session_id):
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM fingerprints WHERE session_id = ? ORDER BY timestamp ASC',
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_known_attack_signatures():
    conn = get_conn()
    rows = conn.execute('SELECT * FROM known_attack_signatures').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_threat_users(limit=5):
    conn = get_conn()
    rows = conn.execute(
        '''SELECT u.username, u.id, COUNT(*) as threat_count
           FROM prompt_events pe
           JOIN users u ON pe.user_id = u.id
           WHERE pe.blocked = 1
           GROUP BY u.id
           ORDER BY threat_count DESC
           LIMIT ?''',
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]