import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── OWNERSHIP: ALL PII detection and masking — user messages AND AI responses ─
# Does NOT own: system manipulation (Injection), credentials in code (Behavior Monitor)
# Fires on: SSN, credit cards, phone numbers, emails, passwords, API keys, bank accounts

try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    SPACY_AVAILABLE = True
except Exception:
    SPACY_AVAILABLE = False
    print('[FIREWALL][DLP] spaCy not available, NER disabled.')

DLP_PATTERNS = [
    {
        'name': 'credit_card',
        'pattern': re.compile(r'\b[3-4][0-9]{3}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}\b'),
        'replacement': '[REDACTED-CREDIT-CARD]'
    },
    {
        'name': 'ssn',
        'pattern': re.compile(r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b'),
        'replacement': '[REDACTED-SSN]'
    },
    {
        'name': 'api_key',
        # Matches long alphanumeric strings followed by key/token/secret context
        'pattern': re.compile(r'\b(?:sk|pk|rk|ak)-[A-Za-z0-9\-_]{20,}\b|\b[A-Za-z0-9]{32,}(?=\s*(?:is\s+my\s+|:\s*|=\s*)(?:api|key|token|secret))', re.IGNORECASE),
        'replacement': '[REDACTED-API-KEY]'
    },
    {
        'name': 'password',
        'pattern': re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*\S+', re.IGNORECASE),
        'replacement': '[REDACTED-PASSWORD]'
    },
    {
        'name': 'bank_account',
        'pattern': re.compile(r'\b[0-9]{8,18}\b(?=.*(?:account|IFSC|routing|IBAN))', re.IGNORECASE),
        'replacement': '[REDACTED-BANK-ACCOUNT]'
    },
    {
        'name': 'indian_phone',
        'pattern': re.compile(r'\b[6-9][0-9]{9}\b'),
        'replacement': '[REDACTED-PHONE]'
    },
    {
        'name': 'us_phone',
        'pattern': re.compile(r'\b\d{3}[.\-]\d{3}[.\-]\d{4}\b'),
        'replacement': '[REDACTED-PHONE]'
    },
    {
        'name': 'email',
        'pattern': re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'),
        'replacement': '[REDACTED-EMAIL]'
    },
]


def scan_and_mask(text: str) -> dict:
    print(f'[FIREWALL][DLP] Scanning text for PII ({len(text)} chars)...')

    masked_text = text
    findings = []

    # Apply all regex patterns
    for rule in DLP_PATTERNS:
        matches = list(rule['pattern'].finditer(masked_text))
        if matches:
            for match in matches:
                val = match.group()
                findings.append({
                    'type': rule['name'],
                    'value': val[:20] + '...' if len(val) > 20 else val,
                    'position': match.start()
                })
            masked_text = rule['pattern'].sub(rule['replacement'], masked_text)

    # Bulk email warning
    email_count = len(re.findall(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b', text))
    if email_count > 3:
        findings.append({'type': 'bulk_email', 'value': f'{email_count} emails found', 'position': 0})

    # spaCy NER — only for HR/payroll context to avoid false positives
    if SPACY_AVAILABLE:
        try:
            hr_keywords = ['salary', 'payroll', 'compensation', 'wage', 'payment', 'employee']
            if any(kw in text.lower() for kw in hr_keywords):
                doc = nlp(text[:5000])
                for ent in doc.ents:
                    if ent.label_ in ['PERSON', 'ORG', 'MONEY']:
                        findings.append({
                            'type': f'ner_{ent.label_.lower()}',
                            'value': ent.text[:30],
                            'position': ent.start_char
                        })
        except Exception as e:
            print(f'[FIREWALL][DLP] spaCy error: {e}')

    print(f'[FIREWALL][DLP] Found {len(findings)} PII findings.')
    return {'masked_text': masked_text, 'findings': findings}