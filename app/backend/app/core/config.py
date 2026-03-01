"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, Dict


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
    
    # OpenAI (디폴트 mini로 토큰 절감. 필요 시 .env에서 gpt-4o 등으로 변경)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MODEL_CLASSIFICATION: str = ""  # 비우면 OPENAI_MODEL 사용. 분류만 정확도 올리려면 gpt-4o 등 설정
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # LangSmith (Observability)
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_PROJECT: str = "fsc-policy-rag"
    LANGCHAIN_TRACING_V2: bool = True
    
    # LlamaParse
    LLAMAPARSE_API_KEY: str = ""
    
    # Redis (로컬 기본값. Redis Cloud 사용 시 .env에 REDIS_URL 설정)
    # 예: redis://default:PASSWORD@redis-16019.c340....redislabs.com:16019/0
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    
    # RSS Sources - 금융위원회 (fid = 게시판 코드, 공식 4개 + 추가 2개)
    FSC_RSS_BASE: str = "http://www.fsc.go.kr/about/fsc_bbs_rss/"
    FSC_RSS_FIDS: List[str] = ["0111", "0112", "0114", "0113", "0115", "0411"]
    # 피드당 최대 수집 건수. 0이면 제한 없음(전체). 너무 크면 FSC 서버·DB 부하 가능.
    RSS_MAX_ITEMS: int = 500
    
    # 금융감독원 (FSS) - 웹 스크래핑
    FSS_BASE_URL: str = "https://www.fss.or.kr"
    FSS_BOARDS: List[str] = [
        "/fss/bbs/B0000052/list.do?menuNo=200358",  # 보도자료
        "/fss/bbs/B0000110/list.do?menuNo=200138",  # 공지사항
    ]
    ENABLE_FSS_SCRAPING: bool = True  # 금감원 스크래핑 활성화

    # 국제기구 RSS (Gap Map GI 국제 데이터·RAG 소스) — 금융위원회처럼 URL에서 크롤링
    ENABLE_INTERNATIONAL_RSS: bool = True
    INTERNATIONAL_RSS_FEEDS: List[Dict[str, str]] = [
        {"fid": "fsb_policy", "name": "FSB Policy Documents", "url": "https://www.fsb.org/wordpress/content_type/policy-documents/feed/"},
        {"fid": "fsb_g20", "name": "FSB Reports to the G20", "url": "https://www.fsb.org/wordpress/content_type/reports-to-the-g20/feed/"},
        {"fid": "fsb_press", "name": "FSB Press Releases", "url": "https://www.fsb.org/wordpress/content_type/press-releases/feed/"},
        {"fid": "bis_research", "name": "BIS Research Papers", "url": "https://www.bis.org/doclist/bis_fsi_publs.rss"},
        {"fid": "bis_press", "name": "BIS Press Releases", "url": "https://www.bis.org/doclist/all_pressrels.rss"},
    ]

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
    ENABLE_RERANKING: bool = True   # Cross-Encoder 리랭킹 (정확도 개선)
    ENABLE_TRACING: bool = True     # LangSmith 트레이싱 (API 키 설정 시 동작)
    
    # LangGraph
    MAX_AGENT_ITERATIONS: int = 5
    AGENT_TIMEOUT_SECONDS: int = 120
    
    # Ragas Evaluation
    RAGAS_TEST_SIZE: int = 100
    
    # Notifications
    SLACK_WEBHOOK_URL: str = ""

    # CORS (프로덕션 도메인. 쉼표 구분 문자열, 비우면 CORS_DEFAULT_ORIGINS 사용)
    CORS_ORIGINS: str = ""
    CORS_DEFAULT_ORIGINS: List[str] = [
        "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
        "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
