from bytez import Bytez
from config import BYTEZ_API_KEY, BYTEZ_MODEL
import re
import time
import threading

sdk = Bytez(BYTEZ_API_KEY)
model = sdk.model(BYTEZ_MODEL)

_llm_lock = threading.Lock()
_last_request_time = 0

def call_llm(system_prompt, user_message, max_tokens=400):
    global _last_request_time
    
    with _llm_lock:
        elapsed = time.time() - _last_request_time
        if elapsed < 1.2:
            time.sleep(1.2 - elapsed)
        
        try:
            input_messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ]
            
            params = {
                'temperature': 0.1
            }
            
            result = model.run(input_messages, params)
            _last_request_time = time.time()
            
            if result.error:
                print(f'[FIREWALL][LLM] Error calling LLM: {result.error}')
                return None
            
            # Extract content from response
            if isinstance(result.output, dict) and 'content' in result.output:
                content = result.output['content']
            else:
                content = str(result.output)
            
            # Remove <think> tags if present
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            return content
            
        except Exception as e:
            _last_request_time = time.time()
            print(f'[FIREWALL][LLM] Error calling LLM: {e}')
            return None