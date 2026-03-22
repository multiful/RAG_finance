# Railway/컨테이너: 저장소 루트가 아닌 이 디렉터리(app/backend)를 Root Directory로 지정하세요.
# Nixpacks가 Node+Python을 한 이미지에 넣으면 수 GB로 커질 수 있어, API만 이 이미지로 배포하는 것을 권장합니다.
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# 리랭크(cross-encoder): 기본 설정은 config에서 ENABLE_RERANKING=true.
# 슬림 이미지에 sentence-transformers 없으면 런타임에서 폴백. 필요 시:
#   pip install sentence-transformers scikit-learn
# 또는 Railway Variables: ENABLE_RERANKING=false

# 일부 휠이 없을 때를 대비한 최소 빌드 도구(psycopg2-binary 등은 보통 휠 사용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY constraints.txt requirements.txt ./
# `-c constraints.txt` 대신 pip가 공식 지원하는 PIP_CONSTRAINT (Railway/Nixpacks에서 플래그 생략 시 동일 효과)
RUN pip install --upgrade pip && \
    PIP_CONSTRAINT=/app/constraints.txt pip install -r requirements.txt

COPY run_prod.py ./
COPY app ./app
# scripts/ 는 로컬 도구(골든 평가 등)용이며 .gitignore 대상일 수 있어 이미지에 포함하지 않음.
# API 런타임(run_prod.py)에는 불필요. 스크립트를 컨테이너에 넣으려면 git 추적 후 아래 주석 해제.
# COPY scripts ./scripts

EXPOSE 8000

# PORT는 run_prod.py에서 int로 읽음 (Windows·Railway Nixpacks에서 $PORT 문자열 오류 방지)
CMD ["python", "run_prod.py"]
