# ======================================================================
# FSC Policy RAG System | 모듈: app.core.database
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

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
