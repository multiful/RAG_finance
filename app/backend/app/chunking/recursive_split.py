"""문맥 보존 재귀 청킹 — 규제 문서(한글·조문·표)에 맞춘 구분자 우선순위."""
from __future__ import annotations

from typing import List, Tuple

from app.core.config import settings


# 금융·규제 텍스트: 큰 단위 → 작은 단위 순으로 분할 시도
_DEFAULT_SEPARATORS: List[str] = [
    "\n\n\n",
    "\n\n",
    "\n",
    "。",
    ". ",
    "다.",
    "요.",
    "음.",
    "함.",
    " ",
    "",
]


def get_recursive_splitter(
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
):
    """LangChain RecursiveCharacterTextSplitter (문자 길이 기준)."""
    size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
    overlap = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=min(overlap, size // 2),
        separators=_DEFAULT_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


def split_text_recursive(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> List[str]:
    """전체 텍스트를 재귀 분할. 실패 시 고정 길이 윈도 폴백."""
    if not (text or "").strip():
        return []
    size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
    overlap = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP
    try:
        splitter = get_recursive_splitter(size, overlap)
        parts = splitter.split_text(text.strip())
        return [p for p in parts if p.strip()]
    except Exception:
        return _fallback_char_windows(text.strip(), size, overlap)


def _fallback_char_windows(text: str, size: int, overlap: int) -> List[str]:
    """LangChain 없을 때 문자 단위 슬라이딩."""
    if size <= 0:
        return [text]
    out: List[str] = []
    step = max(1, size - overlap)
    for i in range(0, len(text), step):
        chunk = text[i : i + size]
        if chunk.strip():
            out.append(chunk)
        if i + size >= len(text):
            break
    return out


def split_with_section_hints(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> List[Tuple[str, str | None]]:
    """섹션 헤더(##) 단위로 먼저 나눈 뒤, 긴 블록만 재귀 분할. 반환: (chunk_text, section_title)."""
    import re

    if not (text or "").strip():
        return []
    size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
    overlap = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP

    # 페이지/섹션 경계
    parts = re.split(r"(?m)^(?=#+\s)", text)
    results: List[Tuple[str, str | None]] = []

    for raw in parts:
        block = raw.strip()
        if not block:
            continue
        title: str | None = None
        if block.startswith("#"):
            lines = block.split("\n", 1)
            if len(lines) == 2:
                title = lines[0].lstrip("#").strip()[:200]
                body = lines[1].strip()
            else:
                body = block
        else:
            body = block

        if len(body) <= size * 1.15:
            prefix = f"[{title}]\n" if title else ""
            results.append((prefix + body, title))
            continue

        sub = split_text_recursive(body, size, overlap)
        for j, s in enumerate(sub):
            prefix = f"[{title}] " if title and j == 0 else (f"[{title}] …\n" if title and j > 0 else "")
            results.append((prefix + s, title))

    if not results:
        for s in split_text_recursive(text, size, overlap):
            results.append((s, None))
    return results
