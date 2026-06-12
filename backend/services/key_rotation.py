"""
Vachan Study Bible Chatbot — Gemini API Key Rotation Service
Automatically rotates through multiple Gemini API keys when one hits rate limits.
"""

import os
import time
import threading
from typing import Optional

# Cooldown period in seconds before retrying a rate-limited key
KEY_COOLDOWN_SECONDS = 60


class GeminiKeyRotator:
    """Thread-safe Gemini API key rotator with automatic cooldown tracking."""
    
    def __init__(self):
        self._keys: list[str] = []
        self._current_index: int = 0
        self._cooldowns: dict[int, float] = {}  # index -> timestamp when cooldown expires
        self._lock = threading.Lock()
        self._load_keys()
    
    def _load_keys(self):
        """Loads API keys from GEMINI_API_KEYS (comma-separated) or falls back to GEMINI_API_KEY."""
        keys_str = os.environ.get("GEMINI_API_KEYS", "")
        if keys_str:
            self._keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        
        # Fallback to single key
        if not self._keys:
            single = os.environ.get("GEMINI_API_KEY", "")
            if single:
                self._keys = [single]
        
        if self._keys:
            print(f"Gemini Key Rotator: Loaded {len(self._keys)} API key(s).")
        else:
            print("Gemini Key Rotator: WARNING — No API keys found!")
    
    @property
    def total_keys(self) -> int:
        return len(self._keys)
    
    def get_active_key(self) -> Optional[str]:
        """Returns the current active (non-cooldown) API key, or None if all keys are exhausted."""
        with self._lock:
            if not self._keys:
                return None
            
            now = time.time()
            # Try each key starting from current index
            for _ in range(len(self._keys)):
                idx = self._current_index % len(self._keys)
                cooldown_until = self._cooldowns.get(idx, 0)
                
                if now >= cooldown_until:
                    return self._keys[idx]
                
                # This key is still cooling down, try the next one
                self._current_index = (self._current_index + 1) % len(self._keys)
            
            # All keys are on cooldown — return the one closest to expiry
            earliest_idx = min(self._cooldowns, key=self._cooldowns.get)
            wait_time = self._cooldowns[earliest_idx] - now
            print(f"Gemini Key Rotator: All {len(self._keys)} keys are rate-limited. Nearest available in {wait_time:.0f}s.")
            self._current_index = earliest_idx
            return self._keys[earliest_idx]
    
    def report_rate_limited(self):
        """Marks the current key as rate-limited and rotates to the next available key."""
        with self._lock:
            idx = self._current_index % len(self._keys)
            self._cooldowns[idx] = time.time() + KEY_COOLDOWN_SECONDS
            old_index = idx + 1  # human-readable 1-based
            self._current_index = (self._current_index + 1) % len(self._keys)
            new_index = (self._current_index % len(self._keys)) + 1
            print(f"Gemini Key Rotator: Key #{old_index} rate-limited. Rotating to Key #{new_index} (cooldown {KEY_COOLDOWN_SECONDS}s).")
    
    def report_success(self):
        """Clears cooldown on the current key after a successful request."""
        with self._lock:
            idx = self._current_index % len(self._keys)
            if idx in self._cooldowns:
                del self._cooldowns[idx]


# Global singleton instance
_rotator: Optional[GeminiKeyRotator] = None


def get_key_rotator() -> GeminiKeyRotator:
    """Returns the global GeminiKeyRotator singleton."""
    global _rotator
    if _rotator is None:
        _rotator = GeminiKeyRotator()
    return _rotator
