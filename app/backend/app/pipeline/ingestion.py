"""Phase A: 데이터 인제스천 파이프라인 (LLM Ops)

Pipeline: Collector → Parser → Chunker → Embedder → Supabase(pgvector)
"""
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

from app.core.config import settings
from app.core.database import get_db
from langchain_openai import OpenAIEmbeddings

_log = logging.getLogger(__name__)


@dataclass
class DocumentIngestionResult:
    """Document ingestion result."""
    document_id: str
    source_id: str
    title: str
    url: str
    status: str  # 'success', 'failed', 'skipped'
    chunks_count: int
    embeddings_count: int
    error_message: Optional[str] = None
    processing_time_ms: int = 0


class RSSCollector:
    """금융위 RSS 수집기 (1일 4회 체크)."""
    
    RSS_URLS = {
        "0111": "보도자료",
        "0112": "보도설명",
        "0114": "공지사항",
        "0411": "카드뉴스"
    }
    
    def __init__(self):
        self.db = get_db()
    
    def _get_rss_url(self, fid: str) -> str:
        return f"{settings.FSC_RSS_BASE}?fid={fid}"
    
    def _generate_hash(self, url: str, title: str, published: str) -> str:
        content = f"{url}:{title}:{published}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    async def fetch_feed(self, fid: str, base_url: str = None) -> List[Dict[str, Any]]:
        """RSS 피드 수집."""
        import feedparser
        
        url = (base_url + f"?fid={fid}") if base_url else self._get_rss_url(fid)
        _log.debug("Fetching RSS feed from: %s", url)
        
        try:
            feed = feedparser.parse(url)
            documents = []
            
            if not feed.entries:
                _log.debug("No entries found for fid %s", fid)
                return []
            
            all_entries = feed.entries
            limit = getattr(settings, "RSS_MAX_ITEMS", 200)
            entries_to_process = all_entries[:limit] if limit else all_entries
            
            _log.debug(
                "Feed entries total=%s, to process=%s (RSS_MAX_ITEMS=%s)",
                len(all_entries),
                len(entries_to_process),
                limit,
            )
            
            for entry in entries_to_process:
                published_str = entry.get("published", "")
                published_at = self._parse_date(published_str)
                
                # Double check for NOT NULL
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
            
            _log.debug("Parsed %s documents for fid %s", len(documents), fid)
            return documents
            
        except Exception as e:
            _log.warning("Error fetching RSS feed %s: %s", fid, e)
            return []
    
    def _parse_date(self, date_str: str) -> datetime:
        import feedparser
        try:
            struct_time = feedparser._parse_date(date_str)
            if struct_time:
                # Convert struct_time to UTC-aware datetime
                dt = datetime(*struct_time[:6])
                return dt.replace(tzinfo=timezone.utc)
        except:
            pass
        return datetime.now(timezone.utc)
    
    async def collect_all(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """모든 RSS 피드 수집."""
        from app.services.job_tracker import job_tracker
        results = {
            "total_new": 0,
            "total_existing": 0,
            "errors": [],
            "documents": []
        }
        
        # Pre-fetch source records to map from fid
        try:
            sources_res = self.db.table("sources").select("source_id, fid, base_url, active").execute()
            fid_map = {s["fid"]: s for s in (sources_res.data or [])}
            _log.debug("Found sources in DB: %s", list(fid_map.keys()))
        except Exception as e:
            _log.warning("Error fetching sources: %s", e)
            return {"error": str(e)}
        
        for fid in settings.FSC_RSS_FIDS:
            if job_id:
                job_tracker.update_job(job_id, stage="collecting", message=f"Fetching feed {fid}...")
            try:
                source_rec = fid_map.get(fid)
                if not source_rec:
                    _log.debug("No source record found for fid %s, skipping", fid)
                    continue

                if not source_rec.get("active", True):
                    _log.debug("Source for fid %s is inactive, skipping", fid)
                    continue
                    
                source_uuid = source_rec["source_id"]
                base_url = source_rec.get("base_url")
                
                documents = await self.fetch_feed(fid, base_url)
                
                for doc in documents:
                    # 중복 체크 (hash)
                    existing = self.db.table("documents").select("document_id").eq(
                        "hash", doc["hash"]
                    ).execute()
                    
                    if existing.data:
                        results["total_existing"] += 1
                        continue
                    
                    # 신규 문서 저장 (upsert on url)
                    from fastapi.encoders import jsonable_encoder
                    doc_data = {
                        "source_id": source_uuid,
                        "title": doc["title"],
                        "published_at": doc["published_at"],
                        "url": doc["url"],
                        "category": doc["category"],
                        "hash": doc["hash"],
                        "status": "ingested",
                        "raw_html": doc.get("summary", "")
                    }
                    
                    try:
                        # Ensure all values in doc_data are JSON serializable (datetime -> str)
                        payload = jsonable_encoder(doc_data)
                        result = self.db.table("documents").upsert(
                            payload,
                            on_conflict="url"
                        ).execute()
                        
                        if result.data:
                            results["total_new"] += 1
                            results["documents"].append(result.data[0])
                    except Exception as ins_err:
                        _log.warning("Error inserting document %s: %s", doc["url"], ins_err)

            except Exception as e:
                _log.warning("Error in collect_all for fid %s: %s", fid, e)
                results["errors"].append({"fid": fid, "error": str(e)})
        
        return results


class LlamaDocumentParser:
    """LlamaParse API로 PDF/HWP → 마크다운 변환."""
    
    def __init__(self):
        self.db = get_db()
    
    async def parse_document(self, document_id: str) -> Dict[str, Any]:
        """문서 파싱 및 청킹."""
        start_time = datetime.now()
        _log.debug("[%s] Starting parsing phase...", document_id)

        try:
            # 문서 조회 (파싱에 필요한 컬럼만 — 대용량 필드 페이로드 축소)
            doc_result = self.db.table("documents").select(
                "document_id, raw_html, title, url, status"
            ).eq("document_id", document_id).execute()

            if not doc_result.data:
                _log.warning("[%s] Error: Document not found", document_id)
                return {"status": "failed", "error": "Document not found"}
            
            doc = doc_result.data[0]
            
            # 첨부 파일 확인
            all_chunks = []
            try:
                files_result = self.db.table("document_files").select("*").eq(
                    "document_id", document_id
                ).execute()
                
                if files_result.data:
                    _log.debug(
                        "[%s] Found %s attachments. Using LlamaParse...",
                        document_id,
                        len(files_result.data),
                    )
                    from app.parsers.llama_parser import parse_and_chunk_document

                    async def _parse_att(f):
                        fp = f.get("file_path")
                        if not fp:
                            return []
                        ft = f.get("file_type", "pdf")
                        return await parse_and_chunk_document(fp, ft)

                    att_results = await asyncio.gather(
                        *[_parse_att(f) for f in files_result.data],
                        return_exceptions=True,
                    )
                    for item in att_results:
                        if isinstance(item, Exception):
                            _log.warning("[%s] attachment parse error: %s", document_id, item)
                            continue
                        all_chunks.extend(item)
                else:
                    _log.debug("[%s] No attachments found.", document_id)
            except Exception as e:
                _log.debug("[%s] document_files check failed, assuming empty: %s", document_id, e)

            if not all_chunks:
                # HTML 본문 직접 파싱
                raw_html = doc.get("raw_html", "")
                if raw_html:
                    _log.debug("[%s] Extracting chunks from raw_html...", document_id)
                    all_chunks = self._parse_html_to_chunks(raw_html, document_id)
            
            if not all_chunks:
                _log.warning("[%s] No content available for parsing.", document_id)
                return {"status": "failed", "error": "No content found"}

            # 청크 저장 — 행 단위 insert N회 대신 배치 insert (RTT·부하 감소)
            chunk_ids: List[str] = []
            insert_batch_size = 200
            for start in range(0, len(all_chunks), insert_batch_size):
                slice_chunks = all_chunks[start : start + insert_batch_size]
                rows = [
                    {
                        "document_id": document_id,
                        "chunk_index": start + i,
                        "chunk_text": c["chunk_text"],
                        "chunk_tokens": c.get("chunk_tokens", 0),
                        "chunking_version": c.get("chunking_version", "llamaparse_v1"),
                        "section_title": c.get("section_title"),
                    }
                    for i, c in enumerate(slice_chunks)
                ]
                result = self.db.table("chunks").insert(rows).execute()
                if result.data:
                    chunk_ids.extend(str(r["chunk_id"]) for r in result.data)
            
            # 문서 상태 업데이트
            self.db.table("documents").update({
                "status": "parsed",
                "parsed_at": datetime.now().isoformat()
            }).eq("document_id", document_id).execute()
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            _log.info("[%s] Successfully parsed into %s chunks.", document_id, len(chunk_ids))
            
            return {
                "status": "success",
                "document_id": document_id,
                "chunks_count": len(chunk_ids),
                "chunk_ids": chunk_ids,
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            self.db.table("documents").update({
                "status": "failed",
                "fail_reason": str(e)
            }).eq("document_id", document_id).execute()
            
            return {"status": "failed", "error": str(e)}
    
    def _parse_html_to_chunks(self, html: str, document_id: str) -> List[Dict]:
        """HTML을 청크로 변환 (재귀 분할 — 단어 단위 고정 윈도 제거)."""
        from bs4 import BeautifulSoup
        from app.chunking.recursive_split import split_text_recursive

        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        pieces = split_text_recursive(text)
        return [
            {
                "chunk_text": p,
                "chunk_tokens": len(p.split()),
                "section_title": None,
                "chunking_version": "recursive_ko_v1",
            }
            for p in pieces
        ]


class ContextualChunker:
    """LangChain 기반 문맥 보존 청킹 + 업권 메타데이터 부착."""
    
    def __init__(self):
        self.db = get_db()
    
    async def enrich_chunks(self, document_id: str) -> Dict[str, Any]:
        """청크에 메타데이터 부착."""
        try:
            # 청크 조회 (메타데이터 부착에 필요한 필드만)
            chunks_result = self.db.table("chunks").select("chunk_id, chunk_text").eq(
                "document_id", document_id
            ).execute()

            if not chunks_result.data:
                return {"status": "failed", "error": "No chunks found"}
            
            # 업권 분류
            industry_keywords = {
                "INSURANCE": ["보험", "생명보험", "손핳보험", "보험료", "보험금"],
                "BANKING": ["은행", "예금", "대출", "금리", "시중은행"],
                "SECURITIES": ["증권", "주식", "채권", "펀드", "투자"]
            }
            
            sem = asyncio.Semaphore(16)

            def _build_metadata(chunk: Dict[str, Any]) -> Dict[str, Any]:
                chunk_text = chunk.get("chunk_text", "").lower()
                industry_tags = []
                for industry, keywords in industry_keywords.items():
                    if any(kw in chunk_text for kw in keywords):
                        industry_tags.append(industry)
                return {
                    "industry_tags": industry_tags,
                    "has_table": "|" in chunk.get("chunk_text", ""),
                    "enriched_at": datetime.now().isoformat(),
                }

            async def _update_chunk(chunk: Dict[str, Any]) -> None:
                metadata = _build_metadata(chunk)
                cid = chunk["chunk_id"]

                def _run():
                    self.db.table("chunks").update({"metadata": metadata}).eq("chunk_id", cid).execute()

                async with sem:
                    await asyncio.to_thread(_run)

            await asyncio.gather(*[_update_chunk(c) for c in chunks_result.data])
            enriched_count = len(chunks_result.data)

            return {
                "status": "success",
                "document_id": document_id,
                "enriched_chunks": enriched_count
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}


class OpenAIEmbedder:
    """OpenAI로 문장을 벡터로 변환하여 Supabase(pgvector)에 저장."""
    
    def __init__(self):
        self.db = get_db()
        self.embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
    
    async def embed_chunks(self, document_id: str) -> Dict[str, Any]:
        """청크 임베딩 생성 및 저장."""
        start_time = datetime.now()
        _log.debug("[%s] Starting embedding phase...", document_id)

        try:
            # 청크 조회 (임베딩에 필요한 필드만)
            chunks_result = self.db.table("chunks").select("chunk_id, chunk_text").eq(
                "document_id", document_id
            ).execute()

            if not chunks_result.data:
                _log.warning("[%s] Error: No chunks found to embed", document_id)
                return {"status": "failed", "error": "No chunks found"}
            
            # 이미 임베딩된 청크 제외
            existing_embeddings = self.db.table("embeddings").select("chunk_id").in_(
                "chunk_id", [c["chunk_id"] for c in chunks_result.data]
            ).execute()
            
            existing_ids = {e["chunk_id"] for e in (existing_embeddings.data or [])}
            
            chunks_to_embed = [
                c for c in chunks_result.data 
                if c["chunk_id"] not in existing_ids
            ]
            
            if not chunks_to_embed:
                _log.debug(
                    "[%s] All %s chunks already embedded. Skipping.",
                    document_id,
                    len(chunks_result.data),
                )
                # Ensure status is indexed
                self.db.table("documents").update({
                    "status": "indexed",
                    "indexed_at": datetime.now().isoformat()
                }).eq("document_id", document_id).execute()
                
                return {
                    "status": "success",
                    "document_id": document_id,
                    "embedded_count": 0,
                    "message": "All chunks already embedded"
                }
            
            # 배치 임베딩 (한 번에 수백 문단이면 API 한도·지연 증가 → 청크 단위로 분할)
            _log.info(
                "[%s] Generating embeddings for %s chunks using %s...",
                document_id,
                len(chunks_to_embed),
                settings.OPENAI_EMBEDDING_MODEL,
            )
            texts = [c["chunk_text"] for c in chunks_to_embed]
            embed_batch = 48
            vectors: List[List[float]] = []
            for i in range(0, len(texts), embed_batch):
                batch = texts[i : i + embed_batch]
                part = await self.embeddings.aembed_documents(batch)
                vectors.extend(part)
            
            # Supabase에 저장
            embedding_data = [
                {
                    "chunk_id": chunk["chunk_id"],
                    "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
                    "embedding": vector # pgvector handles list of floats or json string
                }
                for chunk, vector in zip(chunks_to_embed, vectors)
            ]
            
            self.db.table("embeddings").upsert(embedding_data).execute()
            
            # 문서 상태 업데이트
            self.db.table("documents").update({
                "status": "indexed",
                "indexed_at": datetime.now().isoformat()
            }).eq("document_id", document_id).execute()
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            _log.info(
                "[%s] Embedding success: %s vectors in %sms",
                document_id,
                len(embedding_data),
                processing_time,
            )
            
            return {
                "status": "success",
                "document_id": document_id,
                "embedded_count": len(embedding_data),
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}


class IngestionPipeline:
    """전체 인제스천 파이프라인 오케스트레이터."""
    
    def __init__(self):
        self.collector = RSSCollector()
        self.parser = LlamaDocumentParser()
        self.chunker = ContextualChunker()
        self.embedder = OpenAIEmbedder()
    
    async def run_full_pipeline(self, document_id: str) -> DocumentIngestionResult:
        """전체 파이프라인 실행."""
        start_time = datetime.now()
        
        try:
            # Phase 1: Parse
            parse_result = await self.parser.parse_document(document_id)
            if parse_result["status"] != "success":
                return DocumentIngestionResult(
                    document_id=document_id,
                    source_id="",
                    title="",
                    url="",
                    status="failed",
                    chunks_count=0,
                    embeddings_count=0,
                    error_message=parse_result.get("error")
                )
            
            # Phase 2: Enrich chunks
            enrich_result = await self.chunker.enrich_chunks(document_id)
            
            # Phase 3: Embed
            embed_result = await self.embedder.embed_chunks(document_id)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 문서 정보 조회 및 업데이트 (Resilient to column missing or DB error)
            try:
                self.parser.db.table("documents").update({
                    "chunks_count": parse_result.get("chunks_count", 0),
                    "last_processed_at": datetime.now().isoformat(),
                    "processing_status": "indexed"
                }).eq("document_id", document_id).execute()
            except Exception as db_err:
                _log.warning("[%s] DB update warning: %s", document_id, db_err)
                # Continue anyway as processing itself succeeded
            
            doc_result = self.parser.db.table("documents").select("*").eq(
                "document_id", document_id
            ).execute()
            
            doc = doc_result.data[0] if doc_result.data else {}
            
            return DocumentIngestionResult(
                document_id=document_id,
                source_id=doc.get("source_id", ""),
                title=doc.get("title", ""),
                url=doc.get("url", ""),
                status="success",
                chunks_count=parse_result.get("chunks_count", 0),
                embeddings_count=embed_result.get("embedded_count", 0),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            return DocumentIngestionResult(
                document_id=document_id,
                source_id="",
                title="",
                url="",
                status="failed",
                chunks_count=0,
                embeddings_count=0,
                error_message=str(e)
            )
    
    async def run_scheduled_collection(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """스케줄된 수집 실행 (1일 4회)."""
        from app.services.job_tracker import job_tracker
        
        results = {
            "collected": 0,
            "processed": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            if job_id:
                job_tracker.update_job(job_id, stage="collecting", progress=10, message="Starting RSS collection")
            
            # 1. RSS 수집
            collection = await self.collector.collect_all(job_id=job_id)
            results["collected"] = collection.get("total_new", 0)
            
            if job_id:
                if results["collected"] == 0:
                    job_tracker.update_job(job_id, status="no_change", stage="done", progress=100, message="No new documents found")
                    return results
                
                job_tracker.update_job(
                    job_id, 
                    stage="parsing", 
                    progress=20, 
                    total_count=results["collected"],
                    message=f"Collected {results['collected']} new docs. Starting pipeline..."
                )
            
            # 2. 신규 문서 처리
            for i, doc in enumerate(collection.get("documents", [])):
                doc_id = doc.get("document_id")
                
                if job_id:
                    progress = 20 + int((i / results["collected"]) * 75)
                    job_tracker.update_job(
                        job_id, 
                        stage="processing", 
                        progress=progress, 
                        processed_count=i,
                        message=f"Processing {i+1}/{results['collected']}: {doc.get('title')[:30]}..."
                    )
                
                pipeline_result = await self.run_full_pipeline(doc_id)
                
                if pipeline_result.status == "success":
                    results["processed"] += 1
                else:
                    results["failed"] += 1
                
                results["details"].append({
                    "document_id": doc_id,
                    "title": pipeline_result.title,
                    "status": pipeline_result.status
                })
            
            if job_id:
                final_status = "success"
                msg = f"Completed: {results['collected']} collected, {results['processed']} processed"
                job_tracker.update_job(job_id, status=final_status, stage="done", progress=100, count=results["collected"], message=msg)
        except Exception as e:
            _log.exception("Pipeline error: %s", e)
            if job_id:
                job_tracker.update_job(job_id, status="error", message=f"Pipeline crashed: {str(e)}")
            
        return results


# 싱글톤 인스턴스
_ingestion_pipeline: Optional[IngestionPipeline] = None

def get_ingestion_pipeline() -> IngestionPipeline:
    global _ingestion_pipeline
    if _ingestion_pipeline is None:
        _ingestion_pipeline = IngestionPipeline()
    return _ingestion_pipeline
