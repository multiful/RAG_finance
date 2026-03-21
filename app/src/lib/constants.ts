/**
 * 앱 공통 상수. 환경 변수로 대체 가능한 항목은 VITE_* 로 주입.
 * @see .env.example (VITE_APP_NAME, VITE_SOURCE_LABEL_ORIGIN 등)
 */
const env = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {} as Record<string, string | undefined>;

/**
 * Vercel 등 HTTPS 페이지에서 `http://*.up.railway.app` / `http://*.onrender.com` 으로 API를 부르면
 * 브라우저가 Mixed Content 로 차단한다. 호스트는 항상 TLS 종료되므로 https 로 고친다.
 * 로컬 `http://127.0.0.1` 은 그대로 둔다.
 */
function normalizePublicApiBaseUrl(raw: string): string {
  const u = raw.trim();
  if (!u.startsWith('http://')) return u;
  const rest = u.slice('http://'.length);
  if (rest.includes('.up.railway.app') || rest.includes('.onrender.com')) {
    return `https://${rest}`;
  }
  return u;
}

/** 앱 이름 (헤더·푸터·출처 표기). 기본: FSC Policy RAG */
export const APP_NAME: string = (env.VITE_APP_NAME ?? 'FSC Policy RAG').trim() || 'FSC Policy RAG';

/** 원문 보기 버튼 등에서 쓰는 출처 짧은 라벨 (예: 금융위원회). */
export const SOURCE_LABEL_ORIGIN: string = (env.VITE_SOURCE_LABEL_ORIGIN ?? '금융위원회').trim() || '금융위원회';

/** 설명문에서 쓰는 출처 풀 라벨 (예: 금융위원회·금융감독원·국제기구(FSB·BIS)). */
export const SOURCE_LABEL_FULL: string = (env.VITE_SOURCE_LABEL_FULL ?? '금융위원회·금융감독원·국제기구(FSB·BIS)').trim() || '금융위원회·금융감독원·국제기구(FSB·BIS)';

/**
 * API 베이스 (FastAPI의 /api/v1 과 동일 경로).
 * - 로컬: 기본 `/api/v1` (vite 프록시 또는 동일 오리진)
 * - Vercel: `VITE_API_BASE_URL` 에 백엔드 **공개 HTTPS URL** 전체 + `/api/v1`
 *   예: `https://xxxx.up.railway.app/api/v1` 또는 기존 Render URL
 * - 주의: `*.railway.internal` 은 Railway 내부망 전용이라 브라우저에서 접근 불가 → 넣지 마세요.
 * - `http://` 로 Railway/Render 공개 URL을 넣지 마세요(혼합 콘텐츠 차단). 반드시 `https://` 또는 상대경로 `/api/v1`.
 */
export const API_BASE_URL: string = normalizePublicApiBaseUrl(
  (env.VITE_API_BASE_URL ?? '/api/v1').trim() || '/api/v1',
);

/** Verifier/출처 표기 블록 제목에 넣을 시스템명. */
export const VERIFIER_SYSTEM_LABEL: string = (env.VITE_VERIFIER_SYSTEM_LABEL ?? APP_NAME).trim() || APP_NAME;

/** 예시 질문 칩 중 출처명이 들어가는 문구. */
export const EXAMPLE_QUESTION_SOURCE_CHIP = `${SOURCE_LABEL_ORIGIN} 스테이블코인 입장은?`;
