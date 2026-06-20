"""
Vachan Study Bible Chatbot — Gemini API Key Rotation Service
Automatically rotates through multiple Gemini API keys when one hits rate limits.
"""

import os
import time
import threading
from typing import Optional

from db.repositories import KeyRepository

# Cooldown period in seconds before retrying a rate-limited key
KEY_COOLDOWN_SECONDS = 60


class GeminiKeyRotator:
    """Thread-safe and MongoDB-backed Gemini API key rotator with automatic cooldown tracking."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._current_key: Optional[str] = None
        self._fallback_keys: list[str] = []
        self._fallback_cooldowns: dict[str, float] = {}
        self._load_fallback_keys()
        self._sync_env_to_db()
    
    def _load_fallback_keys(self):
        """Loads API keys from GEMINI_API_KEYS (comma-separated) or falls back to GEMINI_API_KEY."""
        keys_str = os.environ.get("GEMINI_API_KEYS", "")
        if keys_str:
            self._fallback_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        
        # Fallback to single key
        if not self._fallback_keys:
            single = os.environ.get("GEMINI_API_KEY", "")
            if single:
                self._fallback_keys = [single]
                
    def _sync_env_to_db(self):
        """Pushes any keys found in .env into MongoDB automatically on startup."""
        try:
            added = 0
            for key in self._fallback_keys:
                if KeyRepository.add_key(key):
                    added += 1
            if added > 0:
                print(f"Gemini Key Rotator: Synced {len(self._fallback_keys)} env keys to MongoDB.")
        except Exception as e:
            print(f"Gemini Key Rotator: MongoDB unreachable for sync ({e}). Running in fallback mode.")
    
    @property
    def total_keys(self) -> int:
        try:
            return len(KeyRepository.get_all_keys())
        except Exception:
            return len(self._fallback_keys)
    
    def get_active_key(self) -> Optional[str]:
        """Returns the oldest available (non-cooldown) API key from MongoDB."""
        with self._lock:
            try:
                keys_data = KeyRepository.get_all_keys()
                if not keys_data:
                    # DB empty, rely on fallback
                    return self._get_fallback_key()
                    
                now = time.time()
                available_keys = []
                cooldown_keys = []
                
                for kd in keys_data:
                    token = kd.get("token")
                    cooldown = kd.get("cooldown_until", 0.0)
                    if now >= cooldown:
                        available_keys.append(token)
                    else:
                        cooldown_keys.append((token, cooldown))
                        
                if available_keys:
                    self._current_key = available_keys[0]
                    return self._current_key
                    
                # All keys are on cooldown — return the one closest to expiry
                if cooldown_keys:
                    cooldown_keys.sort(key=lambda x: x[1])
                    earliest_key, earliest_time = cooldown_keys[0]
                    wait_time = earliest_time - now
                    print(f"Gemini Key Rotator: All {len(keys_data)} keys are rate-limited. Nearest available in {wait_time:.0f}s.")
                    self._current_key = earliest_key
                    return self._current_key
                    
                return None
            except Exception as e:
                print(f"Gemini Key Rotator: DB Error ({e}). Using fallback keys.")
                return self._get_fallback_key()

    async def get_active_key_async(self) -> Optional[str]:
        try:
            keys_data = await KeyRepository.get_all_keys_async()
            if not keys_data: return self._get_fallback_key()
            now = time.time()
            available_keys = []
            cooldown_keys = []
            for kd in keys_data:
                token = kd.get("token")
                cooldown = kd.get("cooldown_until", 0.0)
                if now >= cooldown: available_keys.append(token)
                else: cooldown_keys.append((token, cooldown))
            if available_keys:
                self._current_key = available_keys[0]
                return self._current_key
            if cooldown_keys:
                cooldown_keys.sort(key=lambda x: x[1])
                earliest_key, earliest_time = cooldown_keys[0]
                self._current_key = earliest_key
                return self._current_key
            return None
        except Exception as e:
            print(f"Gemini Key Rotator: Async DB Error ({e}). Using fallback keys.")
            return self._get_fallback_key()
                
    def _get_fallback_key(self) -> Optional[str]:
        """In-memory rotation if MongoDB fails."""
        if not self._fallback_keys:
            return None
        now = time.time()
        for k in self._fallback_keys:
            if now >= self._fallback_cooldowns.get(k, 0.0):
                self._current_key = k
                return k
        # Return first if all on cooldown
        self._current_key = self._fallback_keys[0]
        return self._current_key
    
    def report_rate_limited(self):
        """Marks the current key as rate-limited in MongoDB and forces a rotation."""
        with self._lock:
            if not self._current_key:
                return
            try:
                KeyRepository.mark_rate_limited(self._current_key, KEY_COOLDOWN_SECONDS)
                print(f"Gemini Key Rotator: Key rate-limited. Pushed 60s cooldown to MongoDB.")
            except Exception:
                self._fallback_cooldowns[self._current_key] = time.time() + KEY_COOLDOWN_SECONDS
                print("Gemini Key Rotator: Key rate-limited (Fallback Memory).")
    
    def report_success(self):
        """Clears cooldown on the current key after a successful request."""
        with self._lock:
            if not self._current_key:
                return
            try:
                KeyRepository.report_success(self._current_key)
            except Exception:
                if self._current_key in self._fallback_cooldowns:
                    del self._fallback_cooldowns[self._current_key]


# Global singleton instance
_rotator: Optional[GeminiKeyRotator] = None


def get_key_rotator() -> GeminiKeyRotator:
    """Returns the global GeminiKeyRotator singleton."""
    global _rotator
    if _rotator is None:
        _rotator = GeminiKeyRotator()
    return _rotator
