import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

_cache = {}
CACHE_TTL_MINUTES = 60
ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
OPENSEARCH_NS = {"opensearch": "http://a9.com/-/spec/opensearch/1.1/"}
USER_AGENT = "paper-recommender/1.0"

PERIOD_DAYS = {"week": 7, "month": 30, "year": 365, "5year": 1825}

# arXivカテゴリでフィールドグループを定義
FIELD_GROUPS = {
    "cs": "cat:cs.*",
    "humanities": "cat:cs.CY",
    "all": None,
}


def _http_get(url: str, retries: int = 3) -> bytes | None:
    """arXiv API への HTTP GET。429（Rate Limit）に出会ったら短い待機をはさんでリトライする。
    成功時はレスポンス本文（bytes）、失敗時は None を返す。"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(3 * (attempt + 1))  # 指数的に待機を伸ばす
                continue
            return None
        except urllib.error.URLError:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return None
    return None


def _parse_arxiv_entry(entry) -> dict | None:
    """atom feed の <entry> タグを論文 dict に変換する。
    summary が無いエントリは return None で除外。"""
    title = (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip()
    summary = (entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "").strip()
    entry_id = (entry.findtext("atom:id", default="", namespaces=ATOM_NS) or "").strip()
    published = entry.findtext("atom:published", default="", namespaces=ATOM_NS) or ""
    authors = [
        (a.findtext("atom:name", default="", namespaces=ATOM_NS) or "")
        for a in entry.findall("atom:author", ATOM_NS)
    ]

    if not summary:
        return None

    submitted = ""
    if published:
        try:
            submitted = datetime.fromisoformat(published.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return {
        "arxiv_id": entry_id,
        "title": title,
        "abstract": summary,
        "authors": authors,
        "submitted": submitted,
    }


def _build_search_query(period: str, field_group: str, query: str, now: datetime) -> str:
    """arXiv API に渡す検索クエリ文字列を組み立てる。
    fetch_papers と fetch_total_count で共通利用するためのヘルパー。"""
    parts = []
    stripped = query.strip()
    if stripped:
        # arXivは "all:(A B)" の括弧構文が効かないため、単語ごとに all: を付けて AND 結合する
        parts.append(" AND ".join(f"all:{w}" for w in stripped.split()))
    fg_filter = FIELD_GROUPS.get(field_group, FIELD_GROUPS["cs"])
    if fg_filter:
        parts.append(fg_filter)
    if period != "all":
        days = PERIOD_DAYS.get(period, 7)
        start = (now - timedelta(days=days)).strftime("%Y%m%d%H%M")
        end = now.strftime("%Y%m%d%H%M")
        parts.append(f"submittedDate:[{start} TO {end}]")
    return " AND ".join(parts)


def is_cached(period: str, field_group: str = "cs", query: str = "") -> bool:
    cache_key = f"{period}:{field_group}:{query}"
    now = datetime.now(timezone.utc)
    return cache_key in _cache and _cache[cache_key]["expires"] > now


def fetch_total_count(period: str = "week", field_group: str = "cs", query: str = "") -> int:
    """arXiv API からこの検索条件にマッチする総件数を取得する。
    max_results=1 で問い合わせる（arXivは max_results=0 だと HTTP 500 を返す仕様）。
    返ってくる atom feed の <opensearch:totalResults> から件数だけを抜き出す。
    1時間キャッシュする。失敗時は 0 を返す（呼び出し側でフォールバック）。"""
    cache_key = f"total:{period}:{field_group}:{query}"
    now = datetime.now(timezone.utc)

    cached = _cache.get(cache_key)
    if cached and cached["expires"] > now:
        return cached["count"]

    search_query = _build_search_query(period, field_group, query, now)
    params = urllib.parse.urlencode({"search_query": search_query, "max_results": 1})
    url = f"{ARXIV_API_URL}?{params}"

    count = 0
    xml_data = _http_get(url)
    if xml_data is not None:
        try:
            root = ET.fromstring(xml_data)
            total_elem = root.find("opensearch:totalResults", OPENSEARCH_NS)
            if total_elem is not None and total_elem.text:
                count = int(total_elem.text)
        except (ET.ParseError, ValueError):
            pass

    _cache[cache_key] = {"count": count, "expires": now + timedelta(minutes=CACHE_TTL_MINUTES)}
    return count


def fetch_papers(period: str = "week", max_results: int = 40, field_group: str = "cs", query: str = "", offset: int = 0) -> list[dict]:
    """指定 offset から最大 max_results 件の論文を取得する。
    arXiv API の start パラメータを直接使うので、何ページ目だろうと1回の HTTP で済む。"""
    cache_key = f"papers:{period}:{field_group}:{query}:{offset}:{max_results}"
    now = datetime.now(timezone.utc)

    cached = _cache.get(cache_key)
    if cached and cached["expires"] > now:
        return cached["papers"]

    search_query = _build_search_query(period, field_group, query, now)
    params = urllib.parse.urlencode({
        "search_query": search_query,
        "start": offset,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = f"{ARXIV_API_URL}?{params}"

    papers = []
    xml_data = _http_get(url)
    if xml_data is not None:
        try:
            root = ET.fromstring(xml_data)
            for entry in root.findall("atom:entry", ATOM_NS):
                paper = _parse_arxiv_entry(entry)
                if paper:
                    papers.append(paper)
        except ET.ParseError:
            pass

    _cache[cache_key] = {"papers": papers, "expires": now + timedelta(minutes=CACHE_TTL_MINUTES)}
    return papers
