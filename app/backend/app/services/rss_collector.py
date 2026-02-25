"""RSS feed collector service."""
import feedparser
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import DocumentCreate, DocumentStatus


class RSSCollector:
    """Financial Services Commission RSS collector."""
    
    # fid → 수집 문서 category 라벨 (config.FSC_RSS_FIDS와 1:1 매핑 권장)
    RSS_URLS = {
        "0111": "보도자료",
        "0112": "보도설명",
        "0114": "공지사항",
        "0113": "행사/채용안내",
        "0115": "정책자료",
        "0411": "카드뉴스",
    }
    
    def __init__(self):
        self.db = get_db()
    
    def _get_rss_url(self, fid: str) -> str:
        """Generate RSS URL for given fid."""
        return f"{settings.FSC_RSS_BASE}?fid={fid}"
    
    def _generate_hash(self, url: str, title: str, published: str) -> str:
        """Generate unique hash for document."""
        content = f"{url}:{title}:{published}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse RSS date string."""
        from datetime import timezone
        try:
            # Try common RSS date formats
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            # Fallback to feedparser's parsed date
            struct_time = feedparser._parse_date(date_str)
            if struct_time:
                dt = datetime(*struct_time[:6])
                return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
        return datetime.now(timezone.utc)
    
    async def fetch_feed(self, fid: str, base_url: str = None) -> List[Dict[str, Any]]:
        """Fetch and parse RSS feed.
        동일 URL을 호출해도 금융위원회 서버가 최신 N건을 반환하므로, 매 수집 시 새 글이 있으면 포함됩니다.
        똑같은 것만 호출하는 것이 아니라, 서버 쪽 목록이 일별로 갱신됩니다.
        """
        url = (base_url + f"?fid={fid}") if base_url else self._get_rss_url(fid)
        print(f"Fetching RSS feed from: {url}")
        
        try:
            feed = feedparser.parse(url)
            documents = []
            
            if not feed.entries:
                print(f"No entries found for fid {fid}")
                return []
            
            all_entries = feed.entries
            limit = getattr(settings, "RSS_MAX_ITEMS", 200)
            entries_to_process = all_entries[:limit] if limit else all_entries
            
            print(f"Feed entries total={len(all_entries)}, to process={len(entries_to_process)} (RSS_MAX_ITEMS={limit})")
            
            for entry in entries_to_process:
                # Get published date with multiple fallbacks
                published_str = entry.get("published", "")
                published_at = self._parse_date(published_str)
                
                # Double check to never have None for NOT NULL constraint
                if published_at is None:
                    published_at = datetime.now(timezone.utc)
                
                doc = {
                    "title": entry.get("title", "No Title"),
                    "url": entry.get("link", ""),
                    "published_at": published_at,
                    "summary": entry.get("summary", ""),
                    "category": self.RSS_URLS.get(fid, "unknown"),
                    "fid": fid
                }
                
                if not doc["url"]:
                    continue
                    
                doc["hash"] = self._generate_hash(
                    doc["url"], doc["title"], published_str or str(published_at)
                )
                documents.append(doc)
            
            print(f"Parsed {len(documents)} documents for fid {fid}")
            return documents
            
        except Exception as e:
            print(f"Error fetching RSS feed {fid}: {e}")
            return []
    
    async def collect_all(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """Collect all RSS feeds with optimized parallel processing."""
        import asyncio
        from app.services.job_tracker import job_tracker
        
        results = {
            "total_new": 0,
            "total_existing": 0,
            "errors": [],
            "feeds": {}
        }
        
        if job_id:
            job_tracker.update_job(job_id, status="running", stage="초기화", progress=5, message="소스 정보 조회 중...")
        
        # Pre-fetch source records + 누락된 fid 자동 보강 (config·RSS_URLS와 sources 정합성)
        try:
            sources_res = self.db.table("sources").select("source_id, fid, base_url, active").execute()
            fid_map = {s["fid"]: s for s in (sources_res.data or [])}
            fids = settings.FSC_RSS_FIDS
            for fid in fids:
                if fid not in fid_map:
                    name = self.RSS_URLS.get(fid, f"금융위원회({fid})")
                    try:
                        self.db.table("sources").insert({
                            "name": name,
                            "type": "rss",
                            "base_url": settings.FSC_RSS_BASE,
                            "fid": fid,
                            "active": True,
                        }).execute()
                        print(f"Created source for fid={fid} ({name})")
                    except Exception as ins_e:
                        print(f"Failed to create source for fid={fid}: {ins_e}")
            # 재조회하여 새로 넣은 행 반영
            sources_res = self.db.table("sources").select("source_id, fid, base_url, active").execute()
            fid_map = {s["fid"]: s for s in (sources_res.data or [])}
            print(f"Found sources in DB: {list(fid_map.keys())}")
        except Exception as e:
            print(f"Error fetching sources: {e}")
            if job_id:
                job_tracker.update_job(job_id, status="error", message=f"소스 조회 실패: {str(e)}")
            return {"error": str(e)}
        
        # Step 1: Parallel fetch all feeds (병렬 수집으로 속도 향상)
        if job_id:
            job_tracker.update_job(job_id, stage="RSS 수집", progress=10, message="피드 데이터 수집 중...")
        
        async def fetch_with_source(fid: str):
            source_rec = fid_map.get(fid)
            if not source_rec or not source_rec.get("active", True):
                return fid, [], source_rec
            base_url = source_rec.get("base_url")
            docs = await self.fetch_feed(fid, base_url)
            return fid, docs, source_rec
        
        # Parallel fetch all feeds
        fetch_tasks = [fetch_with_source(fid) for fid in fids]
        fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        if job_id:
            job_tracker.update_job(job_id, stage="중복 체크", progress=40, message="기존 문서와 비교 중...")
        
        # Step 2: Collect all hashes for batch duplicate check
        all_docs_by_fid = {}
        all_hashes = []
        
        for result in fetch_results:
            if isinstance(result, Exception):
                continue
            fid, docs, source_rec = result
            if docs and source_rec:
                all_docs_by_fid[fid] = {"docs": docs, "source": source_rec}
                all_hashes.extend([d["hash"] for d in docs])
        
        # Batch check existing hashes (한 번의 쿼리로 중복 체크)
        # hash = url+title+published 기준으로 기존 DB에 있으면 스킵 → 신규만 추가됨
        existing_hashes = set()
        if all_hashes:
            try:
                # Check in batches of 100 to avoid query limits
                for i in range(0, len(all_hashes), 100):
                    batch = all_hashes[i:i+100]
                    existing_res = self.db.table("documents").select("hash").in_("hash", batch).execute()
                    if existing_res.data:
                        existing_hashes.update(d["hash"] for d in existing_res.data)
            except Exception as e:
                print(f"Error batch checking hashes: {e}")
        
        if job_id:
            job_tracker.update_job(job_id, stage="저장 중", progress=60, message="신규 문서 저장 중...")
        
        # Step 3: Insert new documents in batches
        total_fids = len(all_docs_by_fid)
        processed = 0
        
        for fid, data in all_docs_by_fid.items():
            docs = data["docs"]
            source_rec = data["source"]
            source_uuid = source_rec["source_id"]
            
            feed_result = {"fetched": len(docs), "new": 0, "existing": 0}
            new_docs_batch = []
            
            for doc in docs:
                if doc["hash"] in existing_hashes:
                    feed_result["existing"] += 1
                    results["total_existing"] += 1
                    continue
                
                doc_create = DocumentCreate(
                    source_id=source_uuid,
                    title=doc["title"],
                    published_at=doc["published_at"],
                    url=doc["url"],
                    category=doc["category"],
                    hash=doc["hash"]
                )
                new_docs_batch.append(doc_create.model_dump(mode='json'))
            
            # Batch upsert new documents
            if new_docs_batch:
                try:
                    self.db.table("documents").upsert(
                        new_docs_batch,
                        on_conflict="url"
                    ).execute()
                    feed_result["new"] = len(new_docs_batch)
                    results["total_new"] += len(new_docs_batch)
                except Exception as ins_err:
                    print(f"Error batch inserting for fid {fid}: {ins_err}")
                    # Fallback to individual inserts
                    for payload in new_docs_batch:
                        try:
                            self.db.table("documents").upsert(payload, on_conflict="url").execute()
                            feed_result["new"] += 1
                            results["total_new"] += 1
                        except Exception:
                            pass
            
            results["feeds"][fid] = feed_result
            processed += 1
            
            if job_id:
                progress = 60 + int((processed / total_fids) * 35)
                job_tracker.update_job(job_id, progress=progress, message=f"{fid} 처리 완료 ({feed_result['new']}건 신규)")
        
        if job_id:
            final_status = "success_collect" if results["total_new"] > 0 else "no_change"
            msg = f"완료: 신규 {results['total_new']}건 수집" if results["total_new"] > 0 else "신규 문서 없음"
            job_tracker.update_job(job_id, status=final_status, stage="완료", progress=100, count=results["total_new"], message=msg)
            
        return results
    
    async def get_recent_documents(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get documents from last N hours."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        result = self.db.table("documents").select("*").gte(
            "ingested_at", since.isoformat()
        ).order("ingested_at", desc=True).execute()
        
        return result.data or []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics. 총 문서 수는 limit 없이 전체 테이블 기준입니다."""
        # Total documents (전체 행 수, 제한 없음)
        total = self.db.table("documents").select("*", count="exact").execute()
        
        # Last 24 hours
        since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_24h = self.db.table("documents").select("*", count="exact").gte(
            "ingested_at", since_24h.isoformat()
        ).execute()

        # Last 7 days (수집/저장된 건수 — 추가 여부 확인용)
        since_7d = datetime.now(timezone.utc) - timedelta(days=7)
        recent_7d = self.db.table("documents").select("*", count="exact").gte(
            "ingested_at", since_7d.isoformat()
        ).execute()
        week_data = self.db.table("documents").select("status").gte(
            "ingested_at", since_7d.isoformat()
        ).execute()

        total_week = len(week_data.data) if week_data.data else 0
        failed_week = sum(1 for d in week_data.data if d.get("status") == "failed") if week_data.data else 0
        success_rate = (total_week - failed_week) / total_week * 100 if total_week > 0 else 100

        # Parsing failures in last 24h
        failures_24h = self.db.table("documents").select("*", count="exact").eq(
            "status", "failed"
        ).gte("ingested_at", since_24h.isoformat()).execute()

        return {
            "total_documents": (total.count if hasattr(total, 'count') else 0) or 0,
            "documents_24h": (recent_24h.count if hasattr(recent_24h, 'count') else 0) or 0,
            "documents_7d": (recent_7d.count if hasattr(recent_7d, 'count') else 0) or 0,
            "success_rate_7d": float(success_rate),
            "parsing_failures_24h": (failures_24h.count if hasattr(failures_24h, 'count') else 0) or 0,
        }
