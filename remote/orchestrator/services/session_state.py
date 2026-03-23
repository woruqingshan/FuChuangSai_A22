from collections import defaultdict


class SessionState:
    def __init__(self) -> None:
        self._history: dict[str, list[str]] = defaultdict(list)

    def append_turn(self, session_id: str, user_text: str) -> None:
        if user_text:
            self._history[session_id].append(user_text)

    def get_summary(self, session_id: str, limit: int = 2) -> str:
        turns = self._history.get(session_id, [])
        if not turns:
            return ""
        return "；".join(turns[-limit:])


session_state = SessionState()
