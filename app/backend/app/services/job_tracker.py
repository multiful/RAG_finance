import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.core.redis import get_redis

class JobTracker:
    """Tracks status of long-running collection jobs in Redis."""
    
    def __init__(self):
        self._redis = None
        self.prefix = "job:"
        self.expiry = 3600  # 1 hour TTL

    @property
    def redis(self):
        """Lazy load redis client."""
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    def is_available(self) -> bool:
        """Check if Redis is available."""
        try:
            return self.redis.ping()
        except Exception:
            return False

    def create_job(self, stage: str = "collecting") -> str:
        if not self.is_available():
            print("❌ Cannot create job: Redis is unavailable")
            return "fallback-job-id"
            
        job_id = str(uuid.uuid4())
        job_data = {
            "job_id": job_id,
            "status": "running",
            "stage": stage,
            "progress": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "new_documents_count": 0,
            "processed_documents_count": 0,
            "total_documents_count": 0,
            "message": f"Job started: {stage}"
        }
        try:
            key = f"{self.prefix}{job_id}"
            latest_key = f"{self.prefix}latest"
            
            print(f"DEBUG: Creating job {job_id} at key {key}")
            self.redis.setex(key, self.expiry, json.dumps(job_data))
            self.redis.setex(latest_key, self.expiry, job_id)
            
            # Verify immediately
            verify = self.redis.get(key)
            if not verify:
                print(f"⚠️ WARNING: Job {job_id} was NOT found immediately after setex!")
            
            return job_id
        except Exception as e:
            print(f"Redis error in create_job: {e}")
            return job_id

    def update_job(self, job_id: str, status: Optional[str] = None, count: Optional[int] = None, 
                   message: str = "", stage: Optional[str] = None, progress: Optional[float] = None,
                   processed_count: Optional[int] = None, total_count: Optional[int] = None):
        if not self.is_available():
            return
            
        key = f"{self.prefix}{job_id}"
        data = self.get_job(job_id)
        if not data:
            print(f"⚠️ WARNING: Tried to update non-existent job {job_id} at key {key}")
            return
        
        if status: data["status"] = status
        if count is not None: data["new_documents_count"] = count
        if message: data["message"] = message
        if stage: data["stage"] = stage
        if progress is not None: data["progress"] = progress
        if processed_count is not None: data["processed_documents_count"] = processed_count
        if total_count is not None: data["total_documents_count"] = total_count
        
        if status in ["success", "success_collect", "no_change", "error"]:
            data["finished_at"] = datetime.now(timezone.utc).isoformat()
        
        try:
            self.redis.setex(f"{self.prefix}{job_id}", self.expiry, json.dumps(data))
        except Exception as e:
            print(f"Redis error in update_job: {e}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_available():
            return None
            
        try:
            raw = self.redis.get(f"{self.prefix}{job_id}")
            if not raw:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception as e:
            print(f"Redis error in get_job: {e}")
            return None

    def get_latest_job_id(self) -> Optional[str]:
        if not self.is_available():
            return None
            
        try:
            val = self.redis.get(f"{self.prefix}latest")
            if isinstance(val, bytes):
                return val.decode("utf-8")
            return val
        except Exception:
            return None

job_tracker = JobTracker()
