"""Redis 캐시 헬퍼: TTL 기반 get/set (Gap Map·Analytics 요약 등)."""
import json
from typing import Any, Optional

from app.core.redis import get_redis

CACHE_TTL_GAP_MAP = 600   # 10분 (Heatmap·Gap Map 캐시 확대)
CACHE_TTL_ANALYTICS = 600  # 10분 (Analytics 캐시 확대)
CACHE_TTL_SANDBOX_SIMULATE = 600  # 10분 (시뮬레이션 결과 캐시)
# 대시보드·평가 요약: 프론트 60초 폴링 대비 DB 부하 완화 (짧은 TTL로 신선도 유지)
CACHE_TTL_DASHBOARD = 120       # 2분
CACHE_TTL_DASHBOARD_HOURLY = 90  # 1.5분 (차트용)
CACHE_TTL_METRICS_SUMMARY = 180  # 3분


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


def cache_delete(key: str) -> None:
    try:
        get_redis().delete(key)
    except Exception:
        pass


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """값을 JSON 직렬화해 Redis에 저장."""
    try:
        r = get_redis()
        r.setex(key, ttl_seconds, json.dumps(value, ensure_ascii=False))
        return True
    except Exception:
        return False


def invalidate_dashboard_caches() -> None:
    """RSS/FSS 수집 완료 후 대시보드·평가 요약 캐시 무효화."""
    try:
        r = get_redis()
        keys_to_del = []
        if hasattr(r, "scan_iter"):
            for k in r.scan_iter(match="dashboard:*"):
                keys_to_del.append(k)
        else:
            keys_to_del.extend(r.keys("dashboard:*"))
        for k in keys_to_del:
            r.delete(k)
        cache_delete("evaluation:metrics_summary:v1")
    except Exception:
        pass


def invalidate_query_cache_prefix() -> None:
    """query:* 캐시 키 삭제 — KEYS 대신 SCAN 우선 (대량 키 시 병목 완화)."""
    try:
        r = get_redis()
        to_del = []
        if hasattr(r, "scan_iter"):
            for k in r.scan_iter(match="query:*"):
                to_del.append(k)
        else:
            to_del = list(r.keys("query:*"))
        if to_del:
            r.delete(*to_del)
    except Exception:
        pass
