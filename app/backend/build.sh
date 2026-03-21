#!/usr/bin/env bash
# Render 빌드: scikit-learn 1.4.2 선설치 후 슬림 + 풀 스택 의존성 설치
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PIP_CONSTRAINT="$SCRIPT_DIR/constraints.txt"
pip install "scikit-learn==1.4.2"
pip install -r requirements.txt
pip install -r requirements-full.txt
