from huggingface_hub import InferenceClient
from config import HF_TOKEN, HF_MODEL

print(f"Testing Hugging Face API...")
print(f"Model: {HF_MODEL}")
print(f"Token: {HF_TOKEN[:20]}...")

try:
    client = InferenceClient(api_key=HF_TOKEN)
    
    print("\nSending test request...")
    completion = client.chat.completions.create(
        model=HF_MODEL,
        messages=[
            {"role": "user", "content": "Say 'Hello, API is working!' if you can read this."}
        ],
        max_tokens=50
    )
    
    print("\n✅ SUCCESS! API is working!")
    print(f"Response: {completion.choices[0].message.content}")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
