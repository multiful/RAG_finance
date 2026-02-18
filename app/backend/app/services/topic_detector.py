"""Topic surge detection service."""
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import TopicResponse, AlertResponse, AlertSeverity, IndustryType


class TopicDetector:
    """Detect emerging topics and generate alerts."""
    
    def __init__(self):
        self.db = get_db()
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)
    
    async def cluster_documents(
        self,
        start_date: datetime,
        end_date: datetime,
        min_cluster_size: int = 3
    ) -> List[Dict[str, Any]]:
        """Cluster documents by embedding similarity."""
        
        # Get documents with embeddings
        result = self.db.table("chunks").select(
            "*, documents!inner(title, published_at, url), embeddings!inner(embedding)"
        ).gte("documents.published_at", start_date.isoformat()).lte(
            "documents.published_at", end_date.isoformat()
        ).execute()
        
        if not result.data:
            return []
        
        # Group by document
        doc_chunks = defaultdict(list)
        for item in result.data:
            doc_id = item["document_id"]
            doc_chunks[doc_id].append(item)
        
        # Create document embeddings (average of chunks)
        doc_embeddings = {}
        doc_info = {}
        
        for doc_id, chunks in doc_chunks.items():
            embeddings = []
            for chunk in chunks:
                if chunk.get("embeddings") and chunk["embeddings"].get("embedding"):
                    emb = json.loads(chunk["embeddings"]["embedding"])
                    embeddings.append(emb)
            
            if embeddings:
                doc_embeddings[doc_id] = np.mean(embeddings, axis=0).tolist()
                doc_info[doc_id] = {
                    "title": chunks[0]["documents"]["title"],
                    "published_at": chunks[0]["documents"]["published_at"],
                    "url": chunks[0]["documents"]["url"]
                }
        
        # Simple clustering (agglomerative)
        doc_ids = list(doc_embeddings.keys())
        n = len(doc_ids)
        
        if n < min_cluster_size:
            return []
        
        # Similarity matrix
        similarity_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i+1, n):
                sim = self._cosine_similarity(
                    doc_embeddings[doc_ids[i]],
                    doc_embeddings[doc_ids[j]]
                )
                similarity_matrix[i][j] = sim
                similarity_matrix[j][i] = sim
        
        # Hierarchical clustering (simplified)
        clusters = []
        threshold = 0.75
        visited = set()
        
        for i in range(n):
            if i in visited:
                continue
            
            cluster = [i]
            visited.add(i)
            
            for j in range(i+1, n):
                if j not in visited and similarity_matrix[i][j] > threshold:
                    cluster.append(j)
                    visited.add(j)
            
            if len(cluster) >= min_cluster_size:
                cluster_docs = [doc_ids[idx] for idx in cluster]
                
                # Calculate centroid
                centroid = np.mean(
                    [doc_embeddings[doc_id] for doc_id in cluster_docs],
                    axis=0
                ).tolist()
                
                clusters.append({
                    "document_ids": cluster_docs,
                    "centroid": centroid,
                    "size": len(cluster)
                })
        
        return clusters
    
    async def calculate_surge_score(
        self,
        cluster: Dict[str, Any],
        prev_period_clusters: List[Dict[str, Any]]
    ) -> float:
        """Calculate surge score for a topic cluster."""
        
        # Factors:
        # 1. Recency (more recent = higher)
        # 2. Growth rate (vs previous period)
        # 3. Novelty (not in previous period)
        
        score = 0.0
        current_size = cluster["size"]
        
        # Base score from size
        score += min(current_size * 5, 30)
        
        # Check if similar cluster existed in previous period
        is_new = True
        max_prev_similarity = 0.0
        
        for prev_cluster in prev_period_clusters:
            sim = self._cosine_similarity(
                cluster["centroid"],
                prev_cluster["centroid"]
            )
            max_prev_similarity = max(max_prev_similarity, sim)
            
            if sim > 0.7:  # Similar cluster exists
                is_new = False
                growth = (current_size - prev_cluster["size"]) / max(prev_cluster["size"], 1)
                score += growth * 20  # Growth bonus
        
        # Novelty bonus
        if is_new:
            score += 25
        
        # Normalize to 0-100
        return min(score, 100)
    
    async def detect_surging_topics(
        self,
        days: int = 7
    ) -> List[TopicResponse]:
        """Detect surging topics in recent period."""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        prev_start = start_date - timedelta(days=days)
        
        # Current period clusters
        current_clusters = await self.cluster_documents(start_date, end_date)
        
        # Previous period clusters (for comparison)
        prev_clusters = await self.cluster_documents(prev_start, start_date)
        
        topics = []
        
        for i, cluster in enumerate(current_clusters):
            surge_score = await self.calculate_surge_score(cluster, prev_clusters)
            
            # Get representative documents
            rep_docs = []
            for doc_id in cluster["document_ids"][:3]:
                doc_result = self.db.table("documents").select("*").eq(
                    "document_id", doc_id
                ).execute()
                
                if doc_result.data:
                    doc = doc_result.data[0]
                    rep_docs.append({
                        "document_id": doc_id,
                        "title": doc["title"],
                        "url": doc["url"],
                        "published_at": doc["published_at"]
                    })
            
            # Generate topic name from documents
            titles = [d["title"] for d in rep_docs]
            topic_name = self._generate_topic_name(titles)
            
            # Save topic
            topic_data = {
                "topic_name": topic_name,
                "topic_summary": f"{len(cluster['document_ids'])}개 문서 클러스터",
                "time_window_start": start_date.isoformat(),
                "time_window_end": end_date.isoformat(),
                "topic_embedding": json.dumps(cluster["centroid"])
            }
            
            topic_result = self.db.table("topics").insert(topic_data).execute()
            topic_id = topic_result.data[0]["topic_id"] if topic_result.data else f"topic_{i}"
            
            # Save memberships
            for doc_id in cluster["document_ids"]:
                self.db.table("topic_memberships").insert({
                    "topic_id": topic_id,
                    "document_id": doc_id,
                    "score": 1.0
                }).execute()
            
            # Create alert if surge score is high
            if surge_score > 50:
                severity = AlertSeverity.HIGH if surge_score > 75 else (
                    AlertSeverity.MEDIUM if surge_score > 60 else AlertSeverity.LOW
                )
                
                # Detect industries
                industries = await self._detect_topic_industries(cluster["document_ids"])
                
                self.db.table("alerts").insert({
                    "topic_id": topic_id,
                    "surge_score": surge_score,
                    "severity": severity.value,
                    "industries": [i.value for i in industries],
                    "status": "open"
                }).execute()
            
            topics.append(TopicResponse(
                topic_id=topic_id,
                topic_name=topic_name,
                topic_summary=topic_data["topic_summary"],
                time_window_start=start_date,
                time_window_end=end_date,
                document_count=len(cluster["document_ids"]),
                surge_score=surge_score,
                representative_documents=rep_docs
            ))
        
        # Sort by surge score
        topics.sort(key=lambda x: x.surge_score, reverse=True)
        return topics
    
    def _generate_topic_name(self, titles: List[str]) -> str:
        """Generate topic name from document titles."""
        if not titles:
            return "Unknown Topic"
        
        # Extract common keywords
        import re
        from collections import Counter
        
        all_words = []
        for title in titles:
            words = re.findall(r'[가-힣]{2,}', title)
            all_words.extend(words)
        
        # Filter common stop words
        stop_words = {"금융", "위원회", "금융위", "관련", "대한", "및", "등"}
        words = [w for w in all_words if w not in stop_words]
        
        if words:
            most_common = Counter(words).most_common(2)
            return "".join([w[0] for w in most_common])
        
        return titles[0][:20] if titles else "Unknown Topic"
    
    async def _detect_topic_industries(
        self,
        document_ids: List[str]
    ) -> List[IndustryType]:
        """Detect industries affected by topic."""
        industries = set()
        
        for doc_id in document_ids:
            labels = self.db.table("industry_labels").select("*").eq(
                "document_id", doc_id
            ).execute()
            
            if labels.data:
                label = labels.data[0]
                if label.get("label_insurance", 0) > 0.3:
                    industries.add(IndustryType.INSURANCE)
                if label.get("label_banking", 0) > 0.3:
                    industries.add(IndustryType.BANKING)
                if label.get("label_securities", 0) > 0.3:
                    industries.add(IndustryType.SECURITIES)
        
        return list(industries)
    
    async def get_active_alerts(self) -> List[AlertResponse]:
        """Get active alerts."""
        result = self.db.table("alerts").select(
            "*, topics(topic_name)"
        ).eq("status", "open").order("surge_score", desc=True).execute()
        
        alerts = []
        if result.data:
            for item in result.data:
                alerts.append(AlertResponse(
                    alert_id=item["alert_id"],
                    topic_id=item["topic_id"],
                    topic_name=item.get("topics", {}).get("topic_name"),
                    surge_score=item["surge_score"],
                    severity=AlertSeverity(item["severity"]),
                    industries=[IndustryType(i) for i in item.get("industries", [])],
                    generated_at=item["generated_at"],
                    status=item["status"]
                ))
        
        return alerts
