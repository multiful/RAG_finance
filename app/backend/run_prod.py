"""프로덕션/Railway 진입점: PORT 환경 변수를 정수로 읽어 uvicorn 기동.

Railway·Render 등은 PORT를 주입하며, PowerShell에서는 `$PORT` 문자열이 그대로 넘어가
`Invalid value for '--port': '$PORT'` 오류가 납니다. 이 스크립트는 항상 정수 포트를 씁니다.
"""
import os

import uvicorn


def main() -> None:
    raw = os.environ.get("PORT", "8000")
    try:
        port = int(raw)
    except ValueError:
        port = 8000
    # timeout_keep_alive: 긴 RAG 응답 후에도 연결 재사용. Railway/리버스프록시는 보통 60~120s 요청 한도가 별도.
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
        timeout_keep_alive=120,
    )


if __name__ == "__main__":
    main()
