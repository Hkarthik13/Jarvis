import os
import sys
import asyncio
import base64
import requests
import edge_tts
import dotenv

# Load environment variables
dotenv.load_dotenv()

BASE_URL = "http://127.0.0.1:8000"
API_KEY = os.getenv("JARVIS_API_KEY", "jarvis_secure_key_123")

def safe_print(*args, **kwargs):
    """Print arguments safely, replacing unencodable characters (like emojis) on Windows."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        new_args = []
        for arg in args:
            if isinstance(arg, str):
                # Fallback: encode and decode with replace to drop incompatible characters
                new_args.append(arg.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8'))
            else:
                new_args.append(arg)
        print(*new_args, **kwargs)

async def generate_test_audio(text: str, filename: str):
    """Generate a test speech file to simulate user voice input."""
    safe_print(f"Generating test voice input: '{text}'...")
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    await communicate.save(filename)
    safe_print(f"Saved test voice input to {filename}")

def test_chat():
    safe_print("\n=== Testing /api/chat (Text Chat) ===")
    url = f"{BASE_URL}/api/chat"
    payload = {
        "messages": [
            {"role": "user", "content": "Hello JARVIS, list three core capabilities you possess."}
        ]
    }
    
    # 1. Test missing API key header (Expected 401)
    safe_print("Testing chat endpoint without API Key...")
    try:
        r_missing = requests.post(url, json=payload)
        safe_print(f"Status: {r_missing.status_code} (Expected: 401)")
        assert r_missing.status_code == 401
    except AssertionError:
        safe_print("[FAIL] Expected 401 Unauthorized for missing API Key header.")
        return False

    # 2. Test invalid API key header (Expected 401)
    safe_print("Testing chat endpoint with incorrect API Key...")
    try:
        r_invalid = requests.post(url, json=payload, headers={"X-Jarvis-API-Key": "wrong_key"})
        safe_print(f"Status: {r_invalid.status_code} (Expected: 401)")
        assert r_invalid.status_code == 401
    except AssertionError:
        safe_print("[FAIL] Expected 401 Unauthorized for invalid API Key header.")
        return False

    # 3. Test correct API key header (Expected 200)
    safe_print("Testing chat endpoint with correct API Key...")
    try:
        headers = {"X-Jarvis-API-Key": API_KEY}
        response = requests.post(url, json=payload, headers=headers)
        safe_print(f"Status: {response.status_code} (Expected: 200)")
        if response.status_code == 200:
            safe_print("JARVIS Response:\n", response.json().get("response"))
            assert "response" in response.json()
        else:
            safe_print("[FAIL] Live chat request failed:", response.text)
            return False
    except Exception as e:
        safe_print(f"[FAIL] Connection Error: {e}")
        return False

    safe_print("[PASS] Chat security checks passed.")
    return True

def test_voice(audio_filename: str, output_filename: str):
    safe_print("\n=== Testing /api/voice (Voice Chat Pipeline) ===")
    url = f"{BASE_URL}/api/voice"
    
    # 1. Test missing API key header (Expected 401)
    safe_print("Testing voice endpoint without API Key...")
    try:
        with open(audio_filename, "rb") as f:
            files = {"file": (audio_filename, f, "audio/mpeg")}
            r_missing = requests.post(url, files=files)
        safe_print(f"Status: {r_missing.status_code} (Expected: 401)")
        assert r_missing.status_code == 401
    except AssertionError:
        safe_print("[FAIL] Expected 401 Unauthorized for missing API Key header.")
        return False

    # 2. Test invalid API key header (Expected 401)
    safe_print("Testing voice endpoint with incorrect API Key...")
    try:
        with open(audio_filename, "rb") as f:
            files = {"file": (audio_filename, f, "audio/mpeg")}
            r_invalid = requests.post(url, files=files, headers={"X-Jarvis-API-Key": "wrong_key"})
        safe_print(f"Status: {r_invalid.status_code} (Expected: 401)")
        assert r_invalid.status_code == 401
    except AssertionError:
        safe_print("[FAIL] Expected 401 Unauthorized for invalid API Key header.")
        return False

    # 3. Test correct API key header (Expected 200)
    safe_print("Testing voice endpoint with correct API Key...")
    try:
        headers = {"X-Jarvis-API-Key": API_KEY}
        with open(audio_filename, "rb") as f:
            files = {"file": (audio_filename, f, "audio/mpeg")}
            response = requests.post(url, files=files, headers=headers)
            
        safe_print(f"Status: {response.status_code} (Expected: 200)")
        if response.status_code == 200:
            data = response.json()
            safe_print("Transcribed User Text:", data.get("transcribed_text"))
            safe_print("JARVIS Text Response:", data.get("llm_response"))
            
            audio_base64 = data.get("audio_base64")
            if audio_base64:
                audio_bytes = base64.b64decode(audio_base64)
                with open(output_filename, "wb") as out_f:
                    out_f.write(audio_bytes)
                safe_print(f"JARVIS Audio Response saved successfully to: {output_filename}")
                assert len(audio_bytes) > 0
            else:
                safe_print("[FAIL] No audio output returned.")
                return False
        else:
            safe_print("[FAIL] Live voice request failed:", response.text)
            return False
    except Exception as e:
        safe_print(f"[FAIL] Connection Error: {e}")
        return False

    safe_print("[PASS] Voice security checks passed.")
    return True

async def main():
    input_file = "test_user_input.mp3"
    output_file = "jarvis_response.mp3"
    
    # 1. Verify text endpoint
    chat_ok = test_chat()
    
    # 2. Create simulated speech input
    await generate_test_audio("Hello JARVIS, tell me a short joke.", input_file)
    
    # 3. Verify speech pipeline endpoint
    voice_ok = test_voice(input_file, output_file)
    
    if chat_ok and voice_ok:
        safe_print("\nAll live API security checks passed successfully!")
        sys.exit(0)
    else:
        safe_print("\nSome live API security checks failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
