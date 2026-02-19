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
    
    RSS_URLS = {
        "0111": "보도자료",
        "0112": "보도설명",
        "0114": "공지사항",
        "0411": "카드뉴스"
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
        """Fetch and parse RSS feed."""
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
        """Collect all RSS feeds."""
        from app.services.job_tracker import job_tracker
        
        results = {
            "total_new": 0,
            "total_existing": 0,
            "errors": [],
            "feeds": {}
        }
        
        if job_id:
            job_tracker.update_job(job_id, status="running", stage="collecting", progress=5, message="Fetching source records")
        
        # Pre-fetch source records to map from fid
        try:
            sources_res = self.db.table("sources").select("source_id, fid, base_url, active").execute()
            fid_map = {s["fid"]: s for s in (sources_res.data or [])}
            print(f"Found sources in DB: {list(fid_map.keys())}")
        except Exception as e:
            print(f"Error fetching sources: {e}")
            if job_id:
                job_tracker.update_job(job_id, status="error", message=f"Failed to fetch sources: {str(e)}")
            return {"error": str(e)}
        
        fids = settings.FSC_RSS_FIDS
        for i, fid in enumerate(fids):
            try:
                source_rec = fid_map.get(fid)
                if not source_rec:
                    print(f"No source record found for fid {fid}, skipping")
                    continue
                
                if not source_rec.get("active", True):
                    print(f"Source for fid {fid} is inactive, skipping")
                    continue
                    
                source_uuid = source_rec["source_id"]
                base_url = source_rec.get("base_url")
                
                if job_id:
                    progress = 5 + int((i / len(fids)) * 90)
                    job_tracker.update_job(job_id, stage="collecting", progress=progress, message=f"Processing feed {fid}")
                
                documents = await self.fetch_feed(fid, base_url)
                feed_result = {
                    "fetched": len(documents),
                    "new": 0,
                    "existing": 0
                }
                
                for doc in documents:
                    # Check if document already exists by hash
                    existing = self.db.table("documents").select("document_id").eq(
                        "hash", doc["hash"]
                    ).execute()
                    
                    if existing.data:
                        feed_result["existing"] += 1
                        results["total_existing"] += 1
                        continue
                    
                    # Insert new document with upsert on url
                    doc_create = DocumentCreate(
                        source_id=source_uuid,
                        title=doc["title"],
                        published_at=doc["published_at"],
                        url=doc["url"],
                        category=doc["category"],
                        hash=doc["hash"]
                    )
                    
                    try:
                        # FIX: Convert to JSON-compatible types (str, int, etc)
                        # mode='json' converts datetime to ISO string and Enum to value
                        payload = doc_create.model_dump(mode='json')
                        
                        self.db.table("documents").upsert(
                            payload,
                            on_conflict="url"
                        ).execute()
                        feed_result["new"] += 1
                        results["total_new"] += 1
                    except Exception as ins_err:
                        print(f"Error inserting document {doc['url']}: {ins_err}")
                
                results["feeds"][fid] = feed_result
                
            except Exception as e:
                print(f"Error in collect_all for fid {fid}: {e}")
                results["errors"].append({"fid": fid, "error": str(e)})
        
        if job_id:
            final_status = "success_collect" if results["total_new"] > 0 else "no_change"
            msg = f"Completed: {results['total_new']} new docs" if results["total_new"] > 0 else "No new documents found"
            job_tracker.update_job(job_id, status=final_status, stage="done", progress=100, count=results["total_new"], message=msg)
            
        return results
    
    async def get_recent_documents(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get documents from last N hours."""
        since = datetime.now() - timedelta(hours=hours)
        
        result = self.db.table("documents").select("*").gte(
            "ingested_at", since.isoformat()
        ).order("ingested_at", desc=True).execute()
        
        return result.data or []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        # Total documents
        total = self.db.table("documents").select("*", count="exact").execute()
        
        # Last 24 hours
        since_24h = datetime.now() - timedelta(hours=24)
        recent_24h = self.db.table("documents").select("*", count="exact").gte(
            "ingested_at", since_24h.isoformat()
        ).execute()
        
        # Last 7 days success rate
        since_7d = datetime.now() - timedelta(days=7)
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
            "total_documents": total.count if hasattr(total, 'count') else 0,
            "documents_24h": recent_24h.count if hasattr(recent_24h, 'count') else 0,
            "success_rate_7d": success_rate,
            "parsing_failures_24h": failures_24h.count if hasattr(failures_24h, 'count') else 0
        }
