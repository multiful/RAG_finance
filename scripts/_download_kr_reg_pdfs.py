# ======================================================================
# FSC Policy RAG System | 스크립트: scripts/_download_kr_reg_pdfs.py
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, data/golden/parse/README.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""레거시: FSS 공지 5건 시도. 신규는 `download_kr_pdf_fixtures.py` 사용."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "data" / "golden" / "parse" / "fixtures"
BASE = "https://www.fss.or.kr"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    sess.headers.update(UA)

    list_url = f"{BASE}/fss/bbs/B0000110/list.do?menuNo=200138"
    r = sess.get(list_url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select("table.bd_list tbody tr")
    detail_urls: list[str] = []
    for row in rows:
        if row.get("class") and "notice" in " ".join(row.get("class") or []):
            continue
        a = row.select_one("td.subject a, td.title a")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        detail = href if href.startswith("http") else BASE + href
        if detail not in detail_urls:
            detail_urls.append(detail)
        if len(detail_urls) >= 12:
            break

    saved: list[tuple[str, str]] = []  # (fixture_name, source_url)
    for i, du in enumerate(detail_urls):
        if len(saved) >= 5:
            break
        try:
            dr = sess.get(du, timeout=30)
            dr.raise_for_status()
        except Exception as e:
            print("skip detail", du, e, file=sys.stderr)
            continue
        dsoup = BeautifulSoup(dr.text, "html.parser")
        # fileDown links (relative)
        for a in dsoup.find_all("a", href=True):
            href = a["href"]
            if "fileDown.do" not in href and "FileDown.do" not in href:
                continue
            if href.startswith("/"):
                full = BASE + href
            elif href.startswith("http"):
                full = href
            else:
                full = BASE + "/" + href.lstrip("/")
            fname = f"fss_notice_{len(saved)+1:02d}.pdf"
            out = FIX / fname
            try:
                pr = sess.get(full, timeout=60)
                pr.raise_for_status()
                ct = (pr.headers.get("content-type") or "").lower()
                data = pr.content
                if len(data) < 500:
                    continue
                if "pdf" not in ct and not data.startswith(b"%PDF"):
                    continue
                out.write_bytes(data)
                saved.append((f"data/golden/parse/fixtures/{fname}", full))
                print("saved", fname, "from", full[:80])
                break
            except Exception as e:
                print("dl fail", full, e, file=sys.stderr)

    if len(saved) < 5:
        print("Need fallback: only got", len(saved), file=sys.stderr)

    # Write golden_parse.jsonl lines (minimal)
    golden = ROOT / "data" / "golden" / "parse" / "golden_parse.jsonl"
    lines = []
    for idx, (rel, src) in enumerate(saved, 1):
        lines.append(
            {
                "id": f"kr-reg-pdf-{idx:02d}",
                "file_path": rel.replace("\\", "/"),
                "file_type": "pdf",
                "notes": f"FSS 공지 첨부 샘플 — source: {src}",
                "reading_order_anchors": [],
                "table_gold": [],
                "structure_checks": [],
                "chunk_quality_unit_groups": [],
            }
        )
    golden.write_text(
        "\n".join(__import__("json").dumps(x, ensure_ascii=False) for x in lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )
    print("golden_parse.jsonl entries:", len(lines))


if __name__ == "__main__":
    main()
