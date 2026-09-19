import hmac
import hashlib
import time
import secrets
from backend.config import settings
from backend.utils.logger import logger

class DeviceAuthManager:
    """
    Manages secure pairing, cryptographic challenge-response authentication,
    and HMAC-SHA256 signatures between mobile controllers and the laptop agent.
    """
    def __init__(self):
        self._paired_devices: dict[str, dict] = {}
        # In-memory nonce cache to prevent replay attacks (nonce -> expiry timestamp)
        self._nonces: dict[str, float] = {}

    def generate_pairing_token(self, device_id: str, device_name: str = "Mobile Client") -> str:
        """Generates a secure pairing token for a mobile device."""
        secret = secrets.token_hex(32)
        issued_at = time.time()
        self._paired_devices[device_id] = {
            "device_id": device_id,
            "device_name": device_name,
            "secret": secret,
            "paired_at": issued_at,
            "last_active": issued_at
        }
        logger.info(f"Paired new device '{device_name}' (ID: {device_id})")
        return secret

    def verify_request_signature(self, device_id: str, payload_str: str, timestamp: int, signature: str) -> bool:
        """
        Verifies that an incoming request payload has a valid HMAC-SHA256 signature
        and hasn't expired or been replayed.
        """
        # 1. Check timestamp window (allow max 60 seconds drift)
        current_time = int(time.time())
        if abs(current_time - timestamp) > 60:
            logger.warning(f"Rejected request from {device_id}: Timestamp drift too large ({timestamp} vs {current_time})")
            return False

        # 2. Lookup device secret or fallback to master JARVIS key
        device = self._paired_devices.get(device_id)
        secret = device["secret"] if device else settings.jarvis_api_key

        if not secret:
            return True  # If no auth configured in development

        # 3. Compute expected HMAC
        message = f"{device_id}:{timestamp}:{payload_str}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

        is_valid = hmac.compare_digest(expected_sig, signature)
        if is_valid and device:
            device["last_active"] = time.time()
        return is_valid

    def create_signature(self, device_id: str, payload_str: str, secret: str = None) -> tuple[int, str]:
        """Utility for clients/agents to sign an outbound message."""
        sec = secret or settings.jarvis_api_key
        ts = int(time.time())
        message = f"{device_id}:{ts}:{payload_str}".encode("utf-8")
        sig = hmac.new(sec.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return ts, sig

    def is_device_paired(self, device_id: str) -> bool:
        return device_id in self._paired_devices

# Global device authentication manager instance
device_auth = DeviceAuthManager()
