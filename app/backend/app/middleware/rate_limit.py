"""QA·시뮬레이션 등 엔드포인트용 Redis 기반 rate limit (분당 N회)."""
from typing import Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.redis import get_redis

RATE_LIMIT_WINDOW = 60  # 초
RATE_LIMIT_MAX = 60     # 분당 최대 요청

def _rate_limit_paths() -> Tuple[str, ...]:
    prefix = settings.API_V1_PREFIX
    return (
        f"{prefix}/qa",
        f"{prefix}/qa/stream",
        f"{prefix}/advanced/agent/query",
        f"{prefix}/sandbox/simulate",
    )

RATE_LIMIT_PATHS = _rate_limit_paths()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.scope.get("path", "")
        if not any(path.startswith(p) for p in RATE_LIMIT_PATHS):
            return await call_next(request)

        try:
            r = get_redis()
            ip = _client_ip(request)
            key = f"ratelimit:{path.split('/')[2]}:{ip}"
            count = r.incr(key)
            if count == 1:
                r.expire(key, RATE_LIMIT_WINDOW)
            if count > RATE_LIMIT_MAX:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."},
                )
        except Exception:
            pass
        return await call_next(request)
