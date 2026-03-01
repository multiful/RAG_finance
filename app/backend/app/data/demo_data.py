"""데모/샘플 데이터 — DB 오류 또는 데이터 없음 시 API가 반환할 기본 데이터."""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from app.core.config import settings
from app.models.schemas import (
    DashboardStats,
    CollectionStatus,
    TopicResponse,
)


def get_demo_dashboard_stats() -> DashboardStats:
    """대시보드 통계 데모 데이터."""
    now = datetime.now(timezone.utc)
    collection_status: List[CollectionStatus] = []
    for i, fid in enumerate(settings.FSC_RSS_FIDS[:6]):
        name = {"0111": "보도자료", "0112": "보도설명", "0114": "공지사항", "0113": "행사/채용안내", "0115": "정책자료", "0411": "카드뉴스"}.get(fid, f"금융위원회({fid})")
        n = (i + 1) * 3
        collection_status.append(CollectionStatus(
            source_id=fid,
            source_name=name,
            last_fetch=now,
            new_documents_24h=n,
            total_documents=n * 8,
            success_rate_7d=98.0,
            parsing_failures_24h=0,
        ))
    since = now - timedelta(days=7)
    recent_topics: List[TopicResponse] = [
        TopicResponse(
            topic_id="demo-t1",
            topic_name="스테이블코인 규제 동향",
            topic_summary="국내외 스테이블코인 규제 정책 요약",
            time_window_start=since,
            time_window_end=now,
            document_count=12,
            surge_score=0.85,
            representative_documents=[],
        ),
        TopicResponse(
            topic_id="demo-t2",
            topic_name="금융소비자보호 강화",
            topic_summary="금융소비자 보호법 개정 관련",
            time_window_start=since,
            time_window_end=now,
            document_count=8,
            surge_score=0.62,
            representative_documents=[],
        ),
    ]
    total = sum(c.total_documents for c in collection_status)
    docs_24h = sum(c.new_documents_24h for c in collection_status)
    return DashboardStats(
        total_documents=total or 42,
        documents_24h=docs_24h or 9,
        active_alerts=1,
        high_severity_alerts=0,
        collection_status=collection_status,
        recent_topics=recent_topics,
        quality_metrics=None,
        documents_this_week=total or 42,
        domestic_this_week=24,
        international_this_week=18,
    )


def get_demo_recent_documents() -> List[Dict[str, Any]]:
    """최근 수집 문서 데모 목록."""
    now = datetime.now(timezone.utc)
    base = [
        {"title": "스테이블코인 발행·유통 가이드라인 개정안 시행", "category": "보도자료", "published_at": (now - timedelta(hours=2)).isoformat()},
        {"title": "2024년 금융규제 개혁 로드맵 공지", "category": "공지사항", "published_at": (now - timedelta(hours=5)).isoformat()},
        {"title": "금융소비자보호법 시행령 개정", "category": "정책자료", "published_at": (now - timedelta(hours=8)).isoformat()},
        {"title": "디지털자산 사업자 신고 안내", "category": "보도설명", "published_at": (now - timedelta(hours=12)).isoformat()},
        {"title": "금융감독 정책방향 설명회 개최", "category": "행사/채용안내", "published_at": (now - timedelta(hours=20)).isoformat()},
    ]
    return [
        {
            "document_id": f"demo-doc-{i}",
            "title": d["title"],
            "category": d["category"],
            "published_at": d["published_at"],
            "ingested_at": d["published_at"],
            "url": f"https://www.fsc.go.kr/demo/{i}",
            "status": "completed",
        }
        for i, d in enumerate(base)
    ]


def get_demo_industry_impact(days: int = 90) -> Dict[str, Any]:
    """업권별 영향도 데모 데이터."""
    now = datetime.now(timezone.utc)
    industry_impact = [
        {"industry": "INSURANCE", "industry_label": "보험", "document_count": 18, "alert_count": 0, "high_severity_count": 0, "impact_score": 72.0, "risk_level": "HIGH", "top_keywords": [{"keyword": "보험", "count": 12}, {"keyword": "손해", "count": 8}]},
        {"industry": "BANKING", "industry_label": "은행", "document_count": 14, "alert_count": 0, "high_severity_count": 0, "impact_score": 58.0, "risk_level": "MEDIUM", "top_keywords": [{"keyword": "은행", "count": 10}, {"keyword": "대출", "count": 6}]},
        {"industry": "SECURITIES", "industry_label": "증권", "document_count": 10, "alert_count": 0, "high_severity_count": 0, "impact_score": 45.0, "risk_level": "MEDIUM", "top_keywords": [{"keyword": "증권", "count": 8}, {"keyword": "공시", "count": 4}]},
    ]
    return {
        "period_days": days,
        "analysis_date": now.isoformat(),
        "industry_impact": industry_impact,
        "summary": {
            "most_affected": "보험",
            "total_regulations": 42,
            "total_alerts": 0,
        },
    }


def get_demo_weekly_report() -> Dict[str, Any]:
    """주간 보고서 데모 데이터."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    by_industry = {"INSURANCE": 12, "BANKING": 10, "SECURITIES": 8, "GENERAL": 12}
    return {
        "generated_at": now.isoformat(),
        "period": {"start": week_ago.isoformat(), "end": now.isoformat()},
        "summary": "이번 주 총 42건의 금융 규제 문서가 발표되었습니다. 업권별로는 보험업 12건, 은행업 10건, 증권업 8건이 발표되었습니다.",
        "statistics": {
            "total_documents": 42,
            "domestic_this_week": 24,
            "international_this_week": 18,
            "by_industry": by_industry,
            "urgent_alerts": 0,
            "total_alerts": 0,
        },
        "highlights": [
            {"title": "스테이블코인 발행·유통 가이드라인 개정안 시행", "date": (now - timedelta(days=1)).isoformat(), "category": "보도자료"},
            {"title": "2024년 금융규제 개혁 로드맵 공지", "date": (now - timedelta(days=2)).isoformat(), "category": "공지사항"},
            {"title": "금융소비자보호법 시행령 개정", "date": (now - timedelta(days=3)).isoformat(), "category": "정책자료"},
        ],
        "recommendations": [
            {"priority": "medium", "text": "이번 주 발표된 42건의 규제 내용 파악"},
            {"priority": "low", "text": "다음 주 예정된 규제 시행일 확인"},
        ],
    }


def get_demo_hourly_stats(hours: int = 48) -> Dict[str, Any]:
    """시간대별 수집 통계 데모 데이터."""
    now = datetime.now(timezone.utc)
    hourly = []
    for i in range(min(24, hours)):
        h = (now - timedelta(hours=i)).strftime("%Y-%m-%d %H:00")
        c = (i % 3) + 1
        hourly.append({"hour": h, "count": c, "success": c, "failed": 0})
    hourly.sort(key=lambda x: x["hour"])
    by_source = [{"name": "보도자료", "count": 8}, {"name": "공지사항", "count": 6}, {"name": "정책자료", "count": 5}]
    return {
        "hourly": hourly,
        "by_source": by_source,
        "total": sum(x["count"] for x in hourly),
        "period_hours": hours,
    }
