"""
진짜 데이터 수집: 금융위원회(FSC) + 국제기구(FSB, BIS) RSS에서 실제 공문을 가져와 DB에 저장합니다.
Redis 없이 실행 가능 (job_id=None).
피드당 건수 제한: .env의 RSS_MAX_ITEMS (기본 500, 0이면 제한 없음).

실행 방법 (app/backend 에서):
  pip install httpx pydantic-settings pydantic python-dotenv supabase feedparser  # 필요 시
  python -m scripts.run_real_collection
"""
import asyncio
import os
import sys

# backend 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.rss_collector import RSSCollector


async def main():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        print(" .env에 SUPABASE_URL, SUPABASE_SERVICE_KEY 를 설정해 주세요.")
        sys.exit(1)

    total_new = 0
    total_existing = 0

    # 1) 금융위원회(FSC) RSS
    print("금융위원회(FSC) RSS 수집 시작...")
    collector = RSSCollector()
    result = await collector.collect_all(job_id=None)
    if "error" in result:
        print("FSC 수집 실패:", result["error"])
    else:
        total_new += result.get("total_new", 0)
        total_existing += result.get("total_existing", 0)
        print(f"  FSC 완료: 신규 {result.get('total_new', 0)}건, 기존 유지 {result.get('total_existing', 0)}건")
        for fid, feed_result in result.get("feeds", {}).items():
            print(f"    fid={fid}: 신규 {feed_result.get('new', 0)}건")

    # 2) 국제기구(FSB, BIS 등) RSS — 대조용
    if getattr(settings, "ENABLE_INTERNATIONAL_RSS", True):
        print("국제기구(FSB, BIS 등) RSS 수집 시작...")
        try:
            from app.services.international_rss_collector import international_rss_collector
            intl = await international_rss_collector.collect_all(job_id=None)
            if "error" in intl:
                print("  국제 수집 실패:", intl["error"])
            else:
                total_new += intl.get("total_new", 0)
                total_existing += intl.get("total_existing", 0)
                print(f"  국제 완료: 신규 {intl.get('total_new', 0)}건, 기존 유지 {intl.get('total_existing', 0)}건")
                for fid, feed_result in intl.get("feeds", {}).items():
                    print(f"    {fid}: 신규 {feed_result.get('new', 0)}건")
        except Exception as e:
            print("  국제 수집 예외:", e)
    else:
        print("ENABLE_INTERNATIONAL_RSS 비활성화로 국제 수집 생략.")

    print(f"총합: 신규 {total_new}건, 기존 유지 {total_existing}건")
    return {"total_new": total_new, "total_existing": total_existing}


if __name__ == "__main__":
    asyncio.run(main())
