"""Database connection and session management."""
from supabase import create_client, Client
from app.core.config import settings


class Database:
    """Supabase database client."""
    
    _client: Client = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client."""
        if cls._client is None:
            cls._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
        return cls._client
    
    @classmethod
    async def close(cls):
        """Close database connection."""
        cls._client = None


def get_db() -> Client:
    """Get database client dependency."""
    return Database.get_client()
