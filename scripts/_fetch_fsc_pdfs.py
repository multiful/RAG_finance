"""Find PDF links: RSS entry pages + direct crawl."""
import re
import feedparser
import requests

BASE = "https://www.fsc.go.kr/about/fsc_bbs_rss/"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
sess = requests.Session()
sess.headers.update(UA)

pdfs = []
for fid in ["0114", "0111"]:
    url = BASE + "?fid=" + fid
    f = feedparser.parse(url)
    for e in f.entries[:15]:
        link = e.get("link")
        if not link:
            continue
        if not link.startswith("http"):
            link = "https://www.fsc.go.kr" + link
        try:
            r = sess.get(link, timeout=15)
            r.raise_for_status()
            found = re.findall(r"https?://[^\s\"'<>]+\.pdf", r.text, re.I)
            found += re.findall(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', r.text, re.I)
            for p in found:
                if p.startswith("/"):
                    p = "https://www.fsc.go.kr" + p
                if p not in pdfs:
                    pdfs.append(p)
        except Exception as ex:
            print("err", link, ex)
        if len(pdfs) >= 8:
            break
    if len(pdfs) >= 8:
        break

print("total", len(pdfs))
for p in pdfs:
    print(p)
