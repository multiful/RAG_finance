# Railway/컨테이너: 저장소 루트가 아닌 이 디렉터리(app/backend)를 Root Directory로 지정하세요.
# Nixpacks가 Node+Python을 한 이미지에 넣으면 수 GB로 커질 수 있어, API만 이 이미지로 배포하는 것을 권장합니다.
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENABLE_RERANKING=false

# 일부 휠이 없을 때를 대비한 최소 빌드 도구(psycopg2-binary 등은 보통 휠 사용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY constraints.txt requirements.txt ./
RUN pip install --upgrade pip && \
    PIP_CONSTRAINT=/app/constraints.txt pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

# Railway는 PORT 환경 변수 제공
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
