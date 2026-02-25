"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # App
    APP_NAME: str = "FSC Policy RAG System"
    DEBUG: bool = False
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # LangSmith (Observability)
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_PROJECT: str = "fsc-policy-rag"
    LANGCHAIN_TRACING_V2: bool = True
    
    # LlamaParse
    LLAMAPARSE_API_KEY: str = ""
    
    # Redis
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    
    # RSS Sources - 금융위원회 (fid = 게시판 코드, 공식 4개 + 추가 2개)
    FSC_RSS_BASE: str = "http://www.fsc.go.kr/about/fsc_bbs_rss/"
    FSC_RSS_FIDS: List[str] = ["0111", "0112", "0114", "0113", "0115", "0411"]
    RSS_MAX_ITEMS: int = 200  # Default to 200 items per feed
    
    # 금융감독원 (FSS) - 웹 스크래핑
    FSS_BASE_URL: str = "https://www.fss.or.kr"
    FSS_BOARDS: List[str] = [
        "/fss/bbs/B0000052/list.do?menuNo=200358",  # 보도자료
        "/fss/bbs/B0000110/list.do?menuNo=200138",  # 공지사항
    ]
    ENABLE_FSS_SCRAPING: bool = True  # 금감원 스크래핑 활성화

    # 일일 자동 수집 (경량 스케줄, 디스크/메모리 절약)
    ENABLE_DAILY_COLLECTION: bool = True
    COLLECTION_AT_HOUR: int = 3  # 03:00
    COLLECTION_TZ: str = "Asia/Seoul"
    
    # Vector DB
    VECTOR_DIMENSION: int = 1536
    
    # Processing
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K_RETRIEVAL: int = 10
    TOP_K_RERANK: int = 5
    ENABLE_RERANKING: bool = False  # Set to False to avoid huggingface_hub import errors
    ENABLE_TRACING: bool = False    # Set to False to avoid LangSmith 400 errors
    
    # LangGraph
    MAX_AGENT_ITERATIONS: int = 5
    AGENT_TIMEOUT_SECONDS: int = 120
    
    # Ragas Evaluation
    RAGAS_TEST_SIZE: int = 100
    
    # Notifications
    SLACK_WEBHOOK_URL: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
