import re
import base64
import unicodedata
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ZERO_WIDTH_CHARS = re.compile(r'[\u200b\u200c\u200d\ufeff\u2060\u00ad]')
DIRECTIONAL_OVERRIDES = re.compile(r'[\u202a-\u202e\u2066-\u2069]')
HTML_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)
BASE64_PATTERN = re.compile(r'[A-Za-z0-9+/]{40,}={0,2}')

INJECTION_KEYWORDS = [
    'ignore', 'bypass', 'override', 'forget', 'pretend', 'jailbreak',
    'instructions', 'system', 'disregard', 'DAN', 'roleplay', 'act as'
]

# 60+ homoglyph pairs: Cyrillic/Greek -> Latin
HOMOGLYPH_MAP = {
    '\u0430': 'a', '\u0435': 'e', '\u043e': 'o', '\u0440': 'r', '\u0441': 'c',
    '\u0445': 'x', '\u0440': 'p', '\u0456': 'i', '\u0454': 'e', '\u0458': 'j',
    '\u0443': 'y', '\u0432': 'b', '\u0491': 'g', '\u0455': 's', '\u04cf': 'l',
    '\u0391': 'A', '\u0392': 'B', '\u0395': 'E', '\u0396': 'Z', '\u0397': 'H',
    '\u0399': 'I', '\u039a': 'K', '\u039c': 'M', '\u039d': 'N', '\u039f': 'O',
    '\u03a1': 'R', '\u03a4': 'T', '\u03a5': 'Y', '\u03a7': 'X',
    '\u03b1': 'a', '\u03b2': 'b', '\u03b5': 'e', '\u03b9': 'i', '\u03bf': 'o',
    '\u03c1': 'p', '\u03c5': 'u', '\u03bd': 'v',
    '\u0d30': 'n', '\u0d2f': 'y', '\u0966': '0', '\u0967': '1',
    '\u2160': 'I', '\u2161': 'II', '\u2162': 'III',
    '\uff41': 'a', '\uff42': 'b', '\uff43': 'c', '\uff44': 'd', '\uff45': 'e',
    '\uff46': 'f', '\uff47': 'g', '\uff48': 'h', '\uff49': 'i', '\uff4a': 'j',
    '\uff4b': 'k', '\uff4c': 'l', '\uff4d': 'm', '\uff4e': 'n', '\uff4f': 'o',
    '\uff50': 'p', '\uff51': 'q', '\uff52': 'r', '\uff53': 's', '\uff54': 't',
    '\uff55': 'u', '\uff56': 'v', '\uff57': 'w', '\uff58': 'x', '\uff59': 'y',
    '\uff5a': 'z',
}


def reveal_shadows(text: str) -> dict:
    print(f'[FIREWALL][SHADOW] Scanning text for hidden content...')

    shadows_found = []
    clean_text = text

    # 1. Zero-width characters
    zw_matches = list(ZERO_WIDTH_CHARS.finditer(text))
    for match in zw_matches:
        shadows_found.append({
            'type': 'zero_width',
            'description': f'Hidden zero-width char (U+{ord(match.group()):04X}) at position {match.start()}',
            'position': match.start(),
            'content': repr(match.group())
        })
    clean_text = ZERO_WIDTH_CHARS.sub('', clean_text)

    # 2. Homoglyphs
    normalized = ''
    homoglyph_changes = []
    for i, ch in enumerate(text):
        if ch in HOMOGLYPH_MAP:
            replacement = HOMOGLYPH_MAP[ch]
            homoglyph_changes.append({
                'original': ch,
                'replacement': replacement,
                'position': i,
                'unicode': f'U+{ord(ch):04X}'
            })
            normalized += replacement
        else:
            normalized += ch
    if homoglyph_changes:
        shadows_found.append({
            'type': 'homoglyph',
            'description': f'{len(homoglyph_changes)} homoglyph character(s) substituted',
            'content': str(homoglyph_changes[:5]),
            'position': homoglyph_changes[0]['position']
        })
        clean_text = normalized

    # 3. HTML comments
    html_comments = HTML_COMMENT.findall(clean_text)
    for comment in html_comments:
        shadows_found.append({
            'type': 'html_comment',
            'description': 'HTML comment found in text',
            'content': comment[:200],
            'position': clean_text.find(comment)
        })
    clean_text = HTML_COMMENT.sub('', clean_text)

    # 4. Unicode directional overrides
    dir_matches = list(DIRECTIONAL_OVERRIDES.finditer(clean_text))
    for match in dir_matches:
        shadows_found.append({
            'type': 'directional_override',
            'description': f'Unicode directional override (U+{ord(match.group()):04X}) at position {match.start()}',
            'position': match.start(),
            'content': repr(match.group())
        })
    clean_text = DIRECTIONAL_OVERRIDES.sub('', clean_text)

    # 5. Base64 embedded content
    b64_matches = BASE64_PATTERN.findall(clean_text)
    for b64str in b64_matches:
        try:
            padding = 4 - len(b64str) % 4
            padded = b64str + ('=' * (padding % 4))
            decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
            decoded_lower = decoded.lower()
            if any(kw in decoded_lower for kw in INJECTION_KEYWORDS):
                shadows_found.append({
                    'type': 'base64_injection',
                    'description': 'Base64 encoded injection found',
                    'content': decoded[:200],
                    'position': clean_text.find(b64str)
                })
        except Exception:
            pass

    print(f'[FIREWALL][SHADOW] Found {len(shadows_found)} shadow elements.')
    return {
        'clean_text': clean_text,
        'shadows_found': shadows_found,
        'original_length': len(text),
        'clean_length': len(clean_text)
    }


def reveal_shadows_pdf(file_bytes: bytes) -> dict:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype='pdf')
        all_text = ''
        page_count = doc.page_count
        for page in doc:
            all_text += page.get_text()
        doc.close()
        result = reveal_shadows(all_text)
        result['pages_scanned'] = page_count
        result['extracted_text'] = all_text  # Add raw extracted text
        return result
    except Exception as e:
        return {
            'clean_text': '',
            'shadows_found': [],
            'extracted_text': '',
            'error': str(e)
        }
