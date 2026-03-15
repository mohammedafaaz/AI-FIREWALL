import re
import unicodedata
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── OWNERSHIP: Obfuscated injection attempts that bypass keyword/regex filters ─
# Shadow module catches: zero-width chars, homoglyphs, Base64, HTML comments
# Token Smuggling catches: everything else attackers do to disguise text
#   - Punctuation insertion  (j.a.i.l.b.r.e.a.k, by-pass, jail_break)
#   - Leetspeak              (1gnor3, byp@ss, j41lbr34k)
#   - Token splitting        (ign ore instruct ions)
#   - Unicode whitespace     (non-breaking spaces, em-spaces, thin spaces)
#   - Mixed case obfuscation (IgNoRe, IGNORE → normalised before injection scan)
#   - Word reversal          (erongi = ignore)
# 
# This module runs BEFORE injection scanning and produces a normalised clean
# text that injection then scans. Obfuscation is reported as a finding.

# ── Leet / symbol substitution map ───────────────────────────────────────────
LEET_MAP = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
    '6': 'g', '7': 't', '8': 'b', '9': 'q',
    '@': 'a', '$': 's', '!': 'i', '+': 't', '|': 'i',
}

# ── Unicode whitespace variants that should collapse to regular space ─────────
# Non-breaking, em, en, thin, hair, ideographic spaces etc.
UNICODE_SPACES = re.compile(
    r'[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000\ufeff]'
)

# ── Punctuation inserted between letters to split tokens ─────────────────────
# Matches: j.a.i.l, by-pass, jail_break, by/pass, j*a*i*l
PUNCT_SPLIT = re.compile(r'(?<=[a-zA-Z0-9])[.\-_/\\*~^](?=[a-zA-Z0-9])')

# ── Reversed injection keywords (attacker reverses words) ────────────────────
REVERSED_KEYWORDS = {
    'erongi': 'ignore',
    'ssapyb': 'bypass',
    'kaerbliaj': 'jailbreak',
    'edrevo': 'override',
    'tegorf': 'forget',
    'dneretsid': 'disregard',
    'dneterp': 'pretend',
    'tca': 'act',
    'laever': 'reveal',
    'metsys': 'system',
    'noitcurtsni': 'instruction',
    'snoitcurtsni': 'instructions',
    'seluр': 'rules',
    'senilediug': 'guidelines',
}

# ── Word-split detection: short fragments that reconstruct injection keywords ──
# e.g. "ign ore" → "ignore", "instruct ions" → "instructions"
INJECTION_KEYWORDS_FULL = [
    'ignore', 'bypass', 'jailbreak', 'override', 'forget', 'disregard',
    'pretend', 'instructions', 'guidelines', 'restrictions', 'limitations',
    'disable', 'reveal', 'system', 'prompt', 'developer', 'unrestricted',
]


def _nfkc_normalize(text: str) -> str:
    """Unicode NFKC normalization - collapses fullwidth, compatibility chars."""
    return unicodedata.normalize('NFKC', text)


def _collapse_unicode_spaces(text: str) -> str:
    """Replace all unicode whitespace variants with regular space."""
    return UNICODE_SPACES.sub(' ', text)


def _remove_punct_splits(text: str) -> str:
    """Remove punctuation inserted between letters: j.a.i.l → jail, by-pass → bypass."""
    return PUNCT_SPLIT.sub('', text)


def _deleet(text: str) -> str:
    """Convert leet/symbol substitutions back to letters: 1gnor3 → ignore."""
    result = []
    for ch in text.lower():
        result.append(LEET_MAP.get(ch, ch))
    return ''.join(result)


def _unreverse_words(text: str) -> str:
    """Detect and replace reversed injection keywords."""
    words = text.lower().split()
    replaced = []
    found = []
    for word in words:
        clean_word = re.sub(r'[^a-z]', '', word)
        if clean_word in REVERSED_KEYWORDS:
            found.append(f'{word} → {REVERSED_KEYWORDS[clean_word]}')
            replaced.append(REVERSED_KEYWORDS[clean_word])
        else:
            replaced.append(word)
    return ' '.join(replaced), found


def _detect_token_splits(text: str) -> list:
    """
    Detect keywords split across multiple short tokens with spaces.
    e.g. 'ign ore' → 'ignore', 'instruct ions' → 'instructions'
    """
    findings = []
    words = text.lower().split()

    for keyword in INJECTION_KEYWORDS_FULL:
        # Check if keyword appears when adjacent short words are merged
        for i in range(len(words) - 1):
            merged = re.sub(r'[^a-z]', '', words[i]) + re.sub(r'[^a-z]', '', words[i + 1])
            if merged == keyword:
                findings.append({
                    'type': 'token_split',
                    'description': f'Keyword "{keyword}" split across tokens: "{words[i]} {words[i+1]}"',
                    'original': f'{words[i]} {words[i+1]}',
                    'reconstructed': keyword
                })
        # Three-way split
        for i in range(len(words) - 2):
            merged3 = (re.sub(r'[^a-z]', '', words[i]) +
                       re.sub(r'[^a-z]', '', words[i + 1]) +
                       re.sub(r'[^a-z]', '', words[i + 2]))
            if merged3 == keyword:
                findings.append({
                    'type': 'token_split_3way',
                    'description': f'Keyword "{keyword}" split across 3 tokens: "{words[i]} {words[i+1]} {words[i+2]}"',
                    'original': f'{words[i]} {words[i+1]} {words[i+2]}',
                    'reconstructed': keyword
                })

    return findings


def scan_for_smuggling(text: str) -> dict:
    """
    Normalize text and detect all token smuggling techniques.
    Returns clean normalized text + list of findings.
    The clean text should be passed to injection scanning.
    """
    print(f'[FIREWALL][TOKEN_SMUGGLING] Scanning: {text[:80]}...')

    findings = []
    clean = text

    # ── Pass 1: NFKC Unicode normalization ───────────────────────────────
    nfkc = _nfkc_normalize(clean)
    if nfkc != clean:
        changed = sum(1 for a, b in zip(clean, nfkc) if a != b)
        if changed > 0:
            findings.append({
                'type': 'unicode_normalization',
                'description': f'Unicode compatibility chars normalized ({changed} chars changed to ASCII equivalents)',
            })
        clean = nfkc

    # ── Pass 2: Unicode whitespace collapse ──────────────────────────────
    no_weird_spaces = _collapse_unicode_spaces(clean)
    if no_weird_spaces != clean:
        findings.append({
            'type': 'unicode_whitespace',
            'description': 'Non-standard Unicode whitespace detected (non-breaking/em/en spaces)',
        })
        clean = no_weird_spaces

    # ── Pass 3: Punctuation-split removal ────────────────────────────────
    depunct = _remove_punct_splits(clean)
    if depunct != clean:
        # Only flag if de-puncting REVEALS a NEW keyword (not one already present as a full word)
        # e.g. "by-pass" → "bypass" is flagged, but "step-by-step instructions" is NOT
        original_kws = set(kw for kw in INJECTION_KEYWORDS_FULL
                           if re.search(r'\b' + kw + r'\b', clean, re.IGNORECASE))
        depunct_kws  = set(kw for kw in INJECTION_KEYWORDS_FULL
                           if re.search(r'\b' + kw + r'\b', depunct, re.IGNORECASE))
        new_kws = depunct_kws - original_kws
        if new_kws:
            findings.append({
                'type': 'punctuation_split',
                'description': f'Punctuation used to split keywords: {", ".join(sorted(new_kws)[:3])}',
                'original_sample': clean[:100],
                'normalized': depunct[:100],
            })
        clean = depunct  # always normalize, only flag when new keywords revealed

    # ── Pass 4: Leet/symbol substitution ─────────────────────────────────
    deleeted = _deleet(clean)
    deleeted_keywords = [kw for kw in INJECTION_KEYWORDS_FULL if kw in deleeted]
    original_keywords = [kw for kw in INJECTION_KEYWORDS_FULL if kw in clean.lower()]
    new_keywords = [kw for kw in deleeted_keywords if kw not in original_keywords]
    if new_keywords:
        findings.append({
            'type': 'leet_substitution',
            'description': f'Leet/symbol substitution reveals keywords: {", ".join(new_keywords[:3])}',
            'original_sample': clean[:100],
            'normalized': deleeted[:100],
        })
        # Use deleeted version for further scanning
        # Keep original case structure but replace leet chars
        clean_lower = clean.lower()
        leet_fixed = ''.join(LEET_MAP.get(c, c) for c in clean_lower)
        clean = leet_fixed

    # ── Pass 5: Reversed keywords ─────────────────────────────────────────
    unreversed, reversed_found = _unreverse_words(clean)
    if reversed_found:
        findings.append({
            'type': 'reversed_keywords',
            'description': f'Reversed injection keywords detected: {"; ".join(reversed_found[:3])}',
        })
        clean = unreversed

    # ── Pass 6: Token split detection ────────────────────────────────────
    split_findings = _detect_token_splits(text)  # check original too
    if split_findings:
        findings.extend(split_findings)
        # Reconstruct the clean version by merging split tokens
        clean_words = clean.split()
        for keyword in INJECTION_KEYWORDS_FULL:
            for i in range(len(clean_words) - 1):
                merged = re.sub(r'[^a-zA-Z]', '', clean_words[i]).lower() + \
                         re.sub(r'[^a-zA-Z]', '', clean_words[i+1]).lower()
                if merged == keyword:
                    clean_words[i] = keyword
                    clean_words[i+1] = ''
        clean = ' '.join(w for w in clean_words if w)

    # ── Final: collapse multiple spaces ──────────────────────────────────
    clean = re.sub(r'\s+', ' ', clean).strip()

    blocked = len(findings) > 0
    score = min(len(findings) * 0.3, 1.0)

    # Upgrade score if findings reveal actual injection keywords
    high_value_keywords = ['jailbreak', 'bypass', 'ignore', 'override', 'instructions']
    if any(kw in clean.lower() for kw in high_value_keywords) and findings:
        score = max(score, 0.85)

    print(f'[FIREWALL][TOKEN_SMUGGLING] Findings: {len(findings)}, Score: {score:.2f}, Blocked: {blocked}')
    if findings:
        for f in findings:
            print(f'  -> [{f["type"]}] {f["description"]}')

    return {
        'clean_text': clean,
        'original_text': text,
        'findings': findings,
        'blocked': blocked,
        'score': score,
        'technique_count': len(findings),
    }