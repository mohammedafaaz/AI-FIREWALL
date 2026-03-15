import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import models

HIGH_RISK_KEYWORDS = [
    'transfer', 'payment', 'approve', 'delete database', 'drop table',
    'send email to all', 'export all', 'modify salary', 'terminate',
    'wire funds', 'wire transfer', 'mass delete', 'purge', 'bulk send',
    'broadcast email', 'remove all', 'salary update'
]

AMOUNT_PATTERN = re.compile(r'\b(\d[\d,]*(?:\.\d+)?)\b')

HIGH_RISK_ROLES = ['employee']


def check_action_risk(action_text: str, user_role: str) -> dict:
    print(f'[FIREWALL][ACTION] Checking action risk: {action_text[:80]}...')

    risk_factors = []
    risk_level = 'LOW'

    # Keyword check
    action_lower = action_text.lower()
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in action_lower:
            risk_factors.append(f'High-risk keyword: "{keyword}"')

    # Amount threshold
    amounts = AMOUNT_PATTERN.findall(action_text.replace(',', ''))
    for amt_str in amounts:
        try:
            amt = float(amt_str)
            if amt > 10000:
                risk_factors.append(f'High amount detected: {amt}')
        except ValueError:
            pass

    # Role-based check
    if user_role in HIGH_RISK_ROLES and any(
        kw in action_lower for kw in ['payment', 'transfer', 'approve', 'salary', 'wire']
    ):
        risk_factors.append(f'Unauthorized role "{user_role}" attempting financial action')

    requires_approval = len(risk_factors) > 0

    if len(risk_factors) >= 3:
        risk_level = 'HIGH'
    elif len(risk_factors) >= 1:
        risk_level = 'MEDIUM'

    result = {
        'requires_approval': requires_approval,
        'risk_level': risk_level,
        'risk_factors': risk_factors
    }
    print(f'[FIREWALL][ACTION] Risk={risk_level}, ApprovalRequired={requires_approval}')
    return result


def queue_action(action_text: str, user_id: int, risk_level: str = 'HIGH'):
    models.add_action_to_queue(action_text, user_id, risk_level)
    print(f'[FIREWALL][ACTION] Action queued for approval by user {user_id}')
