import time
from typing import Dict, Tuple

class RateLimiter:
    """In-memory rate limiter with sliding window and cooldown mechanisms."""

    def __init__(self):
        # Key: (action_name, user_id) -> last_timestamp
        self._last_actions: Dict[Tuple[str, int], float] = {}

    def is_rate_limited(self, action: str, user_id: int, cooldown_seconds: float) -> Tuple[bool, float]:
        """
        Check if user action is rate-limited.
        Returns: (is_limited: bool, remaining_seconds: float)
        """
        key = (action, user_id)
        now = time.time()
        last_time = self._last_actions.get(key, 0.0)
        elapsed = now - last_time

        if elapsed < cooldown_seconds:
            remaining = cooldown_seconds - elapsed
            return True, remaining

        self._last_actions[key] = now
        return False, 0.0

    def cleanup(self, max_age_seconds: float = 3600.0) -> None:
        """Purge entries older than max_age_seconds to free memory."""
        now = time.time()
        keys_to_delete = [
            k for k, last_time in self._last_actions.items()
            if (now - last_time) > max_age_seconds
        ]
        for k in keys_to_delete:
            del self._last_actions[k]


rate_limiter = RateLimiter()
