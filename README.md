# FSC Policy RAG System

금융위원회 정책 문서 기반 RAG(Retrieval-Augmented Generation) 시스템

## 🎯 프로젝트 개요

감독·정책 변화는 상품 운영, 낸부통제, 민원/분쟁, 자본·리스크 관리에 즉시 반영되어야 하나 문서량이 방대해 대응 지연이 발생합니다. 본 연구는 **최신 정책 문서를 자동 수집(RSS)**하고, **업권별 영향·준수 체크 항목을 구조화**하여 대응 시간을 단축하는 시스템을 제안합니다.

### 데이터 소스
- **금융위원회 RSS**: 볏  도자료(fid=0111), 볏  도설명(0112), 공지(0114), 카드뉴스(0411)
- **공공데이터포털**: 금융위원회_볏  도자료 파일데이터

## 🏗️ 시스템 아키텍처

### 백엔드 (FastAPI)
```
backend/
├── app/
│   ├── api/routes.py          # API 엔드포인트
│   ├── core/
│   │   ├── config.py          # 설정
│   │   ├── database.py        # Supabase 연결
│   │   └── redis.py           # Redis 캐시
│   ├── models/schemas.py      # Pydantic 모델
│   └── services/
│       ├── rss_collector.py   # RSS 수집
│       ├── rag_service.py     # RAG 파이프라인
│       ├── industry_classifier.py  # 업권 분류
│       ├── topic_detector.py  # 토픽 서지 탐지
│       └── checklist_service.py    # 체크리스트 추출
└── requirements.txt
```

### 프론트엔드 (React + Vite + TypeScript)
```
src/
├── sections/
│   ├── Header.tsx             # 네비게이션
│   ├── MonitorDashboard.tsx   # 화면1: 수집 모니터
│   ├── TopicMap.tsx           # 화면2: 이슈맵/경보
│   ├── IndustryPanel.tsx      # 화면3: 업권 분류
│   ├── RAGQA.tsx              # 화면4: RAG 질의응답
│   ├── ChecklistGenerator.tsx # 화면5: 체크리스트
│   └── QualityDashboard.tsx   # 화면6: 품질 평가
├── types/index.ts             # TypeScript 타입
└── lib/api.ts                 # API 클라이언트
```

## 📊 6개 주요 화면

### 1. 실시간 수집 모니터 (LLM Ops 대시보드)
- RSS 수집 성공/실패 상태
- 신규 문서 수, 인덱스 최신화 시간
- 파싱 오류(HWP/PDF) 로그
- 최근 24시간 신규 문서 리스트

### 2. 이슈맵 + 급부상 경보 (Topic Surge)
- 임베딩 기반 클러스터 버블차트
- 급부상 토픽 Top 5 + Surge Score
- 대표 근거 문서 링크
- 업권별 경보 라우팅

### 3. 업권 영향 분류 (보험/은행/증권)
- 문서별 업권 영향 확률
- 멀티라벨(복수 업권) 지원
- 근거 문단 하이라이트
- LLM + 키워드 하이브리드 분류

### 4. RAG 질의응답 (근거 인용형)
- 하이브리드 검색(BM25 + Vector)
- 리랭커 기반 근거 문단 선별
- 답변 + 근거 문서 카드
- 불확실성 표시 (가드레일)

### 5. 컴플라이언스 체크리스트 생성기
- 자동 추출: [해야 할 일], [대상], [기한], [제재]
- 근거 chunk_id 연결
- 다운로드: CSV/Markdown/JSON
- 신뢰도 스코어 표시

### 6. 품질/리스크 평가 (모델 거버넌스)
- 환각률, 근거일치율 추적
- 평균 응답 시간, 인용 정확도
- 고위험 답변 샘플링 리뷰 큐
- 시스템 상태 모니터링

## 🔬 RAG 아키텍처 상세

### (A) 수집·정제 (LLM Ops)
```
스케줄러 → RSS pull → 본문/첨부 수집 → 문서 변환 → 청킹 → 메타데이터 저장 → 임베딩 → 벡터DB 인덱싱
```

### (B) Retrieval: 하이브리드 검색 + 리랭킹
1. **1차 검색**: BM25(정확한 용어) + 벡터검색(유사 의미) 결합
2. **리랭커(2차)**: "질문-문단" 매칭 점수로 Top-k 재정렬

### (C) Generation: 근거강제 응답 템플릿
- 요약(3줄) → 업권 영향 → 체크리스트 → 근거 인용 → 불확실성 표시
- 근거 없으면 '모른다'로 종료

### (D) Guardrails (환각 억제 4종)
1. **Citation-required**: 모든 주장에 근거 문단 ID 필수
2. **Answerability check**: Top-k에 답 없으면 "근거 부족"
3. **Policy-lens**: 과도확신 문장 탐지 ("확정", "반드시")
4. **Self-consistency**: 동일 질문 2회 생성 후 충돌 시 재검토

## 📈 연구 질문 (RQ) + 가설 (H)

| RQ | 질문 | 가설 |
|---|---|---|
| RQ1 | 업권별 영향 분류가 가능한가? | LLM 약지도 + 소형 분류기 > 규칙기반 키워드 |
| RQ2 | 급부상 토픽이 정책 이벤트를 조기 포착하는가? | 임베딩 클러스터링 + Surge Score > 빈도 기반 |
| RQ3 | 컴플라이언스 체크 항목 추출이 실무적으로 유용한가? | RAG → LLM 구조화 > LLM 단독 요약 |
| RQ4 | RAG 품질(근거/환각/최신성)이 개선되는가? | 최신 수집 + 인덱스 자동갱신 > 정적 인덱스 |

## 🛠️ 기술 스택

### Backend
- **FastAPI**: 고성능 ASGI 웹 프레임워크
- **Supabase (PostgreSQL)**: 데이터베이스 + pgvector
- **Redis**: 캐싱 및 세션 관리
- **OpenAI GPT-4**: LLM 및 임베딩
- **LangChain**: RAG 파이프라인

### Frontend
- **React 18**: UI 라이브러리
- **TypeScript**: 타입 안정성
- **Vite**: 빌드 도구
- **Tailwind CSS**: 스타일링
- **shadcn/ui**: 컴포넌트 라이브러리
- **Recharts**: 차트/시각화

## 🚀 실행 방법

### 백엔드
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# .env 파일 설정
cp .env.example .env
# SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY 설정

uvicorn app.main:app --reload
```

### 프론트엔드
```bash
cd app
npm install
npm run dev
```

### 환경 변수
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=sk-...

# Redis
REDIS_URL=redis://localhost:6379/0
```

## 📋 데이터베이스 스키마

### 핵심 테이블
- `sources`: RSS 소스 정보
- `documents`: 수집된 문서
- `chunks`: 문서 청크
- `embeddings`: 벡터 임베딩
- `industry_labels`: 업권 분류 결과
- `topics`: 토픽 클러스터
- `alerts`: 급부상 경보
- `checklists`: 체크리스트

## 📊 평가 지표

| 지표 | 설명 | 목표값 |
|---|---|---|
| Groundedness | 근거일치율 | > 90% |
| Hallucination Rate | 환각률 | < 5% |
| Industry F1 | 업권분류 F1 | > 0.85 |
| Checklist Missing | 필수항목 누락률 | < 10% |
| Topic Precision@k | 신규토픽 탐지 정확도 | > 0.8 |

## 🎓 공모전 제출용 제목 추천

1. "금융정책·감독 볏  도자료 기반 RAG 이슈맵 구축과 업권(보험/은행/증권) 영향도·컴플라이언스 체크 자동화"

2. "RSS 기반 금융정책 변화탐지(Topic Surge)와 근거인용형 RAG 요약을 결합한 업권별 규제 리스크 조기경보 시스템"

3. "감독기관 볏  도자료로부터 '업무영향-준수항목'을 추출하는 LLM+딥러닝 파이프라인: RAG 가드레일과 평가셋 구축을 중심으로"

## 📄 라이선스

MIT License

## 👥 팀 정보

- 개발 기간: 7주
- 스택: Python + FastAPI + Vite + Redis + Supabase + OpenAI
