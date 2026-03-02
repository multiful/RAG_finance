"""
DB 시드 스크립트 — sources, documents, gap_map_scores 샘플 데이터 삽입.
실행: app/backend 폴더에서
  python -m scripts.seed_data
또는
  uv run python -m scripts.seed_data
.env에 SUPABASE_URL, SUPABASE_SERVICE_KEY 설정 필요.
"""
import os
import sys
import hashlib
from datetime import datetime, timedelta, timezone

# backend 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.core.config import settings
from app.constants.risk_axes import RISK_AXIS_INITIAL_GI_LC

RSS_NAMES = {"0111": "보도자료", "0112": "보도설명", "0114": "공지사항", "0113": "행사/채용안내", "0115": "정책자료", "0411": "카드뉴스"}


def seed_sources(db):
    """sources 테이블에 FSC RSS 소스 삽입 (없으면)."""
    existing = db.table("sources").select("source_id, fid").execute()
    have_fids = {r["fid"] for r in (existing.data or [])}
    inserted = 0
    for fid in settings.FSC_RSS_FIDS:
        if fid in have_fids:
            continue
        name = RSS_NAMES.get(fid, f"금융위원회({fid})")
        db.table("sources").insert({
            "name": name,
            "type": "rss",
            "base_url": settings.FSC_RSS_BASE,
            "fid": fid,
            "active": True,
        }).execute()
        inserted += 1
        print(f"  Inserted source fid={fid} ({name})")
    return inserted


def seed_documents(db):
    """documents 테이블에 샘플 문서 삽입 (url 기준 upsert)."""
    sources = db.table("sources").select("source_id, fid").in_("fid", settings.FSC_RSS_FIDS).execute()
    if not sources.data:
        print("  No sources found. Run seed_sources first.")
        return 0
    source_id = sources.data[0]["source_id"]
    now = datetime.now(timezone.utc)
    # (제목, 카테고리, 인덱스, raw_text 요약) — 규제 시뮬레이션 본문 폴백용
    docs = [
        ("스테이블코인 발행·유통 가이드라인 개정안 시행", "보도자료", 0,
         "스테이블코인 발행·유통 가이드라인 개정안이 시행됩니다. 가상자산과 연계된 스테이블코인에 대한 금융당국 규제 방향, 준비자산 요건, 발행자 의무사항을 담고 있습니다."),
        ("2024년 금융규제 개혁 로드맵 공지", "공지사항", 1,
         "2024년 금융규제 개혁 로드맵을 공지합니다. 디지털자산·스테이블코인·토큰증권(STO) 관련 제도 정비 방향이 포함됩니다."),
        ("금융소비자보호법 시행령 개정", "정책자료", 2,
         "금융소비자보호법 시행령 개정. 금융상품 판매 시 설명의무, 스테이블코인 등 디지털자산 관련 소비자 보호 조항을 강화합니다."),
        ("디지털자산 사업자 신고 안내", "보도설명", 3,
         "디지털자산 사업자 신고 안내. 가상자산·스테이블코인 사업자를 위한 신고 절차, 제출 서류, 유의사항을 안내합니다."),
        ("금융감독 정책방향 설명회 개최", "행사/채용안내", 4,
         "금융감독 정책방향 설명회를 개최합니다. 스테이블코인·STO 규제 동향, 국제기구 권고 반영 계획을 설명합니다."),
        ("보험업 디지털 전환 가이드라인", "보도자료", 5,
         "보험업 디지털 전환 가이드라인. 보험업계의 디지털 자산·블록체인 활용 방향을 담았습니다."),
        ("은행 BIS 자본규제 대응 안내", "공지사항", 6,
         "은행의 BIS 자본규제 대응 안내. 크립토자산 노출에 대한 자본 요구사항, 스테이블코인 관련 리스크 반영을 설명합니다."),
        ("증권사 전자공시 의무 강화", "정책자료", 7,
         "증권사 전자공시 의무 강화. 토큰증권(STO) 등 디지털 증권 공시 기준이 포함됩니다."),
        ("FSB Policy Documents on Stablecoins and Crypto Assets", "FSB Policy Documents", 8,
         "FSB policy on stablecoins and crypto assets. High-level recommendations on regulation of global stablecoins, reserve requirements, and cross-border cooperation."),
        ("BIS Research on Tokenised Securities and STO", "BIS Research Papers", 9,
         "BIS research on tokenised securities and STO. Analysis of security token offerings, DLT-based settlement, and regulatory implications for stablecoins and tokenised assets."),
    ]
    # 시드 문서용 URL: 실제 페이지(공지 목록) + fragment로 고유 유지. 기존 fsc.go.kr/seed/doc/{i}는 404 발생.
    FSC_NOTICE_LIST = "https://www.fsc.go.kr/po/info/ntc/"
    rows = []
    for item in docs:
        title, category, i = item[0], item[1], item[2]
        raw = item[3] if len(item) > 3 else title
        url = f"{FSC_NOTICE_LIST}#seed-{i}"  # 고유 URL, 클릭 시 공지 목록 페이지로 이동
        h = hashlib.sha256(url.encode()).hexdigest()[:32]
        rows.append({
            "source_id": source_id,
            "title": title,
            "published_at": (now - timedelta(days=i)).isoformat(),
            "url": url,
            "category": category,
            "hash": h,
            "status": "indexed",
            "raw_text": raw,
        })
    db.table("documents").upsert(rows, on_conflict="url").execute()
    print(f"  Upserted {len(rows)} documents")
    return len(rows)


def seed_gap_map_scores(db):
    """gap_map_scores 테이블에 R1~R10 초기값 삽입."""
    rows = [
        {"axis_id": r["axis_id"], "gi": r["gi"], "lc": r["lc"]}
        for r in RISK_AXIS_INITIAL_GI_LC
    ]
    db.table("gap_map_scores").upsert(rows, on_conflict="axis_id").execute()
    print(f"  Upserted {len(rows)} gap_map_scores")
    return len(rows)


def main():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        print("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        sys.exit(1)
    db = get_db()
    print("Seeding sources...")
    seed_sources(db)
    print("Seeding documents...")
    seed_documents(db)
    print("Seeding gap_map_scores...")
    seed_gap_map_scores(db)
    print("Done.")


if __name__ == "__main__":
    main()
