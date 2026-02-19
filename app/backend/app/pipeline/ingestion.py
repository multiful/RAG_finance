"""Phase A: 데이터 인제스천 파이프라인 (LLM Ops)

Pipeline: Collector → Parser → Chunker → Embedder → Supabase(pgvector)
"""
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

from app.core.config import settings
from app.core.database import get_db
from app.parsers.llama_parser import parse_and_chunk_document
from langchain_openai import OpenAIEmbeddings


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
            
            print(f"Parsed {len(documents)} documents for fid {fid}")
            return documents
            
        except Exception as e:
            print(f"Error fetching RSS feed {fid}: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> datetime:
        import feedparser
        from datetime import timezone
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
            print(f"Found sources in DB: {list(fid_map.keys())}")
        except Exception as e:
            print(f"Error fetching sources: {e}")
            return {"error": str(e)}
        
        for fid in settings.FSC_RSS_FIDS:
            if job_id:
                job_tracker.update_job(job_id, stage="collecting", message=f"Fetching feed {fid}...")
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
                        print(f"Error inserting document {doc['url']}: {ins_err}")
                
            except Exception as e:
                print(f"Error in collect_all for fid {fid}: {e}")
                results["errors"].append({"fid": fid, "error": str(e)})
        
        return results


class LlamaDocumentParser:
    """LlamaParse API로 PDF/HWP → 마크다운 변환."""
    
    def __init__(self):
        self.db = get_db()
    
    async def parse_document(self, document_id: str) -> Dict[str, Any]:
        """문서 파싱 및 청킹."""
        start_time = datetime.now()
        print(f"[{document_id}] Starting parsing phase...")
        
        try:
            # 문서 조회
            doc_result = self.db.table("documents").select("*").eq(
                "document_id", document_id
            ).execute()
            
            if not doc_result.data:
                print(f"[{document_id}] Error: Document not found")
                return {"status": "failed", "error": "Document not found"}
            
            doc = doc_result.data[0]
            
            # 첨부 파일 확인
            all_chunks = []
            try:
                files_result = self.db.table("document_files").select("*").eq(
                    "document_id", document_id
                ).execute()
                
                if files_result.data:
                    print(f"[{document_id}] Found {len(files_result.data)} attachments. Using LlamaParse...")
                    for file in files_result.data:
                        file_path = file.get("file_path")
                        file_type = file.get("file_type", "pdf")
                        
                        if file_path:
                            # LlamaParse로 파싱
                            chunks = await parse_and_chunk_document(file_path, file_type)
                            all_chunks.extend(chunks)
                else:
                    print(f"[{document_id}] No attachments found.")
            except Exception as e:
                print(f"[{document_id}] document_files check failed, assuming empty: {e}")

            if not all_chunks:
                # HTML 본문 직접 파싱
                raw_html = doc.get("raw_html", "")
                if raw_html:
                    print(f"[{document_id}] Extracting chunks from raw_html...")
                    all_chunks = self._parse_html_to_chunks(raw_html, document_id)
            
            if not all_chunks:
                print(f"[{document_id}] No content available for parsing.")
                return {"status": "failed", "error": "No content found"}

            # 청크 저장
            chunk_ids = []
            for i, chunk in enumerate(all_chunks):
                chunk_data = {
                    "document_id": document_id,
                    "chunk_index": i,
                    "chunk_text": chunk["chunk_text"],
                    "chunk_tokens": chunk.get("chunk_tokens", 0),
                    "chunking_version": "llamaparse_v1",
                    "section_title": chunk.get("section_title")
                }
                
                result = self.db.table("chunks").insert(chunk_data).execute()
                if result.data:
                    chunk_ids.append(result.data[0]["chunk_id"])
            
            # 문서 상태 업데이트
            self.db.table("documents").update({
                "status": "parsed",
                "parsed_at": datetime.now().isoformat()
            }).eq("document_id", document_id).execute()
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            print(f"[{document_id}] Successfully parsed into {len(chunk_ids)} chunks.")
            
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
        """HTML을 청크로 변환."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 텍스트 추출
        text = soup.get_text(separator='\n', strip=True)
        
        # 청킹
        chunks = []
        chunk_size = settings.CHUNK_SIZE
        chunk_overlap = settings.CHUNK_OVERLAP
        
        words = text.split()
        
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk_text = ' '.join(words[i:i + chunk_size])
            chunks.append({
                "chunk_text": chunk_text,
                "chunk_tokens": len(chunk_text.split()),
                "section_title": None
            })
        
        return chunks


class ContextualChunker:
    """LangChain 기반 문맥 보존 청킹 + 업권 메타데이터 부착."""
    
    def __init__(self):
        self.db = get_db()
    
    async def enrich_chunks(self, document_id: str) -> Dict[str, Any]:
        """청크에 메타데이터 부착."""
        try:
            # 청크 조회
            chunks_result = self.db.table("chunks").select("*").eq(
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
            
            enriched_count = 0
            
            for chunk in chunks_result.data:
                chunk_text = chunk.get("chunk_text", "").lower()
                
                # 업권 태그 추출
                industry_tags = []
                for industry, keywords in industry_keywords.items():
                    if any(kw in chunk_text for kw in keywords):
                        industry_tags.append(industry)
                
                # 메타데이터 업데이트
                metadata = {
                    "industry_tags": industry_tags,
                    "has_table": "|" in chunk.get("chunk_text", ""),
                    "enriched_at": datetime.now().isoformat()
                }
                
                self.db.table("chunks").update({
                    "metadata": metadata
                }).eq("chunk_id", chunk["chunk_id"]).execute()
                
                enriched_count += 1
            
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
        print(f"[{document_id}] Starting embedding phase...")
        
        try:
            # 청크 조회
            chunks_result = self.db.table("chunks").select("*").eq(
                "document_id", document_id
            ).execute()
            
            if not chunks_result.data:
                print(f"[{document_id}] Error: No chunks found to embed")
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
                print(f"[{document_id}] All {len(chunks_result.data)} chunks already embedded. Skipping.")
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
            
            # 배치 임베딩
            print(f"[{document_id}] Generating embeddings for {len(chunks_to_embed)} chunks using {settings.OPENAI_EMBEDDING_MODEL}...")
            texts = [c["chunk_text"] for c in chunks_to_embed]
            vectors = await self.embeddings.aembed_documents(texts)
            
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
            print(f"[{document_id}] Embedding success: {len(embedding_data)} vectors in {processing_time}ms")
            
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
                print(f"[{document_id}] DB Update warning: {db_err}")
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
            print(f"Pipeline error: {e}")
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
