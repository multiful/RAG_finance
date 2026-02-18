"""Redis connection management."""
import redis
from app.core.config import settings


class RedisClient:
    """Redis client singleton."""
    
    _client: redis.Redis = None
    
    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get or create Redis client."""
        if cls._client is None:
            cls._client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
        return cls._client
    
    @classmethod
    def close(cls):
        """Close Redis connection."""
        if cls._client:
            cls._client.close()
            cls._client = None


def get_redis() -> redis.Redis:
    """Get Redis client dependency."""
    return RedisClient.get_client()
