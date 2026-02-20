"""Policy Timeline Extractor Service.

Extracts key dates (effective dates, deadlines, grace periods) from policy documents
and provides calendar-ready timeline events.
"""
import openai
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone, date
from dateutil import parser as date_parser

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.models.schemas import (
    IndustryType, TimelineEvent, TimelineEventType,
    TimelineResponse, TimelineExtractRequest
)


class TimelineExtractorService:
    """Service for extracting policy timelines and managing events."""
    
    def __init__(self):
        self.db = get_db()
        self.redis = get_redis()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def extract_timeline_from_document(
        self,
        document_id: str,
        force_refresh: bool = False
    ) -> List[TimelineEvent]:
        """Extract timeline events from a document using GPT-4."""
        
        if not force_refresh:
            existing = self.db.table("timeline_events").select("*").eq(
                "document_id", document_id
            ).execute()
            
            if existing.data:
                return self._convert_to_events(existing.data, document_id)
        
        doc_result = self.db.table("documents").select("*").eq(
            "document_id", document_id
        ).execute()
        
        if not doc_result.data:
            return []
        
        doc = doc_result.data[0]
        
        chunks_result = self.db.table("chunks").select("chunk_text").eq(
            "document_id", document_id
        ).order("chunk_index").execute()
        
        full_text = "\n".join([c["chunk_text"] for c in chunks_result.data]) if chunks_result.data else ""
        
        if not full_text:
            full_text = doc.get("raw_html", "")[:5000]
        
        events = await self._extract_dates_with_llm(
            document_id=document_id,
            document_title=doc["title"],
            document_text=full_text,
            published_at=doc["published_at"]
        )
        
        for event in events:
            self._save_event(event, document_id)
        
        return events
    
    async def _extract_dates_with_llm(
        self,
        document_id: str,
        document_title: str,
        document_text: str,
        published_at: str
    ) -> List[TimelineEvent]:
        """Use GPT-4 to extract dates and deadlines from document text."""
        
        extraction_prompt = f"""당신은 금융 규제 문서 분석 전문가입니다. 다음 문서에서 모든 중요한 날짜와 기한을 추출하세요.

문서 제목: {document_title}
발행일: {published_at}

문서 내용:
{document_text[:6000]}

다음 유형의 날짜를 모두 찾아주세요:
1. effective_date: 시행일, 적용일
2. deadline: 제출 기한, 신고 기한
3. grace_period_end: 유예기간 종료일
4. submission_due: 보고서 제출일, 서류 제출 마감
5. review_date: 검토 예정일, 재검토 시기

각 날짜에 대해 JSON 형식으로 반환하세요:
{{
    "events": [
        {{
            "event_type": "effective_date|deadline|grace_period_end|submission_due|review_date",
            "event_date": "YYYY-MM-DD",
            "description": "이 날짜의 의미 설명",
            "target_entities": ["적용 대상 기관/업종"],
            "industries": ["INSURANCE", "BANKING", "SECURITIES"],
            "is_critical": true/false
        }}
    ]
}}

규칙:
- 날짜가 명시되지 않은 경우 "즉시 시행"은 발행일로 처리
- "1개월 이내", "6개월 후" 등 상대적 날짜는 발행일 기준으로 계산
- 연도가 없으면 발행연도 사용 (발행월 이전 월은 다음해)
- 확실하지 않은 날짜는 제외
- is_critical: 위반 시 제재가 있거나 중요한 기한인 경우 true"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            events_data = result.get("events", [])
            
            events = []
            today = date.today()
            
            for i, ev in enumerate(events_data):
                try:
                    event_date = date_parser.parse(ev["event_date"]).date()
                    days_remaining = (event_date - today).days
                    
                    industries = [
                        IndustryType(ind) for ind in ev.get("industries", [])
                        if ind in [e.value for e in IndustryType]
                    ]
                    
                    events.append(TimelineEvent(
                        event_id=f"{document_id}_{i}",
                        document_id=document_id,
                        document_title=document_title,
                        event_type=TimelineEventType(ev["event_type"]),
                        event_date=datetime.combine(event_date, datetime.min.time()),
                        description=ev["description"],
                        target_entities=ev.get("target_entities", []),
                        industries=industries,
                        days_remaining=days_remaining,
                        is_critical=ev.get("is_critical", False)
                    ))
                except Exception as e:
                    print(f"Error parsing event: {e}")
                    continue
            
            return events
            
        except Exception as e:
            print(f"Error extracting timeline: {e}")
            return []
    
    def _save_event(self, event: TimelineEvent, document_id: str):
        """Save timeline event to database."""
        event_data = {
            "document_id": document_id,
            "event_type": event.event_type.value,
            "event_date": event.event_date.date().isoformat(),
            "description": event.description,
            "target_entities": event.target_entities,
            "industries": [i.value for i in event.industries],
            "is_critical": event.is_critical
        }
        
        try:
            self.db.table("timeline_events").insert(event_data).execute()
        except Exception as e:
            print(f"Error saving timeline event: {e}")
    
    def _convert_to_events(
        self,
        data: List[Dict[str, Any]],
        document_id: str
    ) -> List[TimelineEvent]:
        """Convert database records to TimelineEvent objects."""
        
        doc_result = self.db.table("documents").select("title").eq(
            "document_id", document_id
        ).execute()
        
        doc_title = doc_result.data[0]["title"] if doc_result.data else "Unknown"
        
        today = date.today()
        events = []
        
        for item in data:
            try:
                event_date = date_parser.parse(item["event_date"]).date()
                days_remaining = (event_date - today).days
                
                industries = [
                    IndustryType(ind) for ind in item.get("industries", [])
                    if ind in [e.value for e in IndustryType]
                ]
                
                events.append(TimelineEvent(
                    event_id=item["event_id"],
                    document_id=document_id,
                    document_title=doc_title,
                    event_type=TimelineEventType(item["event_type"]),
                    event_date=datetime.combine(event_date, datetime.min.time()),
                    description=item["description"],
                    target_entities=item.get("target_entities", []),
                    industries=industries,
                    days_remaining=days_remaining,
                    is_critical=item.get("is_critical", False)
                ))
            except Exception as e:
                print(f"Error converting event: {e}")
                continue
        
        return events
    
    async def get_upcoming_events(
        self,
        days_ahead: int = 90,
        industries: Optional[List[IndustryType]] = None,
        include_past: bool = False
    ) -> TimelineResponse:
        """Get upcoming timeline events."""
        
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        query = self.db.table("timeline_events").select(
            "*, documents(title)"
        ).lte("event_date", end_date.isoformat())
        
        if not include_past:
            query = query.gte("event_date", today.isoformat())
        
        query = query.order("event_date")
        
        result = query.execute()
        
        if not result.data:
            return TimelineResponse(events=[], total_events=0, upcoming_critical=0)
        
        events = []
        critical_count = 0
        
        for item in result.data:
            item_industries = [
                IndustryType(ind) for ind in item.get("industries", [])
            ]
            
            if industries:
                if not any(ind in item_industries for ind in industries):
                    continue
            
            try:
                event_date = date_parser.parse(item["event_date"]).date()
                days_remaining = (event_date - today).days
                
                doc_title = item["documents"]["title"] if item.get("documents") else "Unknown"
                
                event = TimelineEvent(
                    event_id=item["event_id"],
                    document_id=item["document_id"],
                    document_title=doc_title,
                    event_type=TimelineEventType(item["event_type"]),
                    event_date=datetime.combine(event_date, datetime.min.time()),
                    description=item["description"],
                    target_entities=item.get("target_entities", []),
                    industries=item_industries,
                    days_remaining=days_remaining,
                    is_critical=item.get("is_critical", False)
                )
                
                events.append(event)
                
                if event.is_critical and days_remaining >= 0:
                    critical_count += 1
                    
            except Exception as e:
                print(f"Error processing event: {e}")
                continue
        
        return TimelineResponse(
            events=events,
            total_events=len(events),
            upcoming_critical=critical_count
        )
    
    async def get_events_by_date_range(
        self,
        start_date: date,
        end_date: date,
        industries: Optional[List[IndustryType]] = None
    ) -> List[TimelineEvent]:
        """Get events within a date range."""
        
        query = self.db.table("timeline_events").select(
            "*, documents(title)"
        ).gte("event_date", start_date.isoformat()).lte(
            "event_date", end_date.isoformat()
        ).order("event_date")
        
        result = query.execute()
        
        if not result.data:
            return []
        
        today = date.today()
        events = []
        
        for item in result.data:
            item_industries = [
                IndustryType(ind) for ind in item.get("industries", [])
            ]
            
            if industries:
                if not any(ind in item_industries for ind in industries):
                    continue
            
            try:
                event_date = date_parser.parse(item["event_date"]).date()
                days_remaining = (event_date - today).days
                
                doc_title = item["documents"]["title"] if item.get("documents") else "Unknown"
                
                events.append(TimelineEvent(
                    event_id=item["event_id"],
                    document_id=item["document_id"],
                    document_title=doc_title,
                    event_type=TimelineEventType(item["event_type"]),
                    event_date=datetime.combine(event_date, datetime.min.time()),
                    description=item["description"],
                    target_entities=item.get("target_entities", []),
                    industries=item_industries,
                    days_remaining=days_remaining,
                    is_critical=item.get("is_critical", False)
                ))
            except Exception as e:
                continue
        
        return events
    
    async def generate_ical(
        self,
        events: List[TimelineEvent]
    ) -> str:
        """Generate iCal format string for events."""
        
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//FSC Policy RAG//Timeline//KO",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:금융 정책 일정",
            "X-WR-TIMEZONE:Asia/Seoul"
        ]
        
        for event in events:
            event_date_str = event.event_date.strftime("%Y%m%d")
            
            uid = f"{event.event_id}@fsc-policy-rag"
            
            summary = f"[{event.event_type.value}] {event.description[:50]}"
            
            description = (
                f"문서: {event.document_title}\\n"
                f"유형: {event.event_type.value}\\n"
                f"대상: {', '.join(event.target_entities)}\\n"
                f"업권: {', '.join([i.value for i in event.industries])}"
            )
            
            priority = "1" if event.is_critical else "5"
            
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART;VALUE=DATE:{event_date_str}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                f"PRIORITY:{priority}",
                f"CATEGORIES:{event.event_type.value}",
                "END:VEVENT"
            ])
        
        lines.append("END:VCALENDAR")
        
        return "\r\n".join(lines)
    
    async def process_all_documents(self) -> int:
        """Process all unprocessed documents for timeline extraction."""
        
        existing_doc_ids = self.db.table("timeline_events").select(
            "document_id"
        ).execute()
        
        processed_ids = {item["document_id"] for item in existing_doc_ids.data} if existing_doc_ids.data else set()
        
        all_docs = self.db.table("documents").select("document_id").execute()
        
        processed_count = 0
        for doc in all_docs.data or []:
            if doc["document_id"] not in processed_ids:
                events = await self.extract_timeline_from_document(doc["document_id"])
                if events:
                    processed_count += 1
        
        return processed_count


_timeline_service: Optional[TimelineExtractorService] = None


def get_timeline_service() -> TimelineExtractorService:
    """Get singleton timeline service instance."""
    global _timeline_service
    if _timeline_service is None:
        _timeline_service = TimelineExtractorService()
    return _timeline_service
