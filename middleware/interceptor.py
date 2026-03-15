import threading
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import call_llm
from database import models
from modules import prompt_injection, behavior_monitor, dlp, action_approval
from modules import shadow_prompt, mutation_replay, token_smuggling

# ── PIPELINE ──────────────────────────────────────────────────────────────────
# STEP 1: Shadow Reveal       — hidden chars, homoglyphs, Base64, HTML comments
# STEP 2: Token Smuggling     — leet, punct-split, token-split, unicode spaces
# STEP 3: Prompt Injection    — AI system manipulation
# STEP 4: DLP (input)         — PII masking on user message
# STEP 5: AI Call             — sanitized prompt sent to LLM
# STEP 6: Behavior Monitor    — technical secrets in AI response
# STEP 7: DLP (output)        — PII masking on AI response
# STEP 8: Action Approval     — high-risk actions in AI response
#
# mutation_replay fires for EVERY block — not just injection.


def log_event(session_id, user_id, prompt_text, blocked, reason, module, score=0.5):
    models.log_prompt_event(session_id, user_id, prompt_text[:500], blocked, reason, score, module)


def _trigger_replay(prompt_text: str):
    """Fire mutation replay in background for ANY blocked prompt from ANY module."""
    threading.Thread(
        target=mutation_replay.generate_mutations,
        args=(prompt_text,),
        daemon=True
    ).start()


def _block(result: dict, prompt_text: str, session_id: str, user_id: int,
           module: str, reason: str, score: float) -> dict:
    """Unified block handler: log event + trigger replay + return blocked result."""
    log_event(session_id, user_id, prompt_text, True, reason, module, score)
    _trigger_replay(prompt_text)
    return {**result, 'blocked': True, 'reason': reason, 'module': module, 'score': score}


def process_prompt(session_id: str, user_id: int, prompt_text: str, user_role: str) -> dict:
    result = {
        'blocked': False,
        'response': None,
        'warnings': [],
        'shadows': [],
        'module': None,
        'reason': None
    }

    # ── STEP 1: Shadow Prompt Reveal ─────────────────────────────────────────
    # Strips zero-width chars, homoglyphs, Base64 injections, HTML comments,
    # Unicode directional overrides. Sanitises but does NOT block on its own —
    # the cleaned text flows to downstream modules.
    try:
        shadow = shadow_prompt.reveal_shadows(prompt_text)
        if shadow.get('shadows_found'):
            prompt_text = shadow['clean_text']
            result['shadows'] = shadow['shadows_found']
            log_event(session_id, user_id, prompt_text, False,
                      f'Shadow elements removed: {len(shadow["shadows_found"])}', 'SHADOW', 0.5)
    except Exception as e:
        print(f'[FIREWALL][INTERCEPTOR] Shadow error: {e}')

    # ── STEP 2: Token Smuggling Detection ────────────────────────────────────
    # Detects obfuscated injections: leet (1gnor3), punct-split (by-pass),
    # token-split (ign ore), unicode whitespace, reversed keywords.
    # BLOCKS if obfuscation directly reveals injection keywords.
    # Otherwise normalises text and passes clean version downstream.
    try:
        smuggling = token_smuggling.scan_for_smuggling(prompt_text)
        if smuggling['blocked']:
            techniques = ', '.join(set(f['type'] for f in smuggling['findings']))
            return _block(result, prompt_text, session_id, user_id,
                          'TOKEN_SMUGGLING',
                          f'Obfuscated injection detected — techniques: {techniques}',
                          smuggling['score'])
        if smuggling.get('findings'):
            prompt_text = smuggling['clean_text']
            result['warnings'].append({
                'type': 'token_smuggling_normalized',
                'description': f'Input normalized — {len(smuggling["findings"])} obfuscation technique(s) removed'
            })
    except Exception as e:
        print(f'[FIREWALL][INTERCEPTOR] Token smuggling error: {e}')

    # ── STEP 3: Prompt Injection ──────────────────────────────────────────────
    # Scans clean text for AI system manipulation: jailbreaks, persona overrides,
    # instruction replacement, authority impersonation.
    try:
        injection = prompt_injection.scan_prompt(prompt_text)
        if injection['blocked']:
            return _block(result, prompt_text, session_id, user_id,
                          'INJECTION', injection['reason'], injection['score'])
    except Exception as e:
        print(f'[FIREWALL][INTERCEPTOR] Injection error: {e}')

    # ── STEP 4: DLP on User Input ─────────────────────────────────────────────
    original_prompt = prompt_text
    try:
        input_dlp = dlp.scan_and_mask(prompt_text)
        if input_dlp.get('findings'):
            prompt_text = input_dlp['masked_text']
            result['dlp_input'] = {
                'original': original_prompt,
                'masked': prompt_text,
                'findings': input_dlp['findings']
            }
            result['warnings'].append({
                'type': 'dlp_input',
                'description': f'PII masked: {", ".join(set(f["type"] for f in input_dlp["findings"]))}'
            })
            models.log_dlp_event(session_id, user_id, original_prompt, prompt_text, input_dlp['findings'], 'input')
    except Exception as e:
        print(f'[FIREWALL][INTERCEPTOR] DLP input error: {e}')

    # ── STEP 5: Call AI ───────────────────────────────────────────────────────
    ai_response = call_llm('You are a helpful enterprise AI assistant.', prompt_text, max_tokens=600)
    if not ai_response:
        return {**result, 'blocked': False,
                'response': 'AI service unavailable. Please check your API key and try again.'}

    # ── STEP 6: Behavior Monitoring ───────────────────────────────────────────
    # Scans AI response for accidentally leaked technical secrets:
    # credentials, private IPs, stack traces, internal API keys.
    # Blocks the response if critical secrets are detected.
    try:
        behavior = behavior_monitor.monitor_response(ai_response)
        if not behavior['safe']:
            critical = [i for i in behavior.get('issues', [])
                        if (i.get('severity') if isinstance(i, dict) else '') == 'critical']
            if critical:
                desc = critical[0].get('description', 'Critical secret in response') if isinstance(critical[0], dict) else str(critical[0])
                return _block(result, prompt_text, session_id, user_id,
                              'BEHAVIOR', f'AI response contained critical secret: {desc[:80]}', 0.95)
            # Non-critical issues — warn, don't block
            for issue in behavior['issues']:
                result['warnings'].append({
                    'type': 'behavior_issue',
                    'description': issue.get('description', str(issue)) if isinstance(issue, dict) else str(issue)
                })
            log_event(session_id, user_id, 'RESPONSE_SCAN', False,
                      'Non-critical behavior issues in AI response', 'BEHAVIOR', 0.6)
    except Exception as e:
        print(f'[FIREWALL][INTERCEPTOR] Behavior error: {e}')

    # ── STEP 7: DLP on AI Response ────────────────────────────────────────────
    safe_response = ai_response
    try:
        output_dlp = dlp.scan_and_mask(ai_response)
        safe_response = output_dlp['masked_text']
        if output_dlp.get('findings'):
            result['dlp_output'] = {
                'original': ai_response,
                'masked': safe_response,
                'findings': output_dlp['findings']
            }
            models.log_dlp_event(session_id, user_id, ai_response, safe_response, output_dlp['findings'], 'output')
    except Exception as e:
        print(f'[FIREWALL][INTERCEPTOR] DLP output error: {e}')

    # ── STEP 8: Action Approval ───────────────────────────────────────────────
    # Detects high-risk actions in AI response (DROP TABLE, wire transfers, etc.)
    # Blocks delivery and queues for admin review if risk level is critical.
    try:
        action = action_approval.check_action_risk(safe_response, user_role)
        if action.get('requires_approval'):
            if action.get('risk_level') in ('HIGH', 'critical'):
                action_approval.queue_action(safe_response, user_id, action['risk_level'])
                return _block(result, prompt_text, session_id, user_id,
                              'ACTION',
                              f'High-risk action blocked and queued for admin review: {action["risk_level"]}',
                              0.90)
            # Non-critical — queue and annotate but allow
            action_approval.queue_action(safe_response, user_id, action['risk_level'])
            safe_response += '\n\n⚠️ [NOTE: This action requires admin approval before execution]'
            log_event(session_id, user_id, 'ACTION_FLAGGED', False,
                      f'Action queued for review: {action["risk_level"]}', 'ACTION', 0.6)
    except Exception as e:
        print(f'[FIREWALL][INTERCEPTOR] Action error: {e}')

    # ── Save AI response ──────────────────────────────────────────────────────
    try:
        models.save_session_message(session_id, user_id, safe_response, 'assistant', 0.0)
    except Exception as e:
        print(f'[FIREWALL][INTERCEPTOR] Session save error: {e}')

    result['response'] = safe_response
    return result