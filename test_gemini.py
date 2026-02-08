import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import settings
from google import genai

def test_api():
    print(f"API Key present: {bool(settings.gemini_api_key)}")
    if not settings.gemini_api_key:
        print("❌ API Key is missing!")
        return

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say 'Hello Gemini 3' if you can hear me."
        )
        print(f"✅ Response: {response.text}")
    except Exception as e:
        print(f"❌ API Call Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api()
