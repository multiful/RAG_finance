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
    
    # OpenAI — 일반 기능은 mini, RAG 질의는 OPENAI_MODEL_QA로 분리(정확도·근거 우선)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    # RAG HyDE·답변가능성·최종 답변 전용. 비우면 OPENAI_MODEL(gpt-4o-mini 등)과 동일 — 비용·지연 최우선 시 비움 유지
    OPENAI_MODEL_QA: str = ""
    OPENAI_MODEL_CLASSIFICATION: str = ""  # 비우면 OPENAI_MODEL 사용. 분류만 정확도 올리려면 gpt-4o 등 설정
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # LangSmith (Observability)
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_PROJECT: str = "fsc-policy-rag"
    # Railway 등 프로덕션: 키 없으면 false 권장(오버헤드·로그 감소). LangSmith 쓰면 true + LANGSMITH_API_KEY
    LANGCHAIN_TRACING_V2: bool = False
    
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
    CHUNK_OVERLAP: int = 120  # 재귀 청킹 시 문맥 연속성
    # 검색·리랭크: 후보는 넉넉히, 리랭크는 sentence-transformers 필요(Railway 슬림은 false 권장)
    # 골든셋·규제 QA 리콜: 후보를 넉넉히(리랭크 전)
    TOP_K_RETRIEVAL: int = 24
    TOP_K_RERANK: int = 10
    ENABLE_RERANKING: bool = False
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # HyDE: 질문당 LLM 1회 추가. 프로덕션 기본 false(지연·비용), 검색 품질 필요 시 true
    ENABLE_QUERY_HYDE: bool = False
    # true: 유사도·어휘 겹침 충족 시 답변가능성 LLM 생략(요청당 1회 절감)
    ENABLE_FAST_ANSWERABILITY: bool = True
    # 골든 정확도: 어휘만 겹치고 주제가 다른 오검색에서 빠른 통과 억제
    FAST_ANSWERABILITY_MIN_OVERLAP: float = 0.22
    # -1: 유사도 기반 생략 비활성화(정확도 우선). 0 이상이면 상위 청크 유사도가 이 값 이상일 때만 생략
    ANSWERABILITY_FAST_PATH_MIN_SIM: float = -1.0
    # Hybrid Search 가중치 (금융 용어 정확도: 키워드 비중 올리면 용어 매칭 강화)
    HYBRID_VECTOR_WEIGHT: float = 0.7
    HYBRID_KEYWORD_WEIGHT: float = 0.3
    # RRF 후 필터: 근거 후보 확보를 위해 기본은 다소 낮게(리콜↑), 리랭크로 정밀화
    HYBRID_SIMILARITY_THRESHOLD: float = 0.20
    ENABLE_TRACING: bool = True     # LangSmith 트레이싱 (API 키 설정 시 동작)
    
    # LangGraph / Agentic RAG
    MAX_AGENT_ITERATIONS: int = 5
    AGENT_TIMEOUT_SECONDS: int = 120
    AGENT_RECURSION_LIMIT: int = 100  # LangGraph ainvoke recursion_limit (50 초과 시 오류 방지)
    # 정보 부족 시 외부 검색 사용 (선택). .env에 키 설정 시 활성화
    TAVILY_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    ENABLE_WEB_SEARCH_WHEN_INSUFFICIENT: bool = True  # True면 키 있을 때만 웹검색 시도
    # Tavily 검색 옵션 (Playground의 Additional fields와 대응)
    TAVILY_SEARCH_DEPTH: str = "advanced"   # basic | advanced (정보 부족 시 더 깊이 검색)
    TAVILY_MAX_RESULTS: int = 5
    TAVILY_SEARCH_TOPIC: str = "finance"    # 금융 RAG 기본값 (에이전트 웹 보강 시 도메인 정렬)
    TAVILY_INCLUDE_ANSWER: str = "none"     # none | true (검색 요약 포함 여부)
    
    # Ragas Evaluation (골든 기본 12문항과 정합)
    RAGAS_TEST_SIZE: int = 12
    # Ragas 메트릭 채점 전용 LLM (비우면 OPENAI_MODEL 사용). 골든 벤치마크 시 .env에 RAGAS_EVAL_MODEL=gpt-4o 권장.
    RAGAS_EVAL_MODEL: str = ""
    
    # Notifications
    SLACK_WEBHOOK_URL: str = ""

    # CORS (프론트 오리진만. 백엔드 URL이 아님. 쉼표 구분, 비우면 CORS_DEFAULT_ORIGINS + 아래 목록)
    # Railway 백엔드는 *.railway.internal 이 아니라 브라우저가 열 수 있는 Vercel 도메인을 허용해야 함.
    CORS_ORIGINS: str = ""
    CORS_DEFAULT_ORIGINS: List[str] = [
        "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
        "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175",
        "https://rag-finance-rho.vercel.app",  # Vercel 프로덕션 프론트엔드
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
