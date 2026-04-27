import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import arxiv

_cache = {}
CACHE_TTL_MINUTES = 60
ARXIV_API_URL = "http://export.arxiv.org/api/query"

PERIOD_DAYS = {"week": 7, "month": 30, "year": 365, "5year": 1825}

# arXivカテゴリでフィールドグループを定義
FIELD_GROUPS = {
    "cs": "cat:cs.*",
    "humanities": "cat:cs.CY",
    "all": None,
}

_client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=3)


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
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "paper-recommender/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        ns = {"opensearch": "http://a9.com/-/spec/opensearch/1.1/"}
        total_elem = root.find("opensearch:totalResults", ns)
        if total_elem is not None and total_elem.text:
            count = int(total_elem.text)
    except (urllib.error.URLError, ET.ParseError, ValueError):
        count = 0

    _cache[cache_key] = {"count": count, "expires": now + timedelta(minutes=CACHE_TTL_MINUTES)}
    return count


def fetch_papers(period: str = "week", max_results: int = 40, field_group: str = "cs", query: str = "") -> list[dict]:
    cache_key = f"{period}:{field_group}:{query}"
    now = datetime.now(timezone.utc)

    cached = _cache.get(cache_key)
    if cached and cached["expires"] > now:
        # 必要件数を満たしている、または arXiv 側を出し切っているならキャッシュから返す
        if len(cached["papers"]) >= max_results or cached["exhausted"]:
            return cached["papers"][:max_results]

    search_query = _build_search_query(period, field_group, query, now)

    search = arxiv.Search(
        query=search_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    papers = []
    for r in _client.results(search):
        if not r.summary:
            continue
        papers.append({
            "arxiv_id": r.entry_id,
            "title": r.title.strip(),
            "abstract": r.summary.strip(),
            "authors": [a.name for a in r.authors],
            "submitted": r.published.strftime("%Y-%m-%d") if r.published else "",
        })

    # 要求より少なく返ってきたら arXiv 側にもうこれ以上ない、と判定
    exhausted = len(papers) < max_results
    _cache[cache_key] = {
        "papers": papers,
        "expires": now + timedelta(minutes=CACHE_TTL_MINUTES),
        "exhausted": exhausted,
    }
    return papers
