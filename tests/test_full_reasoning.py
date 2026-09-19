import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from backend.ai.client import ai_client

async def main():
    print("Testing chat response with tools...")
    queries = [
        "What is my laptop battery and CPU status?",
        "What is the weather in Chennai?",
        "Hello Jarvis, how are you?"
    ]
    for q in queries:
        print(f"\n[QUERY]: {q}")
        res = await ai_client.generate_chat_response([{"role": "user", "content": q}])
        print(f"[RESPONSE]: {res.encode('ascii', errors='replace').decode('ascii')}\n")

if __name__ == "__main__":
    asyncio.run(main())
