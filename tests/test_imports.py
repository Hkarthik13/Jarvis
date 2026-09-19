import sys
import os

# Append workspace root to path to ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    print("Testing module imports for JARVIS V1...")
    
    try:
        from backend.config import settings
        print(" [OK] backend.config.settings imported successfully.")
    except Exception as e:
        print(f" [FAIL] backend.config import failed: {e}")
        return False
        
    try:
        from backend.utils.logger import logger
        print(" [OK] backend.utils.logger imported successfully.")
    except Exception as e:
        print(f" [FAIL] backend.utils.logger import failed: {e}")
        return False
        
    try:
        from backend.ai.client import ai_client
        print(" [OK] backend.ai.client.ai_client imported successfully.")
    except Exception as e:
        print(f" [FAIL] backend.ai.client import failed: {e}")
        return False
        
    try:
        from backend.voice.stt import transcribe_audio
        print(" [OK] backend.voice.stt.transcribe_audio imported successfully.")
    except Exception as e:
        print(f" [FAIL] backend.voice.stt import failed: {e}")
        return False
        
    try:
        from backend.voice.tts import synthesize_speech
        print(" [OK] backend.voice.tts.synthesize_speech imported successfully.")
    except Exception as e:
        print(f" [FAIL] backend.voice.tts import failed: {e}")
        return False
        
    try:
        from backend.main import app
        print(" [OK] backend.main.app imported successfully.")
    except Exception as e:
        print(f" [FAIL] backend.main import failed: {e}")
        return False

    print("\nAll modules imported and compile successfully! Syntax checks passed.")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
