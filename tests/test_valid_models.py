import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from groq import AsyncGroq
from backend.config import settings

async def main():
    client = AsyncGroq(api_key=settings.groq_api_key)
    valid_models = [
        "groq/compound-mini",
        "qwen/qwen3.8-27b",
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "groq/compound"
    ]
    for m in valid_models:
        try:
            print(f"\n--- Testing {m} with max_tokens=600 ---")
            res = await client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": "Hello, how are you?"}],
                max_tokens=600
            )
            print(f"SUCCESS: {res.choices[0].message.content[:80]}")
        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
