#!/usr/bin/env bash
# Render 빌드: scikit-learn==1.4.1을 요구하는 하위 의존성 때문에 실패하는 문제 회피.
# 1) scikit-learn 1.4.2 선설치 2) 제약 적용 후 requirements 설치 (동일 디렉터리에서 실행)
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
pip install "scikit-learn==1.4.2"
export PIP_CONSTRAINT="$SCRIPT_DIR/constraints.txt"
pip install -r requirements.txt
