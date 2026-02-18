"""Application configuration."""
from pydantic_settings import BaseSettings
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
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # LangSmith (Observability)
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_PROJECT: str = "fsc-policy-rag"
    LANGCHAIN_TRACING_V2: bool = True
    
    # LlamaParse
    LLAMAPARSE_API_KEY: str = ""
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # RSS Sources
    FSC_RSS_BASE: str = "https://www.fsc.go.kr/rss/rss.asp"
    FSC_RSS_FIDS: List[str] = ["0111", "0112", "0114", "0411"]
    
    # Vector DB
    VECTOR_DIMENSION: int = 1536
    
    # Processing
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K_RETRIEVAL: int = 10
    TOP_K_RERANK: int = 5
    
    # LangGraph
    MAX_AGENT_ITERATIONS: int = 5
    AGENT_TIMEOUT_SECONDS: int = 120
    
    # Ragas Evaluation
    RAGAS_TEST_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
