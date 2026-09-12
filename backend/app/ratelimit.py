"""로그인 시도 제한. 프로세스 메모리에 IP별 시도 시각을 둔다 (단일 컨테이너 전제)."""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

WINDOW = 60.0  # 초
MAX_ATTEMPTS = 5  # WINDOW 안에서 허용하는 로그인 시도 수
FAIL_DELAY = 1.0  # 비밀번호 틀렸을 때 응답 지연(초)

_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    # 컨테이너는 127.0.0.1에만 바인딩되므로 앞단 프록시가 붙인 X-Forwarded-For 를 신뢰한다.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def is_limited(ip: str) -> bool:
    """이번 시도를 기록하고, 제한을 넘었으면 True."""
    now = time.monotonic()
    with _lock:
        q = _attempts[ip]
        while q and now - q[0] > WINDOW:
            q.popleft()
        if len(q) >= MAX_ATTEMPTS:
            return True
        q.append(now)
        return False


def penalize_failure() -> None:
    if FAIL_DELAY > 0:
        time.sleep(FAIL_DELAY)


def reset() -> None:
    with _lock:
        _attempts.clear()
