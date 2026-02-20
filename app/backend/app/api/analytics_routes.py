"""Analytics API routes for data analysis and visualization."""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
import logging
import re

from app.services.rss_collector import RSSCollector

router = APIRouter(prefix="/analytics", tags=["analytics"])
rss_collector = RSSCollector()


@router.get("/topic-trends")
async def get_topic_trends(
    months: int = Query(6, ge=1, le=24),
    industry: Optional[str] = None
):
    """
    Get topic/keyword trends over time.
    Returns monthly keyword frequency for trend analysis.
    """
    try:
        db = rss_collector.db
        
        since = datetime.now(timezone.utc) - timedelta(days=months * 30)
        
        query = db.table("documents").select(
            "document_id, title, category, published_at"
        ).gte("published_at", since.isoformat())
        
        if industry:
            query = query.eq("category", industry)
        
        result = query.order("published_at", desc=False).execute()
        
        monthly_keywords: Dict[str, Counter] = defaultdict(Counter)
        
        stop_words = {'및', '등', '의', '에', '를', '을', '이', '가', '은', '는', '로', '으로', '와', '과', '에서', '에게', '부터', '까지', '관련', '관한', '대한', '위한', '따른', '통한', '기관', '금융', '제도', '규정', '법률', '시행'}
        
        for doc in (result.data or []):
            pub_date = datetime.fromisoformat(doc["published_at"].replace("Z", "+00:00"))
            month_key = pub_date.strftime("%Y-%m")
            
            title = doc.get("title", "")
            words = re.findall(r'[가-힣]+', title)
            keywords = [w for w in words if len(w) >= 2 and w not in stop_words]
            
            monthly_keywords[month_key].update(keywords)
        
        trend_data = []
        for month in sorted(monthly_keywords.keys()):
            top_keywords = monthly_keywords[month].most_common(10)
            trend_data.append({
                "month": month,
                "keywords": [{"keyword": k, "count": c} for k, c in top_keywords],
                "total_documents": sum(monthly_keywords[month].values())
            })
        
        all_keywords = Counter()
        for month_counter in monthly_keywords.values():
            all_keywords.update(month_counter)
        
        return {
            "period": f"Last {months} months",
            "monthly_trends": trend_data,
            "top_keywords_overall": [
                {"keyword": k, "count": c} 
                for k, c in all_keywords.most_common(20)
            ],
            "total_documents_analyzed": len(result.data or [])
        }
        
    except Exception as e:
        logging.error(f"Error in get_topic_trends: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industry-impact")
async def get_industry_impact(
    days: int = Query(90, ge=30, le=365)
):
    """
    Analyze regulation impact by industry sector.
    Returns impact scores and distribution.
    """
    try:
        db = rss_collector.db
        
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        docs_result = db.table("documents").select(
            "document_id, title, category, published_at"
        ).gte("published_at", since.isoformat()).execute()
        
        alerts_result = db.table("alerts").select(
            "alert_id, topic_id, severity, industries, urgency_score"
        ).gte("created_at", since.isoformat()).execute()
        
        industry_stats = {
            "INSURANCE": {"doc_count": 0, "alert_count": 0, "high_severity": 0, "keywords": Counter(), "urgency_sum": 0},
            "BANKING": {"doc_count": 0, "alert_count": 0, "high_severity": 0, "keywords": Counter(), "urgency_sum": 0},
            "SECURITIES": {"doc_count": 0, "alert_count": 0, "high_severity": 0, "keywords": Counter(), "urgency_sum": 0},
        }
        
        industry_keywords = {
            "INSURANCE": ["보험", "손해", "생명", "계약자", "보장", "책임준비금", "K-ICS", "지급여력", "보험료", "상품"],
            "BANKING": ["은행", "예금", "대출", "여신", "수신", "BIS", "LCR", "DSR", "LTV", "가계대출", "금리"],
            "SECURITIES": ["증권", "주식", "채권", "파생", "투자", "공매도", "IPO", "공시", "자본시장", "펀드"]
        }
        
        for doc in (docs_result.data or []):
            title = doc.get("title", "")
            
            for industry, keywords in industry_keywords.items():
                if any(kw in title for kw in keywords):
                    industry_stats[industry]["doc_count"] += 1
                    
                    words = re.findall(r'[가-힣]{2,}', title)
                    industry_stats[industry]["keywords"].update(words)
        
        for alert in (alerts_result.data or []):
            industries = alert.get("industries", [])
            severity = alert.get("severity", "low")
            urgency = alert.get("urgency_score", 0) or 0
            
            for industry in industries:
                if industry in industry_stats:
                    industry_stats[industry]["alert_count"] += 1
                    industry_stats[industry]["urgency_sum"] += urgency
                    if severity == "high":
                        industry_stats[industry]["high_severity"] += 1
        
        impact_analysis = []
        max_docs = max(s["doc_count"] for s in industry_stats.values()) or 1
        max_alerts = max(s["alert_count"] for s in industry_stats.values()) or 1
        
        for industry, stats in industry_stats.items():
            doc_score = (stats["doc_count"] / max_docs) * 40
            alert_score = (stats["alert_count"] / max_alerts) * 40
            severity_score = stats["high_severity"] * 5
            urgency_score = min(20, stats["urgency_sum"] / 10) if stats["alert_count"] > 0 else 0
            
            total_impact = min(100, doc_score + alert_score + severity_score + urgency_score)
            
            impact_analysis.append({
                "industry": industry,
                "industry_label": {"INSURANCE": "보험", "BANKING": "은행", "SECURITIES": "증권"}[industry],
                "document_count": stats["doc_count"],
                "alert_count": stats["alert_count"],
                "high_severity_count": stats["high_severity"],
                "impact_score": round(total_impact, 1),
                "risk_level": "HIGH" if total_impact >= 70 else "MEDIUM" if total_impact >= 40 else "LOW",
                "top_keywords": [{"keyword": k, "count": c} for k, c in stats["keywords"].most_common(5)]
            })
        
        impact_analysis.sort(key=lambda x: x["impact_score"], reverse=True)
        
        return {
            "period_days": days,
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "industry_impact": impact_analysis,
            "summary": {
                "most_affected": impact_analysis[0]["industry_label"] if impact_analysis else None,
                "total_regulations": len(docs_result.data or []),
                "total_alerts": len(alerts_result.data or [])
            }
        }
        
    except Exception as e:
        logging.error(f"Error in get_industry_impact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document-stats")
async def get_document_stats(
    days: int = Query(90, ge=7, le=365)
):
    """
    Get document statistics for trend analysis.
    """
    try:
        db = rss_collector.db
        
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        result = db.table("documents").select(
            "document_id, title, category, status, published_at, ingested_at"
        ).gte("published_at", since.isoformat()).execute()
        
        daily_counts: Dict[str, int] = defaultdict(int)
        weekly_counts: Dict[str, int] = defaultdict(int)
        monthly_counts: Dict[str, int] = defaultdict(int)
        category_counts: Counter = Counter()
        status_counts: Counter = Counter()
        
        for doc in (result.data or []):
            pub_date = datetime.fromisoformat(doc["published_at"].replace("Z", "+00:00"))
            
            daily_counts[pub_date.strftime("%Y-%m-%d")] += 1
            
            week_start = pub_date - timedelta(days=pub_date.weekday())
            weekly_counts[week_start.strftime("%Y-%m-%d")] += 1
            
            monthly_counts[pub_date.strftime("%Y-%m")] += 1
            
            category_counts[doc.get("category") or "unknown"] += 1
            status_counts[doc.get("status") or "unknown"] += 1
        
        return {
            "period_days": days,
            "total_documents": len(result.data or []),
            "daily_trend": [
                {"date": d, "count": c} 
                for d, c in sorted(daily_counts.items())
            ],
            "weekly_trend": [
                {"week_start": w, "count": c}
                for w, c in sorted(weekly_counts.items())
            ],
            "monthly_trend": [
                {"month": m, "count": c}
                for m, c in sorted(monthly_counts.items())
            ],
            "by_category": [
                {"category": cat, "count": cnt}
                for cat, cnt in category_counts.most_common()
            ],
            "by_status": [
                {"status": st, "count": cnt}
                for st, cnt in status_counts.most_common()
            ],
            "avg_documents_per_day": round(len(result.data or []) / days, 2)
        }
        
    except Exception as e:
        logging.error(f"Error in get_document_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keyword-cloud")
async def get_keyword_cloud(
    days: int = Query(30, ge=7, le=180),
    limit: int = Query(50, ge=10, le=100)
):
    """
    Get keyword frequency data for word cloud visualization.
    """
    try:
        db = rss_collector.db
        
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        result = db.table("documents").select(
            "title"
        ).gte("published_at", since.isoformat()).execute()
        
        stop_words = {'및', '등', '의', '에', '를', '을', '이', '가', '은', '는', '로', '으로', '와', '과', '에서', '에게', '부터', '까지', '관련', '관한', '대한', '위한', '따른', '통한', '기관', '금융', '제도', '규정', '법률', '시행', '개정', '변경', '안내', '공고', '알림'}
        
        all_keywords = Counter()
        
        for doc in (result.data or []):
            title = doc.get("title", "")
            words = re.findall(r'[가-힣]{2,}', title)
            keywords = [w for w in words if w not in stop_words]
            all_keywords.update(keywords)
        
        max_count = all_keywords.most_common(1)[0][1] if all_keywords else 1
        
        return {
            "period_days": days,
            "keywords": [
                {
                    "text": keyword,
                    "value": count,
                    "normalized": round(count / max_count * 100, 1)
                }
                for keyword, count in all_keywords.most_common(limit)
            ]
        }
        
    except Exception as e:
        logging.error(f"Error in get_keyword_cloud: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regulation-summary")
async def get_regulation_summary():
    """
    Get comprehensive regulation analysis summary.
    """
    try:
        db = rss_collector.db
        now = datetime.now(timezone.utc)
        
        total_result = db.table("documents").select("*", count="exact").execute()
        total_docs = total_result.count if hasattr(total_result, 'count') else 0
        
        week_ago = now - timedelta(days=7)
        week_result = db.table("documents").select("*", count="exact").gte(
            "published_at", week_ago.isoformat()
        ).execute()
        docs_this_week = week_result.count if hasattr(week_result, 'count') else 0
        
        prev_week_start = now - timedelta(days=14)
        prev_week_end = now - timedelta(days=7)
        prev_week_result = db.table("documents").select("*", count="exact").gte(
            "published_at", prev_week_start.isoformat()
        ).lte("published_at", prev_week_end.isoformat()).execute()
        docs_prev_week = prev_week_result.count if hasattr(prev_week_result, 'count') else 0
        
        week_change = ((docs_this_week - docs_prev_week) / docs_prev_week * 100) if docs_prev_week > 0 else 0
        
        alerts_result = db.table("alerts").select("*", count="exact").eq("status", "open").execute()
        active_alerts = alerts_result.count if hasattr(alerts_result, 'count') else 0
        
        high_alerts_result = db.table("alerts").select("*", count="exact").eq(
            "status", "open"
        ).eq("severity", "high").execute()
        high_severity = high_alerts_result.count if hasattr(high_alerts_result, 'count') else 0
        
        return {
            "generated_at": now.isoformat(),
            "overview": {
                "total_regulations": total_docs,
                "regulations_this_week": docs_this_week,
                "week_over_week_change": round(week_change, 1),
                "active_alerts": active_alerts,
                "high_severity_alerts": high_severity
            },
            "insights": [
                {
                    "type": "trend",
                    "message": f"이번 주 {docs_this_week}건의 규제가 발표되었습니다." + (
                        f" (전주 대비 {abs(week_change):.0f}% {'증가' if week_change > 0 else '감소'})" 
                        if docs_prev_week > 0 else ""
                    )
                },
                {
                    "type": "alert",
                    "message": f"현재 {active_alerts}건의 활성 알림이 있으며, 그 중 {high_severity}건이 고위험입니다."
                } if active_alerts > 0 else {
                    "type": "success",
                    "message": "현재 활성화된 긴급 알림이 없습니다."
                }
            ]
        }
        
    except Exception as e:
        logging.error(f"Error in get_regulation_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly-report")
async def get_weekly_report():
    """
    Generate AI-powered weekly regulation report.
    Summarizes key regulatory changes and their implications.
    """
    try:
        db = rss_collector.db
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        
        # Get this week's documents
        docs_result = db.table("documents").select(
            "document_id, title, published_at, category"
        ).gte("published_at", week_ago.isoformat()).order(
            "published_at", desc=True
        ).limit(20).execute()
        
        documents = docs_result.data or []
        
        # Get alerts
        alerts_result = db.table("alerts").select("*").gte(
            "created_at", week_ago.isoformat()
        ).execute()
        alerts = alerts_result.data or []
        
        # Categorize by industry
        by_industry = {"INSURANCE": 0, "BANKING": 0, "SECURITIES": 0, "GENERAL": 0}
        for doc in documents:
            category = doc.get("category", "GENERAL")
            if category in by_industry:
                by_industry[category] += 1
            else:
                by_industry["GENERAL"] += 1
        
        # Generate key highlights
        highlights = []
        for doc in documents[:5]:
            highlights.append({
                "title": doc.get("title", ""),
                "date": doc.get("published_at", ""),
                "category": doc.get("category", "GENERAL")
            })
        
        # Count urgent items
        urgent_count = sum(1 for a in alerts if a.get("severity") == "high")
        
        # Generate summary text
        total_docs = len(documents)
        summary_parts = []
        
        if total_docs > 0:
            summary_parts.append(f"이번 주 총 {total_docs}건의 금융 규제 문서가 발표되었습니다.")
            
            industry_text = []
            if by_industry["INSURANCE"] > 0:
                industry_text.append(f"보험업 {by_industry['INSURANCE']}건")
            if by_industry["BANKING"] > 0:
                industry_text.append(f"은행업 {by_industry['BANKING']}건")
            if by_industry["SECURITIES"] > 0:
                industry_text.append(f"증권업 {by_industry['SECURITIES']}건")
            
            if industry_text:
                summary_parts.append(f"업권별로는 {', '.join(industry_text)}이 발표되었습니다.")
            
            if urgent_count > 0:
                summary_parts.append(f"긴급 대응이 필요한 항목이 {urgent_count}건 있으니 즉시 검토가 필요합니다.")
        else:
            summary_parts.append("이번 주에는 새로운 규제 발표가 없었습니다.")
        
        return {
            "generated_at": now.isoformat(),
            "period": {
                "start": week_ago.isoformat(),
                "end": now.isoformat()
            },
            "summary": " ".join(summary_parts),
            "statistics": {
                "total_documents": total_docs,
                "by_industry": by_industry,
                "urgent_alerts": urgent_count,
                "total_alerts": len(alerts)
            },
            "highlights": highlights,
            "recommendations": [
                {"priority": "high", "text": "고위험 알림 항목 우선 검토"} if urgent_count > 0 else None,
                {"priority": "medium", "text": f"이번 주 발표된 {total_docs}건의 규제 내용 파악"},
                {"priority": "low", "text": "다음 주 예정된 규제 시행일 확인"}
            ]
        }
        
    except Exception as e:
        logging.error(f"Error in get_weekly_report: {str(e)}")
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": "보고서를 생성하는 중 오류가 발생했습니다.",
            "statistics": {"total_documents": 0, "by_industry": {}, "urgent_alerts": 0, "total_alerts": 0},
            "highlights": [],
            "recommendations": []
        }
