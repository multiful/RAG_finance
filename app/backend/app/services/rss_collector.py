"""RSS feed collector service."""
import feedparser
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import DocumentCreate, DocumentStatus


class RSSCollector:
    """Financial Services Commission RSS collector."""
    
    RSS_URLS = {
        "0111": "볏  도자료",
        "0112": "볏  도설명",
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
        try:
            # Try common RSS date formats
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            # Fallback to feedparser's parsed date
            struct_time = feedparser._parse_date(date_str)
            if struct_time:
                return datetime(*struct_time[:6])
        except Exception:
            pass
        return datetime.now()
    
    async def fetch_feed(self, fid: str) -> List[Dict[str, Any]]:
        """Fetch and parse RSS feed."""
        url = self._get_rss_url(fid)
        
        try:
            feed = feedparser.parse(url)
            documents = []
            
            for entry in feed.entries:
                doc = {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "published_at": self._parse_date(entry.get("published", "")),
                    "summary": entry.get("summary", ""),
                    "category": self.RSS_URLS.get(fid, "unknown"),
                    "fid": fid
                }
                doc["hash"] = self._generate_hash(
                    doc["url"], doc["title"], entry.get("published", "")
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"Error fetching RSS feed {fid}: {e}")
            return []
    
    async def collect_all(self) -> Dict[str, Any]:
        """Collect all RSS feeds."""
        results = {
            "total_new": 0,
            "total_existing": 0,
            "errors": [],
            "feeds": {}
        }
        
        for fid in settings.FSC_RSS_FIDS:
            try:
                documents = await self.fetch_feed(fid)
                feed_result = {
                    "fetched": len(documents),
                    "new": 0,
                    "existing": 0
                }
                
                for doc in documents:
                    # Check if document already exists
                    existing = self.db.table("documents").select("document_id").eq(
                        "hash", doc["hash"]
                    ).execute()
                    
                    if existing.data:
                        feed_result["existing"] += 1
                        results["total_existing"] += 1
                        continue
                    
                    # Insert new document
                    doc_create = DocumentCreate(
                        source_id=f"FSC_RSS_{fid}",
                        title=doc["title"],
                        published_at=doc["published_at"],
                        url=doc["url"],
                        category=doc["category"],
                        hash=doc["hash"]
                    )
                    
                    self.db.table("documents").insert(doc_create.model_dump()).execute()
                    feed_result["new"] += 1
                    results["total_new"] += 1
                
                results["feeds"][fid] = feed_result
                
            except Exception as e:
                results["errors"].append({"fid": fid, "error": str(e)})
        
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
        total = self.db.table("documents").select("count", count="exact").execute()
        
        # Last 24 hours
        since_24h = datetime.now() - timedelta(hours=24)
        recent_24h = self.db.table("documents").select("count", count="exact").gte(
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
        failures_24h = self.db.table("documents").select("count", count="exact").eq(
            "status", "failed"
        ).gte("ingested_at", since_24h.isoformat()).execute()
        
        return {
            "total_documents": total.count if hasattr(total, 'count') else 0,
            "documents_24h": recent_24h.count if hasattr(recent_24h, 'count') else 0,
            "success_rate_7d": success_rate,
            "parsing_failures_24h": failures_24h.count if hasattr(failures_24h, 'count') else 0
        }
