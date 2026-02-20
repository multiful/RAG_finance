"""Financial Supervisory Service (FSS) web scraper."""
import hashlib
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import DocumentCreate


class FSSScraper:
    """금융감독원 웹 스크래퍼."""
    
    BOARD_NAMES = {
        "B0000052": "보도자료",
        "B0000110": "공지사항",
    }
    
    def __init__(self):
        self.db = get_db()
        self.base_url = settings.FSS_BASE_URL
    
    def _generate_hash(self, url: str, title: str, date_str: str) -> str:
        """Generate unique hash for document."""
        content = f"{url}:{title}:{date_str}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse Korean date format (YYYY.MM.DD)."""
        try:
            # Format: 2024.01.15
            dt = datetime.strptime(date_str.strip(), "%Y.%m.%d")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)
    
    def _extract_board_id(self, path: str) -> str:
        """Extract board ID from path."""
        for board_id in self.BOARD_NAMES.keys():
            if board_id in path:
                return board_id
        return "unknown"
    
    async def fetch_board(self, board_path: str) -> List[Dict[str, Any]]:
        """Fetch and parse FSS board page."""
        url = f"{self.base_url}{board_path}"
        print(f"Fetching FSS board: {url}")
        
        documents = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # FSS uses table-based layout for board
            rows = soup.select('table.bd_list tbody tr')
            
            board_id = self._extract_board_id(board_path)
            category = self.BOARD_NAMES.get(board_id, "금감원")
            
            for row in rows:
                try:
                    # Skip notice rows (fixed posts)
                    if row.get('class') and 'notice' in ' '.join(row.get('class', [])):
                        continue
                    
                    title_cell = row.select_one('td.subject a, td.title a')
                    date_cell = row.select_one('td.date, td:nth-child(5)')
                    
                    if not title_cell:
                        continue
                    
                    title = title_cell.get_text(strip=True)
                    href = title_cell.get('href', '')
                    
                    # Build full URL
                    if href.startswith('/'):
                        doc_url = f"{self.base_url}{href}"
                    elif href.startswith('http'):
                        doc_url = href
                    else:
                        continue
                    
                    # Get date
                    date_str = date_cell.get_text(strip=True) if date_cell else ""
                    published_at = self._parse_date(date_str)
                    
                    doc = {
                        "title": title,
                        "url": doc_url,
                        "published_at": published_at,
                        "summary": "",
                        "category": category,
                        "source": "FSS",
                        "hash": self._generate_hash(doc_url, title, date_str)
                    }
                    documents.append(doc)
                    
                except Exception as row_err:
                    print(f"Error parsing row: {row_err}")
                    continue
            
            print(f"Parsed {len(documents)} documents from FSS board")
            return documents
            
        except Exception as e:
            print(f"Error fetching FSS board {board_path}: {e}")
            return []
    
    async def collect_all(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """Collect all FSS boards."""
        if not settings.ENABLE_FSS_SCRAPING:
            print("FSS scraping is disabled")
            return {"total_new": 0, "message": "FSS scraping disabled"}
        
        results = {
            "total_new": 0,
            "total_existing": 0,
            "errors": [],
            "boards": {}
        }
        
        # Get or create FSS source record
        try:
            source_res = self.db.table("sources").select("source_id").eq("name", "금융감독원").execute()
            
            if source_res.data:
                source_uuid = source_res.data[0]["source_id"]
            else:
                # Create FSS source
                new_source = self.db.table("sources").insert({
                    "name": "금융감독원",
                    "fid": "FSS",
                    "base_url": self.base_url,
                    "active": True
                }).execute()
                source_uuid = new_source.data[0]["source_id"]
                print(f"Created FSS source with ID: {source_uuid}")
                
        except Exception as e:
            print(f"Error getting/creating FSS source: {e}")
            return {"error": str(e)}
        
        for board_path in settings.FSS_BOARDS:
            try:
                documents = await self.fetch_board(board_path)
                board_id = self._extract_board_id(board_path)
                
                board_result = {
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
                        board_result["existing"] += 1
                        results["total_existing"] += 1
                        continue
                    
                    # Insert new document
                    doc_create = DocumentCreate(
                        source_id=source_uuid,
                        title=doc["title"],
                        published_at=doc["published_at"],
                        url=doc["url"],
                        category=doc["category"],
                        hash=doc["hash"]
                    )
                    
                    try:
                        payload = doc_create.model_dump(mode='json')
                        self.db.table("documents").upsert(
                            payload,
                            on_conflict="url"
                        ).execute()
                        board_result["new"] += 1
                        results["total_new"] += 1
                    except Exception as ins_err:
                        print(f"Error inserting FSS document: {ins_err}")
                
                results["boards"][board_id] = board_result
                
            except Exception as e:
                print(f"Error collecting FSS board {board_path}: {e}")
                results["errors"].append({"board": board_path, "error": str(e)})
        
        return results


# Singleton instance
fss_scraper = FSSScraper()
