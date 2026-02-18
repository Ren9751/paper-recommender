import arxiv
from datetime import datetime, timedelta, timezone

_cache = {}  # key: (category, period) -> {"papers": [...], "expires": datetime}
CACHE_TTL_MINUTES = 60

PERIOD_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}
# 期間ごとに取得する最大件数（多めに取ってPythonで絞る）
FETCH_MAX = {"day": 40, "week": 40, "month": 40, "year": 40}


def fetch_papers(category: str = "cs.CY", max_results: int = 30, period: str = "week") -> list[dict]:
    cache_key = (category, period)
    now = datetime.now(timezone.utc)

    if cache_key in _cache and _cache[cache_key]["expires"] > now:
        return _cache[cache_key]["papers"]

    days = PERIOD_DAYS.get(period, 7)
    cutoff = now - timedelta(days=days)
    fetch_count = FETCH_MAX.get(period, 100)

    client = arxiv.Client(delay_seconds=3, num_retries=3)
    search = arxiv.Search(
        query=f"cat:{category}",
        max_results=fetch_count,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )

    papers = []
    for result in client.results(search):
        if result.published and result.published < cutoff:
            break  # 最新順なので、cutoffより古くなったら終了
        papers.append({
            "arxiv_id": result.entry_id,
            "title": result.title,
            "abstract": result.summary,
            "authors": [a.name for a in result.authors],
            "submitted": result.published.strftime("%Y-%m-%d") if result.published else "",
        })

    _cache[cache_key] = {"papers": papers, "expires": now + timedelta(minutes=CACHE_TTL_MINUTES)}
    return papers
