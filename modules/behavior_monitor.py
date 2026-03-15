import re
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import call_llm

# ── OWNERSHIP: Technical secrets accidentally exposed in AI RESPONSES only ────
# Does NOT own: PII (DLP owns that), user message scanning (other modules)
# Fires on: DB connection strings, private keys, internal IPs, AWS creds,
#           stack traces with file paths, SQL schemas being leaked

SENSITIVE_PATTERNS = {
    'internal_ip': re.compile(
        r'\b(192\.168\.|10\.\d+\.|172\.(1[6-9]|2[0-9]|3[01])\.)[\d.]+\b'
    ),
    'db_connection': re.compile(
        r'(mongodb|mysql|postgresql|sqlite|redis|mssql)://[^\s"\'<>]+'
    ),
    'private_key': re.compile(
        r'-----BEGIN\s+(RSA\s+|EC\s+|OPENSSH\s+|DSA\s+)?PRIVATE KEY-----'
    ),
    'aws_credential': re.compile(
        r'AKIA[0-9A-Z]{16}'
    ),
    'stack_trace': re.compile(
        r'(File "[^"]+\.py", line \d+|Traceback \(most recent call last\))'
    ),
    'sql_schema_leak': re.compile(
        r'\b(CREATE TABLE|DROP TABLE|ALTER TABLE)\s+\w+', re.IGNORECASE
    ),
    'env_variable_leak': re.compile(
        r'(os\.environ\[|process\.env\.|getenv\()["\']?\w+["\']?\)?', re.IGNORECASE
    ),
    'secret_key_pattern': re.compile(
        r'(?:secret|private|api)[_\-]?key\s*[:=]\s*["\']?[A-Za-z0-9+/=_\-]{16,}', re.IGNORECASE
    ),
}


def monitor_response(response_text: str) -> dict:
    print(f'[FIREWALL][BEHAVIOR] Monitoring AI response ({len(response_text)} chars)...')

    issues = []

    for name, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(response_text):
            issues.append({
                'type': name,
                'severity': 'critical',
                'description': f'Technical secret detected in response: {name.replace("_", " ")}'
            })
            print(f'[FIREWALL][BEHAVIOR] Found: {name}')

    # LLM double-check only when regex already found something
    if issues:
        system = (
            'You are a security reviewer checking if an AI response accidentally leaked '
            'technical secrets. Check ONLY for: database connection strings, private/secret keys, '
            'internal IP addresses, AWS credentials, file system paths in stack traces, '
            'or raw SQL schema definitions. '
            'Do NOT flag: general explanations, public information, or educational content. '
            'Respond JSON ONLY: '
            '{"contains_sensitive": true/false, "confirmed_issues": ["list"], "confidence": 0.0-1.0}'
        )
        llm_response = call_llm(system, response_text[:2000], max_tokens=200)

        if llm_response:
            try:
                clean = re.sub(r'```json?|```', '', llm_response).strip()
                json_match = re.search(r'\{.*?\}', clean, re.DOTALL)
                if json_match:
                    res = json.loads(json_match.group())
                    if res.get('contains_sensitive') and res.get('confidence', 0) > 0.6:
                        for issue in res.get('confirmed_issues', []):
                            if not any(i['description'] == issue for i in issues):
                                issues.append({'type': 'llm_detected', 'severity': 'critical', 'description': issue})
            except (json.JSONDecodeError, ValueError):
                pass

    safe = len(issues) == 0
    print(f'[FIREWALL][BEHAVIOR] Safe={safe}, Issues={len(issues)}')
    return {'safe': safe, 'issues': issues}