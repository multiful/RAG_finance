# ======================================================================
# FSC Policy RAG System | 스크립트: scripts/_probe_fss_pdf.py
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, scripts/_download_kr_reg_pdfs.py
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

import re
import requests

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}
url = "https://www.fss.or.kr/fss/bbs/B0000110/list.do?menuNo=200138"
r = requests.get(url, headers=UA, timeout=25)
print("status", r.status_code, "len", len(r.text))
# FSS often /fss/cmm/fms/FileDown.do or attach
for pat in [r"FileDown\.do\?[^\"'<> ]+", r"https?://[^\"'<> ]+\.pdf", r"/fss/[^\"'<> ]+\.pdf"]:
    m = re.findall(pat, r.text, re.I)
    print(pat, "->", len(m), m[:3])
