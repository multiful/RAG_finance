import type { IndustryImpactItem } from './api';

/** API·표시용: 영향 점수를 0~100 구간으로 고정 */
export function clampScore100(n: number | null | undefined): number {
  if (n == null || Number.isNaN(Number(n))) return 0;
  return Math.min(100, Math.max(0, Number(n)));
}

/**
 * 업권별 다차원 레이더: 모든 축을 0~100으로 맞춤.
 * - 문서 수·알림 수·고위험: 기간 내 업권 간 최댓값 대비 비율(%)
 * - 영향 점수: 백엔드에서 산출한 절대 점수(0~100)
 */
export function buildMultiMetricRadarData(
  items: IndustryImpactItem[]
): Array<Record<string, string | number>> {
  if (!items.length) return [];

  const maxDoc = Math.max(...items.map((i) => i.document_count), 0);
  const maxAlert = Math.max(...items.map((i) => i.alert_count), 0);
  const maxHigh = Math.max(...items.map((i) => i.high_severity_count), 0);

  const pct = (value: number, max: number) =>
    max > 0 ? clampScore100((100 * value) / max) : 0;

  const row = (metric: string, getter: (i: IndustryImpactItem) => number) => {
    const r: Record<string, string | number> = { metric };
    for (const i of items) {
      r[i.industry_label] = clampScore100(getter(i));
    }
    return r;
  };

  return [
    row('문서 수', (i) => pct(i.document_count, maxDoc)),
    row('알림 수', (i) => pct(i.alert_count, maxAlert)),
    row('영향 점수', (i) => i.impact_score),
    row('고위험', (i) => pct(i.high_severity_count, maxHigh)),
  ];
}
