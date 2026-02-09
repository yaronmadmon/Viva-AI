from src.config import get_settings
s = get_settings()
k = s.openai_api_key
print(f"Key length: {len(k)}")
print(f"Starts with sk-: {k.startswith('sk-')}")
print(f"Is placeholder: {k.startswith('sk-your-')}")
print(f"First 8 chars: {k[:8]}...")
