# ======================================================================
# FSC Policy RAG System | 모듈: app.evaluation.pdf_parse_metrics
# 최종 수정일: 2026-04-07
# 연관 문서: RAG_PIPELINE.md, EVALUATION_GUIDELINE.md, data/golden/parse/README.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""PDF 문서 특성 지표(텍스트 레이어·레이아웃·표·제목 패턴·OCR·파서 실패율).

골든셋 노트북·배치 평가에서 재사용한다. 값은 휴리스틱이며 절대 진리가 아니다.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pdfplumber

_log = logging.getLogger(__name__)

_MIN_TEXT_CHARS_PER_PAGE = 40


def _full_text_fitz(doc: fitz.Document) -> str:
    parts: list[str] = []
    for i in range(doc.page_count):
        parts.append(doc[i].get_text("text") or "")
    return "\n".join(parts)


def text_layer_ratio(doc: fitz.Document) -> float:
    """텍스트 레이어가 ‘충분한’ 문자를 내는 페이지 비율."""
    if doc.page_count == 0:
        return 0.0
    ok = 0
    for i in range(doc.page_count):
        t = (doc[i].get_text("text") or "").strip()
        if len(t) >= _MIN_TEXT_CHARS_PER_PAGE:
            ok += 1
    return ok / doc.page_count


def chars_per_page(doc: fitz.Document) -> float:
    total = sum(len((doc[i].get_text("text") or "")) for i in range(doc.page_count))
    return total / max(1, doc.page_count)


def image_area_ratio(doc: fitz.Document, max_pages: int = 40) -> float:
    """페이지당 이미지 바운딩 박스 면적 합 / 페이지 면적 의 평균."""
    ratios: list[float] = []
    n = min(doc.page_count, max_pages)
    for i in range(n):
        page = doc[i]
        pr = page.rect
        page_area = float(pr.width * pr.height) or 1.0
        img_area = 0.0
        for img in page.get_images(full=True):
            try:
                xref = img[0]
                rects = page.get_image_rects(xref)
                for r in rects:
                    img_area += float(r.width * r.height)
            except Exception:
                continue
        ratios.append(min(1.0, img_area / page_area))
    return sum(ratios) / max(1, len(ratios))


def multi_column_score(doc: fitz.Document, max_pages: int = 40) -> float:
    """라인 시작 x 좌표가 좌·우 두 띠로 나뉘는 정도(0~1)."""
    scores: list[float] = []
    n = min(doc.page_count, max_pages)
    for i in range(n):
        page = doc[i]
        d = page.get_text("dict")
        x0s: list[float] = []
        for b in d.get("blocks", []):
            if b.get("type") != 0:
                continue
            for line in b.get("lines", []):
                bb = line.get("bbox")
                if bb:
                    x0s.append(float(bb[0]))
        if len(x0s) < 12:
            scores.append(0.0)
            continue
        w = float(page.rect.width) or 1.0
        left = sum(1 for x in x0s if x < w * 0.42)
        right = sum(1 for x in x0s if x > w * 0.48)
        thr = max(4, int(len(x0s) * 0.12))
        if left >= thr and right >= thr:
            scores.append(1.0)
        else:
            scores.append(min(1.0, (left + right) / len(x0s)))
    return sum(scores) / max(1, len(scores))


def table_density(path: Path) -> float:
    """pdfplumber 표 개수 / 페이지."""
    try:
        with pdfplumber.open(path) as pdf:
            n_pages = len(pdf.pages)
            if n_pages == 0:
                return 0.0
            n_tables = 0
            for p in pdf.pages:
                try:
                    ts = p.extract_tables() or []
                    n_tables += len(ts)
                except Exception:
                    continue
            return n_tables / n_pages
    except Exception as e:
        _log.warning("table_density fail %s: %s", path, e)
        return 0.0


def heading_pattern_score(text: str) -> float:
    """조·항·번호 목차형 문자열 밀도를 0~1로 스케일."""
    sample = text[:80000]
    if not sample.strip():
        return 0.0
    patterns = [
        r"제\s*\d+\s*[조장절편]",
        r"(?m)^\s*\d+\.\s+",
        r"[가나다라마바사아자차카타파하]\.\s",
        r"\[[^\]]{2,40}\]",
    ]
    hits = sum(len(re.findall(p, sample)) for p in patterns)
    # 경험적 스케일: 보도자료 20~80, 법령 100+
    raw = hits / max(1, len(sample) / 2000)
    return float(max(0.0, min(1.0, raw)))


def parse_fail_rate(path: Path, doc: fitz.Document) -> float:
    """페이지별 pdfplumber 추출 실패(빈 텍스트·예외) 비율."""
    n = doc.page_count
    if n == 0:
        return 1.0
    failed = 0
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    t = page.extract_text()
                    if not (t or "").strip():
                        failed += 1
                except Exception:
                    failed += 1
    except Exception:
        return 1.0
    return failed / n


def ocr_confidence_optional(path: Path, doc: fitz.Document) -> float | None:
    """텍스트가 얇은 페이지에 대해 Tesseract 평균 신뢰도. 미설치 시 None.

    대형 PDF에서 시간이 과도해지지 않도록 얇은 페이지 최대 3장만 샘플한다.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return None

    confs: list[float] = []
    mat = fitz.Matrix(1.5, 1.5)
    ocr_pages = 0
    max_ocr_pages = 3
    for i in range(doc.page_count):
        if ocr_pages >= max_ocr_pages:
            break
        t = (doc[i].get_text("text") or "").strip()
        if len(t) >= _MIN_TEXT_CHARS_PER_PAGE:
            continue
        ocr_pages += 1
        try:
            pix = doc[i].get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            data = pytesseract.image_to_data(img, lang="kor+eng", output_type=pytesseract.Output.DICT)
            for conf in data.get("conf", []):
                try:
                    c = float(conf)
                    if c >= 0:
                        confs.append(c)
                except (TypeError, ValueError):
                    continue
        except Exception as e:
            _log.debug("ocr page %s skip: %s", i, e)
            continue
    if not confs:
        return None
    return float(sum(confs) / len(confs))


def collect_pdf_metrics(path: Path) -> dict[str, Any]:
    """단일 PDF에 대한 지표 딕셔너리."""
    path = path.resolve()
    doc = fitz.open(path)
    try:
        text = _full_text_fitz(doc)
        row: dict[str, Any] = {
            "file": path.name,
            "page_count": doc.page_count,
            "text_layer_ratio": round(text_layer_ratio(doc), 4),
            "chars_per_page": round(chars_per_page(doc), 1),
            "image_area_ratio": round(image_area_ratio(doc), 4),
            "multi_column_score": round(multi_column_score(doc), 4),
            "table_density": round(table_density(path), 4),
            "heading_pattern_score": round(heading_pattern_score(text), 4),
            "parse_fail_rate": round(parse_fail_rate(path, doc), 4),
        }
        ocr = ocr_confidence_optional(path, doc)
        row["ocr_confidence"] = None if ocr is None else round(ocr, 2)
        return row
    finally:
        doc.close()

