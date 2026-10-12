import hashlib
import hmac
import time
from collections import defaultdict, deque

SESSION_COOKIE = "noteclaire_session"
SESSION_LIFETIME_SECONDS = 60 * 60 * 24 * 90


def _signature(password: str, expires: int) -> str:
    return hmac.new(
        password.encode(), f"noteclaire-session-v2|{expires}".encode(), hashlib.sha256
    ).hexdigest()


def session_token(password: str, now: float | None = None) -> str:
    """Jeton « échéance.signature » : il expire côté serveur, et changer APP_PASSWORD l'invalide."""
    expires = int((time.time() if now is None else now) + SESSION_LIFETIME_SECONDS)
    return f"{expires}.{_signature(password, expires)}"


def is_valid_token(password: str, token: str | None, now: float | None = None) -> bool:
    expires, _, signature = (token or "").partition(".")
    if not expires.isdecimal() or int(expires) <= (time.time() if now is None else now):
        return False
    return hmac.compare_digest(_signature(password, int(expires)), signature)


def is_valid_password(expected: str, given: str) -> bool:
    return hmac.compare_digest(expected.encode(), given.encode())


class LoginThrottle:
    """Bloque temporairement un client après trop d'échecs (essais en série ou en parallèle)."""

    def __init__(self, max_failures: int = 5, window_seconds: float = 300) -> None:
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _recent(self, client: str, now: float) -> deque[float]:
        failures = self._failures[client]
        while failures and now - failures[0] > self.window:
            failures.popleft()
        if not failures:
            self._failures.pop(client, None)
        return failures

    def blocked(self, client: str, now: float | None = None) -> bool:
        return len(self._recent(client, time.time() if now is None else now)) >= self.max_failures

    def failed(self, client: str, now: float | None = None) -> None:
        self._failures[client].append(time.time() if now is None else now)

    def succeeded(self, client: str) -> None:
        self._failures.pop(client, None)
