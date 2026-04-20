import arxiv
from datetime import datetime, timedelta, timezone

_cache = {}
CACHE_TTL_MINUTES = 60

PERIOD_DAYS = {"week": 7, "month": 30, "year": 365, "5year": 1825}

DEFAULT_QUERY = "AI ethics society technology policy"

# arXivカテゴリでフィールドグループを定義
# arXivに人文系は少ないため humanities は社会・経済系カテゴリで近似
FIELD_GROUPS = {
    "cs": "cat:cs.*",
    "humanities": "(cat:cs.CY OR cat:econ.* OR cat:q-fin.* OR cat:stat.AP)",
    "all": None,
}

_client = arxiv.Client(page_size=40, delay_seconds=3, num_retries=3)


def is_cached(period: str, field_group: str = "cs", query: str = "") -> bool:
    cache_key = f"{period}:{field_group}:{query}"
    now = datetime.now(timezone.utc)
    return cache_key in _cache and _cache[cache_key]["expires"] > now


def fetch_papers(period: str = "week", max_results: int = 40, field_group: str = "cs", query: str = "") -> list[dict]:
    cache_key = f"{period}:{field_group}:{query}"
    now = datetime.now(timezone.utc)

    if cache_key in _cache and _cache[cache_key]["expires"] > now:
        return _cache[cache_key]["papers"]

    actual_query = query.strip() if query.strip() else DEFAULT_QUERY

    parts = [f"all:({actual_query})"]
    fg_filter = FIELD_GROUPS.get(field_group, FIELD_GROUPS["cs"])
    if fg_filter:
        parts.append(fg_filter)
    if period != "all":
        days = PERIOD_DAYS.get(period, 7)
        start = (now - timedelta(days=days)).strftime("%Y%m%d%H%M")
        end = now.strftime("%Y%m%d%H%M")
        parts.append(f"submittedDate:[{start} TO {end}]")

    search_query = " AND ".join(parts)

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

    _cache[cache_key] = {"papers": papers, "expires": now + timedelta(minutes=CACHE_TTL_MINUTES)}
    return papers
