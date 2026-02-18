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
        "0111": "볏  도자료",
        "0112": "볏  도설명",
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
    
    async def fetch_feed(self, fid: str) -> List[Dict[str, Any]]:
        """RSS 피드 수집."""
        import feedparser
        
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
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        import feedparser
        try:
            struct_time = feedparser._parse_date(date_str)
            if struct_time:
                return datetime(*struct_time[:6])
        except:
            pass
        return datetime.now()
    
    async def collect_all(self) -> Dict[str, Any]:
        """모든 RSS 피드 수집."""
        results = {
            "total_new": 0,
            "total_existing": 0,
            "errors": [],
            "documents": []
        }
        
        for fid in settings.FSC_RSS_FIDS:
            try:
                documents = await self.fetch_feed(fid)
                
                for doc in documents:
                    # 중복 체크
                    existing = self.db.table("documents").select("document_id").eq(
                        "hash", doc["hash"]
                    ).execute()
                    
                    if existing.data:
                        results["total_existing"] += 1
                        continue
                    
                    # 신규 문서 저장
                    doc_data = {
                        "source_id": f"FSC_RSS_{fid}",
                        "title": doc["title"],
                        "published_at": doc["published_at"].isoformat(),
                        "url": doc["url"],
                        "category": doc["category"],
                        "hash": doc["hash"],
                        "status": "ingested",
                        "raw_html": doc.get("summary", "")
                    }
                    
                    result = self.db.table("documents").insert(doc_data).execute()
                    
                    if result.data:
                        results["total_new"] += 1
                        results["documents"].append(result.data[0])
                
            except Exception as e:
                results["errors"].append({"fid": fid, "error": str(e)})
        
        return results


class LlamaDocumentParser:
    """LlamaParse API로 PDF/HWP → 마크다운 변환."""
    
    def __init__(self):
        self.db = get_db()
    
    async def parse_document(self, document_id: str) -> Dict[str, Any]:
        """문서 파싱 및 청킹."""
        start_time = datetime.now()
        
        try:
            # 문서 조회
            doc_result = self.db.table("documents").select("*").eq(
                "document_id", document_id
            ).execute()
            
            if not doc_result.data:
                return {"status": "failed", "error": "Document not found"}
            
            doc = doc_result.data[0]
            
            # 첨부 파일 확인
            files_result = self.db.table("document_files").select("*").eq(
                "document_id", document_id
            ).execute()
            
            all_chunks = []
            
            if files_result.data:
                for file in files_result.data:
                    file_path = file.get("file_path")
                    file_type = file.get("file_type", "pdf")
                    
                    if file_path:
                        # LlamaParse로 파싱
                        chunks = await parse_and_chunk_document(file_path, file_type)
                        all_chunks.extend(chunks)
            else:
                # HTML 본문 직접 파싱
                raw_html = doc.get("raw_html", "")
                if raw_html:
                    chunks = self._parse_html_to_chunks(raw_html, document_id)
                    all_chunks.extend(chunks)
            
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
        
        try:
            # 청크 조회
            chunks_result = self.db.table("chunks").select("*").eq(
                "document_id", document_id
            ).execute()
            
            if not chunks_result.data:
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
                return {
                    "status": "success",
                    "document_id": document_id,
                    "embedded_count": 0,
                    "message": "All chunks already embedded"
                }
            
            # 배치 임베딩
            texts = [c["chunk_text"] for c in chunks_to_embed]
            vectors = await self.embeddings.aembed_documents(texts)
            
            # Supabase에 저장
            embedding_data = [
                {
                    "chunk_id": chunk["chunk_id"],
                    "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
                    "embedding": json.dumps(vector)
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
            
            # 문서 정보 조회
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
    
    async def run_scheduled_collection(self) -> Dict[str, Any]:
        """스케줄된 수집 실행 (1일 4회)."""
        results = {
            "collected": 0,
            "processed": 0,
            "failed": 0,
            "details": []
        }
        
        # 1. RSS 수집
        collection = await self.collector.collect_all()
        results["collected"] = collection["total_new"]
        
        # 2. 신규 문서 처리
        for doc in collection.get("documents", []):
            doc_id = doc.get("document_id")
            
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
        
        return results


# 싱글톤 인스턴스
_ingestion_pipeline: Optional[IngestionPipeline] = None

def get_ingestion_pipeline() -> IngestionPipeline:
    global _ingestion_pipeline
    if _ingestion_pipeline is None:
        _ingestion_pipeline = IngestionPipeline()
    return _ingestion_pipeline
