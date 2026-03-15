import os
import sys
from datetime import datetime, timedelta, timezone

from flask import Flask, request, jsonify, send_from_directory
from flask_jwt_extended import (
    JWTManager, create_access_token, get_jwt_identity, verify_jwt_in_request
)
from flask_cors import CORS
import bcrypt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import JWT_SECRET_KEY, DATABASE_PATH
from database import models
from database.init_db import init_db
from middleware.auth import jwt_required_middleware, admin_required
from middleware.interceptor import process_prompt
from modules import shadow_prompt
from modules import mutation_replay

app = Flask(__name__, static_folder='frontend', static_url_path='')
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)

jwt = JWTManager(app)
CORS(app, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])

# ─── Init DB on startup ────────────────────────────────────────────────────
if not os.path.exists(DATABASE_PATH):
    init_db()


def api_response(success=True, data=None, error=None, module='CORE'):
    return jsonify({
        'success': success,
        'data': data,
        'error': error,
        'module': module,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


# ─── Static Frontend ────────────────────────────────────────────────────────
@app.route('/')
def serve_login():
    return send_from_directory('frontend', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('frontend', filename)


# ─── Health ─────────────────────────────────────────────────────────────────
@app.get('/api/health')
def health():
    return api_response(data={'status': 'ok', 'service': 'Shell Enterprise AI Firewall'})


# ─── Auth ────────────────────────────────────────────────────────────────────
@app.post('/api/auth/login')
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return api_response(False, error='Username and password required', module='AUTH'), 400

    user = models.get_user_by_username(username)
    if not user:
        return api_response(False, error='Invalid credentials', module='AUTH'), 401

    try:
        valid = bcrypt.checkpw(password.encode(), user['password_hash'].encode())
    except Exception:
        valid = False

    if not valid:
        return api_response(False, error='Invalid credentials', module='AUTH'), 401

    token = create_access_token(identity=str(user["id"]))
    return api_response(data={
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'department': user['department']
        }
    }, module='AUTH')


# ─── Chat ─────────────────────────────────────────────────────────────────────
@app.post('/api/chat/send')
@jwt_required_middleware
def chat_send():
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
    except Exception:
        return api_response(False, error='Auth required', module='CHAT'), 401

    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    session_id = data.get('session_id', f'sess_{user_id}_{int(datetime.now(timezone.utc).timestamp())}')

    if not prompt:
        return api_response(False, error='Prompt cannot be empty', module='CHAT'), 400

    user = models.get_user_by_id(user_id)
    user_role = user['role'] if user else 'employee'

    result = process_prompt(session_id, user_id, prompt, user_role)

    # Save user message to session
    if not result.get('blocked'):
        models.save_session_message(session_id, user_id, prompt, 'user', result.get('gaslighting_score', 0.0))

    return api_response(data=result, module='CHAT')


# ─── Scan Endpoints ──────────────────────────────────────────────────────────
@app.post('/api/scan/prompt')
@jwt_required_middleware
def scan_prompt_endpoint():
    from modules import prompt_injection
    data = request.get_json()
    text = data.get('text', '')
    result = prompt_injection.scan_prompt(text)
    return api_response(data=result, module='INJECTION')


@app.post('/api/monitor/response')
@jwt_required_middleware
def monitor_response_endpoint():
    from modules import behavior_monitor
    data = request.get_json()
    text = data.get('text', '')
    result = behavior_monitor.monitor_response(text)
    return api_response(data=result, module='BEHAVIOR')


@app.post('/api/dlp/scan')
@jwt_required_middleware
def dlp_scan_endpoint():
    from modules import dlp
    data = request.get_json()
    text = data.get('text', '')
    result = dlp.scan_and_mask(text)
    return api_response(data=result, module='DLP')


@app.post('/api/gaslighting/check')
@jwt_required_middleware
def gaslighting_check():
    from modules import gaslighting
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
    except Exception:
        user_id = 0
    data = request.get_json()
    session_id = data.get('session_id', 'default')
    message = data.get('message', '')
    result = gaslighting.analyze_trajectory(session_id, message, user_id)
    return api_response(data=result, module='GASLIGHTING')


@app.post('/api/shadow/scan-text')
@jwt_required_middleware
def shadow_scan_text():
    data = request.get_json()
    text = data.get('text', '')
    result = shadow_prompt.reveal_shadows(text)
    return api_response(data=result, module='SHADOW')


@app.post('/api/shadow/scan-pdf')
@jwt_required_middleware
def shadow_scan_pdf():
    if 'file' not in request.files:
        return api_response(False, error='No file uploaded', module='SHADOW'), 400
    file = request.files['file']
    file_bytes = file.read()
    result = shadow_prompt.reveal_shadows_pdf(file_bytes)
    return api_response(data=result, module='SHADOW')


@app.post('/api/fingerprint/analyze')
@jwt_required_middleware
def fingerprint_analyze():
    from modules import dna_fingerprint
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
    except Exception:
        user_id = 0
    data = request.get_json()
    session_id = data.get('session_id', 'default')
    prompt = data.get('prompt', '')
    result = dna_fingerprint.fingerprint_prompt(session_id, prompt, user_id)
    return api_response(data=result, module='DNA')


@app.post('/api/mutations/generate')
@jwt_required_middleware
def generate_mutations():
    data = request.get_json()
    prompt = data.get('prompt', '')
    result = mutation_replay.generate_mutations(prompt)
    return api_response(data=result, module='MUTATION')


# ─── Action Queue ────────────────────────────────────────────────────────────
@app.post('/api/actions/submit')
@jwt_required_middleware
def submit_action():
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
    except Exception:
        return api_response(False, error='Auth required', module='ACTION'), 401

    data = request.get_json()
    action_text = data.get('action_text', '')
    user = models.get_user_by_id(user_id)
    user_role = user['role'] if user else 'employee'

    from modules.action_approval import check_action_risk, queue_action
    risk = check_action_risk(action_text, user_role)
    queue_action(action_text, user_id, risk['risk_level'])
    return api_response(data={'queued': True, 'risk_level': risk['risk_level']}, module='ACTION')


@app.get('/api/actions/queue')
@jwt_required_middleware
def get_action_queue():
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
    except Exception:
        return api_response(False, error='Auth required', module='ACTION'), 401
    
    user = models.get_user_by_id(user_id)
    if not user:
        return api_response(False, error='User not found', module='ACTION'), 404
    
    # Admins see all actions except those delegated to HR, HR sees their own + delegated, others see only their own
    if user['role'] == 'admin':
        all_actions = models.get_all_actions()
        actions = [a for a in all_actions if not a.get('delegated_to')]
    elif user['role'] == 'hr':
        # HR sees their own actions + actions delegated to HR
        all_actions = models.get_all_actions()
        actions = [a for a in all_actions if a['requested_by'] == user_id or a.get('delegated_to') == 'hr']
    else:
        actions = [a for a in models.get_all_actions() if a['requested_by'] == user_id]
    
    return api_response(data={'actions': actions}, module='ACTION')


@app.post('/api/actions/approve/<int:action_id>')
@admin_required
def approve_action(action_id):
    try:
        verify_jwt_in_request()
        reviewer_id = int(get_jwt_identity())
    except Exception:
        return api_response(False, error='Auth required', module='ACTION'), 401
    
    # Prevent self-approval
    action = models.get_action_by_id(action_id)
    if not action:
        return api_response(False, error='Action not found', module='ACTION'), 404
    
    if action['requested_by'] == reviewer_id:
        return api_response(False, error='Cannot approve your own request. Requires different admin approval.', module='ACTION'), 403
    
    models.approve_action(action_id, reviewer_id)
    return api_response(data={'approved': True, 'action_id': action_id}, module='ACTION')


@app.post('/api/actions/reject/<int:action_id>')
@admin_required
def reject_action(action_id):
    try:
        verify_jwt_in_request()
        reviewer_id = int(get_jwt_identity())
    except Exception:
        reviewer_id = 0
    models.reject_action(action_id, reviewer_id)
    return api_response(data={'rejected': True, 'action_id': action_id}, module='ACTION')


@app.post('/api/actions/delegate/<int:action_id>')
@admin_required
def delegate_to_hr(action_id):
    try:
        verify_jwt_in_request()
        admin_id = int(get_jwt_identity())
    except Exception:
        return api_response(False, error='Auth required', module='ACTION'), 401
    
    models.delegate_action_to_hr(action_id, admin_id)
    return api_response(data={'delegated': True, 'action_id': action_id}, module='ACTION')


# ─── Dashboard ───────────────────────────────────────────────────────────────

@app.get('/api/replay/events')
@jwt_required_middleware
def replay_events():
    """Returns only blocked events for the Threat Replay page — no limit of 20."""
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
    except Exception:
        return api_response(False, error='Auth required', module='REPLAY'), 401

    user = models.get_user_by_id(user_id)
    user_role = user['role'] if user else 'employee'

    if user_role in ['admin', 'hr']:
        events = models.get_recent_blocked_events(50)
    else:
        # Employees only see their own blocked events
        events = [e for e in models.get_recent_blocked_events(50) if e['user_id'] == user_id]

    return api_response(data={'events': events}, module='REPLAY')


@app.get('/api/dashboard/stats')
@jwt_required_middleware
def dashboard_stats():
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
    except Exception:
        return api_response(False, error='Auth required', module='DASHBOARD'), 401
    
    user = models.get_user_by_id(user_id)
    user_role = user['role'] if user else 'employee'
    
    total_threats = models.get_total_threats()
    blocked_today = models.get_stats_today()
    active_sessions = models.get_active_sessions_count()
    pending_approvals = models.get_pending_count()
    
    # Role-based data access
    if user_role in ['admin', 'hr']:
        recent_events = models.get_recent_prompt_events(20)
        top_threat_users = models.get_top_threat_users(5)
    else:
        recent_events = models.get_recent_prompt_events(20, user_id)
        top_threat_users = []
    
    threats_per_module = models.get_threats_per_module()
    threats_hourly = models.get_threats_per_hour_7days()
    threats_daily = models.get_threats_per_day_10days()
    threats_by_type = models.get_threats_by_type()
    unread_alerts = models.get_unread_alerts()

    # Risk level based on last-hour threat count
    last_hour_threats = sum(
        1 for e in recent_events
        if e.get('blocked') and e.get('timestamp', '') >= (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).strftime('%Y-%m-%d %H:%M:%S')
    )
    if last_hour_threats >= 5:
        risk_level = 'HIGH'
    elif last_hour_threats >= 2:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'

    # Personal risk level for admin/hr
    personal_risk_level = 'LOW'
    if user_role in ['admin', 'hr']:
        user_threats = [e for e in recent_events if e.get('user_id') == user_id and e.get('blocked')]
        user_last_hour = sum(
            1 for e in user_threats
            if e.get('timestamp', '') >= (
                datetime.now(timezone.utc) - timedelta(hours=1)
            ).strftime('%Y-%m-%d %H:%M:%S')
        )
        if user_last_hour >= 5:
            personal_risk_level = 'HIGH'
        elif user_last_hour >= 2:
            personal_risk_level = 'MEDIUM'
        else:
            personal_risk_level = 'LOW'

    return api_response(data={
        'total_threats': total_threats,
        'blocked_today': blocked_today,
        'active_sessions': active_sessions,
        'pending_approvals': pending_approvals,
        'risk_level': risk_level,
        'personal_risk_level': personal_risk_level,
        'recent_events': recent_events,
        'threats_per_module': threats_per_module,
        'threats_hourly': threats_hourly,
        'threats_daily': threats_daily,
        'threats_by_type': threats_by_type,
        'unread_alerts': unread_alerts,
        'unread_alerts_count': len(unread_alerts),
        'top_threat_users': top_threat_users,
        'user_role': user_role
    }, module='DASHBOARD')


@app.get('/api/alerts/unread')
@jwt_required_middleware
def get_alerts():
    alerts = models.get_unread_alerts()
    return api_response(data={'alerts': alerts, 'count': len(alerts)}, module='ALERTS')


@app.post('/api/admin/clear-data')
@admin_required
def clear_all_data():
    try:
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
    except Exception:
        return api_response(False, error='Auth required', module='ADMIN'), 401
    
    user = models.get_user_by_id(user_id)
    if not user or user['role'] != 'admin':
        return api_response(False, error='Admin access required', module='ADMIN'), 403
    
    import sqlite3
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('DELETE FROM prompt_events')
    c.execute('DELETE FROM session_messages')
    c.execute('DELETE FROM action_queue')
    c.execute('DELETE FROM blocklist_entries')
    c.execute('DELETE FROM admin_alerts')
    
    conn.commit()
    conn.close()
    
    return api_response(data={'cleared': True}, module='ADMIN')


if __name__ == '__main__':
    print('[FIREWALL] Starting Shell Enterprise AI Firewall...')
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)