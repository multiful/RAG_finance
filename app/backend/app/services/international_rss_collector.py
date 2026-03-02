"""
국제기구 RSS 수집기 (FSB, BIS, IMF 등).
금융위원회 RSS와 동일하게 documents/sources 테이블에 저장 → 기존 RAG·파이프라인 그대로 사용.
Gap Map GI 국제 데이터 출처로 활용 가능.
"""
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import feedparser

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import DocumentCreate


class InternationalRSSCollector:
    """FSB·BIS 등 국제기구 RSS 피드 수집. URL 직접 지정 (금융위 fid 방식과 별도)."""

    def _generate_hash(self, url: str, title: str, published: str) -> str:
        content = f"{url}:{title}:{published}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        try:
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            struct_time = feedparser._parse_date(date_str)
            if struct_time:
                dt = datetime(*struct_time[:6])
                return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
        return datetime.now(timezone.utc)

    async def fetch_feed(self, feed_config: Dict[str, str]) -> List[Dict[str, Any]]:
        """단일 피드 URL로 수집. feed_config = {fid, name, url}."""
        url = feed_config.get("url", "").strip()
        fid = feed_config.get("fid", "intl")
        name = feed_config.get("name", fid)
        if not url:
            return []

        try:
            # feedparser.parse는 동기; 실행기에서 블로킹 방지를 위해 run_in_executor 사용
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, lambda: feedparser.parse(url))
        except Exception as e:
            print(f"[InternationalRSS] fetch error {fid} {url}: {e}")
            return []

        documents = []
        if not feed.entries:
            return []

        limit = getattr(settings, "RSS_MAX_ITEMS", 500)
        entries = feed.entries[:limit] if limit else feed.entries

        for entry in entries:
            published_str = entry.get("published", "")
            published_at = self._parse_date(published_str) or datetime.now(timezone.utc)
            link = entry.get("link", "")
            if not link:
                continue
            title = entry.get("title", "No Title")
            doc = {
                "title": title,
                "url": link,
                "published_at": published_at,
                "summary": entry.get("summary", ""),
                "category": name,
                "fid": fid,
                "hash": self._generate_hash(link, title, published_str or str(published_at)),
            }
            documents.append(doc)
        return documents

    async def collect_all(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """설정된 국제기구 RSS 전부 수집. 소스 없으면 생성, 문서는 url 기준 중복 제거 후 INSERT."""
        from app.services.job_tracker import job_tracker

        feeds = getattr(settings, "INTERNATIONAL_RSS_FEEDS", []) or []
        if not feeds:
            return {"total_new": 0, "total_existing": 0, "errors": [], "feeds": {}}

        db = get_db()
        results = {"total_new": 0, "total_existing": 0, "errors": [], "feeds": {}}

        if job_id:
            job_tracker.update_job(job_id, stage="국제기구 RSS", progress=5, message="소스 확인 중...")

        # 1) 소스 레코드 확보 (fid 기준)
        fid_to_source: Dict[str, dict] = {}
        try:
            existing = db.table("sources").select("source_id, fid, base_url, active").execute()
            for s in (existing.data or []):
                fid_to_source[s["fid"]] = s
            for fc in feeds:
                fid = fc.get("fid")
                if not fid or fid in fid_to_source:
                    continue
                name = fc.get("name", fid)
                url = fc.get("url", "")
                try:
                    db.table("sources").insert({
                        "name": name,
                        "type": "rss",
                        "base_url": url,
                        "fid": fid,
                        "active": True,
                    }).execute()
                    # 재조회로 source_id 획득
                    r = db.table("sources").select("source_id, fid, base_url").eq("fid", fid).execute()
                    if r.data:
                        fid_to_source[fid] = r.data[0]
                except Exception as e:
                    print(f"[InternationalRSS] source insert {fid}: {e}")
        except Exception as e:
            if job_id:
                job_tracker.update_job(job_id, status="error", message=f"소스 조회 실패: {e}")
            return {"error": str(e), **results}

        # 2) 병렬로 피드 수집
        async def fetch_one(fc: Dict[str, str]):
            return fc.get("fid"), await self.fetch_feed(fc)

        fetch_tasks = [fetch_one(fc) for fc in feeds]
        fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        all_docs: List[tuple] = []  # (fid, doc)
        for r in fetch_results:
            if isinstance(r, Exception):
                continue
            fid, docs = r
            for d in docs:
                all_docs.append((fid, d))

        if job_id:
            job_tracker.update_job(job_id, stage="국제기구 RSS", progress=40, message="중복 체크 중...")

        # 3) 기존 hash 일괄 조회
        hashes = [d["hash"] for _, d in all_docs]
        existing_hashes = set()
        for i in range(0, len(hashes), 100):
            batch = hashes[i : i + 100]
            res = db.table("documents").select("hash").in_("hash", batch).execute()
            if res.data:
                existing_hashes.update(x["hash"] for x in res.data)

        # 4) 신규만 INSERT (source_id 매핑)
        for fid, doc in all_docs:
            if doc["hash"] in existing_hashes:
                results["total_existing"] += 1
                results["feeds"][fid] = results["feeds"].get(fid, {"fetched": 0, "new": 0, "existing": 0})
                results["feeds"][fid]["existing"] = results["feeds"][fid].get("existing", 0) + 1
                continue

            src = fid_to_source.get(fid)
            if not src or not src.get("active", True):
                continue

            try:
                payload = DocumentCreate(
                    source_id=src["source_id"],
                    title=doc["title"],
                    published_at=doc["published_at"],
                    url=doc["url"],
                    category=doc["category"],
                    hash=doc["hash"],
                ).model_dump(mode="json")
                db.table("documents").upsert(payload, on_conflict="url").execute()
                results["total_new"] += 1
                existing_hashes.add(doc["hash"])
                results["feeds"][fid] = results["feeds"].get(fid, {"fetched": 0, "new": 0, "existing": 0})
                results["feeds"][fid]["new"] = results["feeds"][fid].get("new", 0) + 1
            except Exception as e:
                results["errors"].append({"fid": fid, "url": doc["url"], "error": str(e)})

        from collections import Counter
        fetched_per_fid = Counter(fid for fid, _ in all_docs)
        for fid in set(fetched_per_fid) | set(results["feeds"].keys()):
            results["feeds"].setdefault(fid, {"fetched": 0, "new": 0, "existing": 0})
            results["feeds"][fid]["fetched"] = fetched_per_fid.get(fid, 0)

        if job_id:
            msg = f"국제기구 수집 완료: 신규 {results['total_new']}건"
            job_tracker.update_job(job_id, stage="완료", progress=100, message=msg)
        return results


# 싱글톤 (routes/scheduler에서 사용)
international_rss_collector = InternationalRSSCollector()
