import time
from collections import defaultdict, deque
from threading import Lock

from app.config import RATE_LIMIT_PER_HOUR, RATE_LIMIT_PER_MIN


class RateLimiter:
    def __init__(self) -> None:
        self._minute: dict[str, deque] = defaultdict(deque)
        self._hour: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            minute = self._minute[key]
            hour = self._hour[key]
            while minute and now - minute[0] > 60:
                minute.popleft()
            while hour and now - hour[0] > 3600:
                hour.popleft()
            if len(minute) >= RATE_LIMIT_PER_MIN or len(hour) >= RATE_LIMIT_PER_HOUR:
                return False
            minute.append(now)
            hour.append(now)
            return True


limiter = RateLimiter()
