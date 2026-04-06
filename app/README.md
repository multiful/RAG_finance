# app/README.md — FSC Policy RAG 프론트엔드

> **파일명**: app/README.md  
> **최종 수정일**: 2026-04-07  
> **문서 해시**: _(루트 스크립트는 `*.md`만 처리 — 필요 시 동일 규칙으로 수동 해시)_  
> **문서 역할**: Vite+React UI 진입 안내  
> **문서 우선순위**: (루트 README.md 보조)  
> **연관 문서**: ../README.md, ../DIRECTORY_SPEC.md, ../RUN.md  
> **참조 규칙**: 실행 포트·프록시 변경 시 루트 README·RUN.md를 함께 갱신한다.

---

## 실행

```bash
cd app
npm install
npm run dev
```

기본 `http://localhost:5173` — API는 Vite 프록시로 백엔드 `8001`을 사용한다.

## 스택

React 18, TypeScript, Vite, Tailwind, React Router. 상세 라우트는 `src/App.tsx` 참고.
