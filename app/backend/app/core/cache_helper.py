"""Redis 캐시 헬퍼: TTL 기반 get/set (Gap Map·Analytics 요약 등)."""
import json
from typing import Any, Optional

from app.core.redis import get_redis

CACHE_TTL_GAP_MAP = 600   # 10분 (Heatmap·Gap Map 캐시 확대)
CACHE_TTL_ANALYTICS = 600  # 10분 (Analytics 캐시 확대)
CACHE_TTL_SANDBOX_SIMULATE = 600  # 10분 (시뮬레이션 결과 캐시)


def cache_get(key: str) -> Optional[Any]:
    """Redis에서 JSON 역직렬화하여 반환. 없으면 None."""
    try:
        r = get_redis()
        raw = r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """값을 JSON 직렬화해 Redis에 저장."""
    try:
        r = get_redis()
        r.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))
        return True
    except Exception:
        return False
