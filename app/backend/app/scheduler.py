"""경량 일일 수집 스케줄러. 외부 cron/디펜던시 없이 asyncio만 사용 (디스크/용량 절약)."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # Python 3.8: 환경변수 COLLECTION_TZ 무시, 서버 로컬 시각 사용

from app.core.config import settings

logger = logging.getLogger(__name__)


def _next_run_utc(hour: int, tz_name: str) -> datetime:
    if ZoneInfo is not None:
        z = ZoneInfo(tz_name)
        now = datetime.now(z)
        next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    else:
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    if next_run <= now:
        next_run += timedelta(days=1)
    if getattr(next_run, "tzinfo", None) is None:
        next_run = next_run.replace(tzinfo=timezone.utc)
    return next_run.astimezone(timezone.utc) if hasattr(next_run, "astimezone") else next_run


async def _run_collection():
    """FSC RSS + FSS + (옵션) 국제기구 RSS 수집 (routes._run_all_collection와 동일 로직)."""
    from app.services.rss_collector import RSSCollector
    from app.services.fss_scraper import fss_scraper
    from app.services.job_tracker import job_tracker

    collector = RSSCollector()
    job_id = job_tracker.create_job()
    try:
        await collector.collect_all(job_id=job_id)
        try:
            await fss_scraper.collect_all()
        except Exception as e:
            logger.warning("FSS 수집 실패: %s", e)
        if getattr(settings, "ENABLE_INTERNATIONAL_RSS", False):
            try:
                from app.services.international_rss_collector import international_rss_collector
                await international_rss_collector.collect_all(job_id=job_id)
            except Exception as e:
                logger.warning("국제기구 RSS 수집 실패: %s", e)
        job = job_tracker.get_job(job_id)
        if job and job.get("status") in ("running", None):
            job_tracker.update_job(
                job_id,
                status="success_collect" if (job.get("new_documents_count") or 0) > 0 else "no_change",
                stage="완료",
                progress=100,
            )
    except Exception as e:
        logger.exception("일일 수집 오류: %s", e)
        job_tracker.update_job(job_id, status="error", message=str(e))


async def run_daily_collection_loop():
    """매일 지정 시각(기본 03:00 KST)에 수집 1회 실행."""
    if not getattr(settings, "ENABLE_DAILY_COLLECTION", True):
        return
    hour = getattr(settings, "COLLECTION_AT_HOUR", 3)
    tz_name = getattr(settings, "COLLECTION_TZ", "Asia/Seoul")
    while True:
        try:
            next_utc = _next_run_utc(hour, tz_name)
            delay = (next_utc - datetime.now(timezone.utc)).total_seconds()
            if delay < 0:
                delay = 0
            logger.info("다음 자동 수집: %s (%.0f초 후)", next_utc.isoformat(), delay)
            await asyncio.sleep(delay)
            await _run_collection()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("스케줄 루프 오류: %s", e)
            await asyncio.sleep(3600)
