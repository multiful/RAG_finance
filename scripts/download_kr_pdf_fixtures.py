#!/usr/bin/env python3
# ======================================================================
# FSC Policy RAG System | 스크립트: scripts/download_kr_pdf_fixtures.py
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, data/golden/parse/README.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""한국 금융·규제 성격 PDF 샘플 수집.

기본(`--mode regulatory`): 금융위 입법·정책 RSS + 공고 중 채용류 제외·규제 키워드 우선,
        보조로 국가법령정보센터 행정규칙 flDownload(고정 flSeq) 1건.
`--mode general`: 금융위 보도 PDF + 한국은행 보도 + 금감원 PDF(이전 동작).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "data" / "golden" / "parse" / "fixtures"
GOLDEN = ROOT / "data" / "golden" / "parse" / "golden_parse.jsonl"

TARGET_DEFAULT = 8

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# 채용·인사 공고 등 규제 문서에서 제외
_RECRUIT_MARKERS = (
    "채용",
    "공무원",
    "임기제",
    "경력경쟁",
    "모집",
    "선발",
    "응시",
    "전문임기",
    "국가공무원",
    "공직",
    "공고 제",
    "필기시험",
    "면접시험",
)

# 법령·규제·금융 정책 문서 우선순위(부분 문자열, 소문자 비교)
_REG_SCORE_KEYWORDS = (
    "고시",
    "시행령",
    "시행규칙",
    "법률",
    "입법",
    "입법예고",
    "개정",
    "훈령",
    "행정규칙",
    "지침",
    "규정",
    "금융",
    "은행",
    "보험",
    "증권",
    "투자",
    "자본시장",
    "금융투자",
    "여신",
    "외국환",
    "전자금융",
    "가상자산",
    "디지털자산",
    "파생",
    "불공정",
    "금융소비자",
    "분쟁",
    "해설",
    "유의사항",
    "설명자료",
    "안내서",
    "mou",
    "협약",
)

# 국가법령정보센터 LSW flDownload.flSeq (행정규칙·안내 PDF). 필요 시 추가 가능.
_LAW_GO_KR_FL_SEQS: tuple[tuple[str, str], ...] = (
    ("22317830", "국가법령정보센터 행정규칙 업무 종합안내 PDF(flDownload)"),
)


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(UA)
    return s


def is_pdf(data: bytes) -> bool:
    return len(data) > 500 and data.startswith(b"%PDF")


def download_pdf(
    sess: requests.Session,
    url: str,
    out: Path,
    referer: str,
) -> bool:
    try:
        r = sess.get(
            url,
            timeout=90,
            headers={"Referer": referer},
            allow_redirects=True,
        )
        r.raise_for_status()
        data = r.content
        if not is_pdf(data):
            return False
        out.write_bytes(data)
        return True
    except Exception as e:
        print("  DL fail", url[:90], e, file=sys.stderr)
        return False


def _recruit_block(title: str, pdf_labels: list[str]) -> bool:
    blob = (title + " " + " ".join(pdf_labels)).lower()
    return any(m.lower() in blob for m in _RECRUIT_MARKERS)


def _reg_score(title: str, pdf_label: str) -> int:
    blob = (title + " " + pdf_label).lower()
    return sum(1 for k in _REG_SCORE_KEYWORDS if k.lower() in blob)


def fsc_detail_pdf_links(html: str, page_url: str) -> list[tuple[str, str]]:
    """(절대 PDF URL, 첨부 파일명 라벨)"""
    base = "https://www.fsc.go.kr"
    soup = BeautifulSoup(html, "html.parser")
    out: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = unescape(a["href"])
        if "getfile" not in href.lower():
            continue
        par = a.parent
        extra = ""
        if par:
            extra = " ".join(
                x.get_text() or "" for x in par.find_all("span") if x != a
            )
        label = ((a.get_text() or "") + " " + extra).strip()
        if ".pdf" not in label.lower():
            continue
        full = href if href.startswith("http") else urljoin(base, href)
        out.append((full, label))
    return out


def collect_law_go_kr_fl_downloads(
    sess: requests.Session,
    max_n: int,
    seen: set[str],
    next_idx: list[int],
) -> list[tuple[str, str, str]]:
    """https://www.law.go.kr/LSW/flDownload.do?flSeq=…"""
    base = "https://www.law.go.kr/LSW"
    ref = f"{base}/admRulSc.do?menuId=5&subMenuId=41&tabMenuId=183"
    sess.get(ref, timeout=40)
    out: list[tuple[str, str, str]] = []
    for fl_seq, desc in _LAW_GO_KR_FL_SEQS:
        if len(out) >= max_n:
            break
        url = f"{base}/flDownload.do?flSeq={fl_seq}"
        if url in seen:
            continue
        next_idx[0] += 1
        fname = f"kr_{next_idx[0]:02d}.pdf"
        if download_pdf(sess, url, FIX / fname, referer=ref):
            seen.add(url)
            out.append((fname, url, desc))
            time.sleep(0.5)
    return out


def collect_fsc_regulatory_rss(
    sess: requests.Session,
    fids: tuple[str, ...],
    max_n: int,
    seen: set[str],
    next_idx: list[int],
) -> list[tuple[str, str, str]]:
    """RSS 상세에서 PDF 첨부 수집. fid 순서 고정(입법·공고 → 금융소비자). fid 내에서는 규제 키워드 점수순."""
    base = "https://www.fsc.go.kr"
    out: list[tuple[str, str, str]] = []

    for fid in fids:
        if len(out) >= max_n:
            break
        scored: list[tuple[int, str, str, str]] = []
        feed = feedparser.parse(f"{base}/about/fsc_bbs_rss/?fid={fid}")
        for e in feed.entries:
            link = getattr(e, "link", "") or ""
            if not link.startswith("http"):
                link = urljoin(base, link)
            title = e.get("title") or ""
            try:
                r = sess.get(link, timeout=45)
                r.raise_for_status()
            except Exception as ex:
                print("FSC skip", link[:70], ex, file=sys.stderr)
                time.sleep(0.25)
                continue
            pairs = fsc_detail_pdf_links(r.text, link)
            if not pairs:
                time.sleep(0.2)
                continue
            labels = [p[1] for p in pairs]
            if _recruit_block(title, labels):
                time.sleep(0.2)
                continue
            best_u, best_lab = max(
                pairs, key=lambda x: _reg_score(title, x[1])
            )
            sc = _reg_score(title, best_lab)
            scored.append((sc, link, best_u, best_lab))
            time.sleep(0.25)

        scored.sort(key=lambda x: (-x[0], x[1]))
        for sc, link, pdf_u, _lab in scored:
            if len(out) >= max_n:
                break
            if pdf_u in seen:
                continue
            next_idx[0] += 1
            fname = f"kr_{next_idx[0]:02d}.pdf"
            if download_pdf(sess, pdf_u, FIX / fname, referer=link):
                seen.add(pdf_u)
                src = f"금융위 RSS(규제·정책) fid={fid} score={sc}"
                out.append((fname, pdf_u, src))
                time.sleep(0.35)
    return out


def collect_fsc_rss_pdfs_any(
    sess: requests.Session,
    fids: tuple[str, ...],
    max_n: int,
    seen_urls: set[str],
    next_idx: list[int],
) -> list[tuple[str, str, str]]:
    """general 모드: 보도 RSS에서 PDF 첨부(기존 로직)."""
    base = "https://www.fsc.go.kr"
    out: list[tuple[str, str, str]] = []
    for fid in fids:
        if len(out) >= max_n:
            break
        feed = feedparser.parse(f"{base}/about/fsc_bbs_rss/?fid={fid}")
        for e in feed.entries:
            if len(out) >= max_n:
                break
            link = getattr(e, "link", "") or ""
            if not link.startswith("http"):
                link = urljoin(base, link)
            try:
                r = sess.get(link, timeout=40)
                r.raise_for_status()
            except Exception as ex:
                print("FSC skip", link[:60], ex, file=sys.stderr)
                time.sleep(0.3)
                continue
            for a in BeautifulSoup(r.text, "html.parser").find_all("a", href=True):
                href = unescape(a["href"])
                if "getfile" not in href.lower():
                    continue
                par = a.parent
                extra = ""
                if par:
                    extra = " ".join(
                        x.get_text() or "" for x in par.find_all("span") if x != a
                    )
                label = (a.get_text() or "") + " " + extra
                if ".pdf" not in label.lower():
                    continue
                full = href if href.startswith("http") else urljoin(base, href)
                if full in seen_urls:
                    continue
                next_idx[0] += 1
                fname = f"kr_{next_idx[0]:02d}.pdf"
                if download_pdf(sess, full, FIX / fname, referer=link):
                    seen_urls.add(full)
                    out.append((fname, full, f"금융위 RSS fid={fid}"))
                    time.sleep(0.35)
                    break
            time.sleep(0.25)
    return out


def list_bok_view_urls(sess: requests.Session, list_url: str) -> list[str]:
    r = sess.get(list_url, timeout=45)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    base = f"{urlparse(list_url).scheme}://{urlparse(list_url).netloc}"
    hrefs: list[str] = []
    for a in soup.select("a[href*='view.do']"):
        h = a.get("href") or ""
        if "nttId=" not in h:
            continue
        full = urljoin(base, h)
        if full not in hrefs:
            hrefs.append(full)
    return hrefs


def first_bok_pdf_path(html: str) -> str | None:
    m = re.search(r'["\'](/fileSrc/[^"\'\s<>]+\.pdf)["\']', html, re.I)
    if m:
        return m.group(1)
    m = re.search(r"file=%2F(fileSrc%2F[^&\"']+\.pdf)", html, re.I)
    if m:
        from urllib.parse import unquote

        return "/" + unquote(m.group(1)).lstrip("/")
    return None


def collect_bok_press_pdfs(
    sess: requests.Session,
    max_n: int,
    seen_urls: set[str],
    next_idx: list[int],
) -> list[tuple[str, str, str]]:
    base = "https://www.bok.or.kr"
    out: list[tuple[str, str, str]] = []
    for page in range(1, 6):
        if len(out) >= max_n:
            break
        list_url = (
            f"{base}/portal/bbs/B0000279/list.do?menuNo=200690&pageIndex={page}"
        )
        try:
            views = list_bok_view_urls(sess, list_url)
        except Exception as ex:
            print("BOK list fail", list_url, ex, file=sys.stderr)
            break
        for link in views:
            if len(out) >= max_n:
                break
            try:
                r = sess.get(link, timeout=45)
                r.raise_for_status()
            except Exception as ex:
                print("BOK skip", link, ex, file=sys.stderr)
                continue
            rel = first_bok_pdf_path(r.text)
            if not rel:
                continue
            full = urljoin(base, rel)
            if full in seen_urls:
                continue
            next_idx[0] += 1
            fname = f"kr_{next_idx[0]:02d}.pdf"
            if download_pdf(sess, full, FIX / fname, referer=link):
                seen_urls.add(full)
                out.append((fname, full, "한국은행 보도자료"))
                time.sleep(0.35)
    return out


def collect_fss_pdf_only_from_list(
    sess: requests.Session,
    max_n: int,
    seen_urls: set[str],
    next_idx: list[int],
) -> list[tuple[str, str, str]]:
    base = "https://www.fss.or.kr"
    list_url = f"{base}/fss/bbs/B0000110/list.do?menuNo=200138"
    out: list[tuple[str, str, str]] = []
    try:
        r = sess.get(list_url, timeout=35)
        r.raise_for_status()
    except Exception as ex:
        print("FSS list fail", ex, file=sys.stderr)
        return out
    paths = re.findall(
        r"/fss/cmmn/file/fileDown\.do\?[^\"'<> ]+",
        r.text,
        re.I,
    )
    for path in paths:
        if len(out) >= max_n:
            break
        full = urljoin(base, path)
        if full in seen_urls:
            continue
        next_idx[0] += 1
        fname = f"kr_{next_idx[0]:02d}.pdf"
        if download_pdf(sess, full, FIX / fname, referer=list_url):
            seen_urls.add(full)
            out.append((fname, full, "금감원 공지(첨부 PDF)"))
            time.sleep(0.4)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="한국 금융·규제 PDF fixtures 수집")
    ap.add_argument(
        "count",
        nargs="?",
        type=int,
        default=TARGET_DEFAULT,
        help="다운로드 개수 (기본 8)",
    )
    ap.add_argument(
        "--mode",
        choices=("regulatory", "general"),
        default="regulatory",
        help="regulatory=법·규제 형태 우선(기본), general=보도·은행 혼합",
    )
    args = ap.parse_args()
    target = max(1, min(30, args.count))

    FIX.mkdir(parents=True, exist_ok=True)
    sess = session()
    seen: set[str] = set()
    next_idx = [0]
    collected: list[tuple[str, str, str]] = []

    if args.mode == "regulatory":
        print("=== 국가법령정보센터 flDownload (행정규칙·안내 PDF) ===", file=sys.stderr)
        law_n = min(len(_LAW_GO_KR_FL_SEQS), max(0, target))
        collected.extend(
            collect_law_go_kr_fl_downloads(sess, law_n, seen, next_idx)
        )
        print("누적", len(collected), file=sys.stderr)

        need = target - len(collected)
        if need > 0:
            print(
                "=== 금융위 RSS (입법·공고 0111·0114, 채용 제외·규제 키워드 우선) ===",
                file=sys.stderr,
            )
            collected.extend(
                collect_fsc_regulatory_rss(
                    sess,
                    ("0111", "0114"),
                    need,
                    seen,
                    next_idx,
                )
            )
            print("누적", len(collected), file=sys.stderr)

        need = target - len(collected)
        if need > 0:
            print(
                "=== 금융위 RSS (보완: 금융소비자·유의사항 0112) ===",
                file=sys.stderr,
            )
            collected.extend(
                collect_fsc_regulatory_rss(
                    sess,
                    ("0112",),
                    need,
                    seen,
                    next_idx,
                )
            )
            print("누적", len(collected), file=sys.stderr)
    else:
        fsc_cap = max(1, min(4, target // 2 + 1))
        print("=== 금융위 RSS (보도·공고 PDF, 최대 %d) ===" % fsc_cap, file=sys.stderr)
        collected.extend(
            collect_fsc_rss_pdfs_any(sess, ("0114", "0111"), fsc_cap, seen, next_idx)
        )
        print("누적", len(collected), file=sys.stderr)

        need = target - len(collected)
        if need > 0:
            print("=== 한국은행 보도 ===", file=sys.stderr)
            collected.extend(collect_bok_press_pdfs(sess, need, seen, next_idx))
            print("누적", len(collected), file=sys.stderr)

        need = target - len(collected)
        if need > 0:
            print("=== 금감원 (PDF만) ===", file=sys.stderr)
            collected.extend(collect_fss_pdf_only_from_list(sess, need, seen, next_idx))
            print("누적", len(collected), file=sys.stderr)

    for fname, url, src in collected:
        print("OK", fname, "|", src)

    if len(collected) < target:
        print(
            "경고: 목표",
            target,
            "개 중",
            len(collected),
            "개만 저장했습니다.",
            file=sys.stderr,
        )

    lines = []
    for idx, (fname, url, src) in enumerate(collected, 1):
        rel = f"data/golden/parse/fixtures/{fname}"
        lines.append(
            {
                "id": f"kr-pdf-{idx:02d}",
                "file_path": rel,
                "file_type": "pdf",
                "notes": f"{src} — {url}",
                "reading_order_anchors": [],
                "table_gold": [],
                "structure_checks": [],
                "chunk_quality_unit_groups": [],
            }
        )
    GOLDEN.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )
    print("golden_parse.jsonl:", len(lines), "줄", file=sys.stderr)


if __name__ == "__main__":
    main()
