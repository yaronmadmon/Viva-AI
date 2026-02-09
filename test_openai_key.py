"""Quick script to verify OpenAI API key is loaded and valid."""
import os
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load .env before importing config
from dotenv import load_dotenv
load_dotenv()

def main():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        print("FAIL: OPENAI_API_KEY is not set in .env")
        sys.exit(1)
    if key.startswith("sk-your-") or key == "sk-your-openai-api-key":
        print("FAIL: OPENAI_API_KEY still has placeholder value. Replace with your real key.")
        sys.exit(1)
    print("OPENAI_API_KEY is set (length:", len(key), "chars)")

    try:
        import openai
    except ImportError:
        print("Installing openai package...")
        os.system(f'"{sys.executable}" -m pip install openai -q')
        import openai

    client = openai.OpenAI(api_key=key)
    # Minimal call: list models (cheap, no usage)
    models = client.models.list()
    names = [m.id for m in models.data[:3]]
    print("OK: API key works. Sample models:", names)
    print("OpenAI connection verified successfully.")

if __name__ == "__main__":
    main()
