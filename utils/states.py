import time
from typing import Dict, Any, Optional

class UserState:
    """Represents the interactive input state for an administrative user."""
    def __init__(self, state: str, data: Optional[Dict[str, Any]] = None, timeout: float = 600.0):
        self.state = state
        self.data = data or {}
        self.created_at = time.time()
        self.timeout = timeout

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.timeout


class StateManager:
    """Manages active conversation states for bot users."""
    def __init__(self):
        self._states: Dict[int, UserState] = {}

    def set_state(self, user_id: int, state: str, data: Optional[Dict[str, Any]] = None, timeout: float = 600.0) -> None:
        """Assign state and arbitrary context data to user."""
        self._states[user_id] = UserState(state, data, timeout)

    def get_state(self, user_id: int) -> Optional[str]:
        """Retrieve user's active state if not expired."""
        user_state = self._states.get(user_id)
        if not user_state:
            return None
        if user_state.is_expired:
            del self._states[user_id]
            return None
        return user_state.state

    def get_data(self, user_id: int) -> Dict[str, Any]:
        """Retrieve stored state context data."""
        user_state = self._states.get(user_id)
        if not user_state or user_state.is_expired:
            return {}
        return user_state.data

    def update_data(self, user_id: int, **kwargs) -> None:
        """Update existing state context data."""
        user_state = self._states.get(user_id)
        if user_state and not user_state.is_expired:
            user_state.data.update(kwargs)

    def clear_state(self, user_id: int) -> None:
        """Clear user state."""
        if user_id in self._states:
            del self._states[user_id]


# Global instance
state_manager = StateManager()

# Defined state constants
class States:
    WAITING_FOR_CHAT_LINK = "WAITING_FOR_CHAT_LINK"
    WAITING_FOR_WELCOME_MSG = "WAITING_FOR_WELCOME_MSG"
    WAITING_FOR_WELCOME_PHOTO = "WAITING_FOR_WELCOME_PHOTO"
    WAITING_FOR_TIMEOUT = "WAITING_FOR_TIMEOUT"
    WAITING_FOR_REQ_CHAT_LINK = "WAITING_FOR_REQ_CHAT_LINK"
    WAITING_FOR_REQ_BTN_TEXT = "WAITING_FOR_REQ_BTN_TEXT"
    WAITING_FOR_REQ_INVITE_LINK = "WAITING_FOR_REQ_INVITE_LINK"
