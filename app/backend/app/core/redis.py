"""Redis connection management. Redis 미사용 시 인메모리 폴백으로 서버 기동."""
import redis
from app.core.config import settings


class _MemoryRedis:
    """Redis 연결 불가 시 사용하는 인메모리 폴백. 동일 인터페이스 제공."""

    def __init__(self):
        self._store: dict = {}
        self._ttl: dict = {}  # key -> (expiry_ts, value) for setex

    def ping(self) -> bool:
        return False  # health check에서 "캐시 미사용"으로 표시

    def get(self, key: str):
        if key in self._ttl:
            import time
            expiry, val = self._ttl[key]
            if time.time() > expiry:
                del self._ttl[key]
                return None
            return val
        return self._store.get(key)

    def set(self, key: str, value, ex=None):
        import time
        if ex is not None:
            self._ttl[key] = (time.time() + ex, value)
        else:
            self._store[key] = value
        return True

    def setex(self, key: str, ttl_seconds: int, value):
        import time
        self._ttl[key] = (time.time() + ttl_seconds, value)
        return True

    def incr(self, key: str) -> int:
        import time
        if key in self._ttl:
            expiry, val = self._ttl[key]
            if time.time() > expiry:
                del self._ttl[key]
                self._ttl[key] = (time.time() + 60, 1)
                return 1
            v = int(val) + 1
            self._ttl[key] = (expiry, v)
            return v
        v = int(self._store.get(key, 0)) + 1
        self._store[key] = v
        return v

    def expire(self, key: str, seconds: int) -> bool:
        import time
        val = self.get(key)
        if val is not None:
            self.setex(key, seconds, val)
            return True
        return False

    def keys(self, pattern: str):
        all_keys = set(self._store.keys()) | set(self._ttl.keys())
        # "query:*" 등 단순 패턴만 지원
        if "*" in pattern:
            prefix = pattern.split("*")[0]
            return [k for k in all_keys if k.startswith(prefix)]
        return [k for k in all_keys if k == pattern]

    def delete(self, *keys):
        n = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                n += 1
            if k in self._ttl:
                del self._ttl[k]
                n += 1
        return n

    def info(self, section=None):
        return {
            "used_memory_human": "0B",
            "connected_clients": 0,
        }

    def close(self):
        self._store.clear()
        self._ttl.clear()


class RedisClient:
    """Redis client singleton. 연결 실패 시 _MemoryRedis 사용."""

    _client = None
    _is_fallback = False

    @classmethod
    def get_client(cls):
        """Get or create Redis client. 연결 불가 시 인메모리 폴백 반환."""
        if cls._client is not None:
            return cls._client
        try:
            # Redis Cloud 등 원격 Redis 대비 타임아웃 완화
            client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            client.ping()
            cls._client = client
            cls._is_fallback = False
            return cls._client
        except Exception as e:
            print(f"[WARN] Redis 연결 실패, 인메모리 캐시로 동작합니다: {e}")
            cls._client = _MemoryRedis()
            cls._is_fallback = True
            return cls._client

    @classmethod
    def ping(cls) -> bool:
        """Check Redis connectivity."""
        try:
            client = cls.get_client()
            return client.ping()
        except Exception as e:
            print(f"Redis ping failed: {e}")
            return False

    @classmethod
    def is_fallback(cls) -> bool:
        """인메모리 폴백 사용 중인지."""
        if cls._client is None:
            cls.get_client()
        return cls._is_fallback

    @classmethod
    def close(cls):
        """Close Redis connection."""
        if cls._client:
            if hasattr(cls._client, "close"):
                try:
                    cls._client.close()
                except Exception:
                    pass
            cls._client = None
            cls._is_fallback = False


def get_redis():
    """Get Redis client dependency. (실제 Redis 또는 인메모리 폴백)"""
    return RedisClient.get_client()
