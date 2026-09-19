import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from groq import AsyncGroq
from backend.config import settings

async def main():
    client = AsyncGroq(api_key=settings.groq_api_key)
    try:
        models = await client.models.list()
        print("Available Groq models on this account:")
        for m in models.data:
            print(f" - {m.id}")
    except Exception as e:
        print(f"Failed to list models: {e}")

    test_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "meta-llama/llama-guard-3-8b",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]
    for m in test_models:
        try:
            print(f"\nTesting {m}...")
            res = await client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": "Say hello in 5 words"}]
            )
            print(f"SUCCESS with {m}: {res.choices[0].message.content}")
        except Exception as e:
            print(f"FAILED with {m}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
