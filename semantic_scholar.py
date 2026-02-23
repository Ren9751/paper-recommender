import os
import requests
from datetime import datetime, timedelta, timezone

_cache = {}
CACHE_TTL_MINUTES = 60

PERIOD_DAYS = {"week": 7, "month": 30, "year": 365, "5year": 1825}

# Semantic Scholar fieldsOfStudy 値のグループ定義
FIELD_GROUPS = {
    "cs": "Computer Science",
    "humanities": "Philosophy,Law,Sociology,Political Science,History,Economics,Psychology",
    "all": "Computer Science,Philosophy,Law,Sociology,Political Science,History,Economics,Psychology",
}

def _api_headers() -> dict:
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    return {"x-api-key": key} if key else {}


def is_cached(period: str, field_group: str = "cs") -> bool:
    cache_key = f"{period}:{field_group}"
    now = datetime.now(timezone.utc)
    return cache_key in _cache and _cache[cache_key]["expires"] > now


def fetch_papers(period: str = "week", max_results: int = 40, field_group: str = "cs") -> list[dict]:
    cache_key = f"{period}:{field_group}"
    now = datetime.now(timezone.utc)

    if cache_key in _cache and _cache[cache_key]["expires"] > now:
        return _cache[cache_key]["papers"]

    fields_of_study = FIELD_GROUPS.get(field_group, FIELD_GROUPS["cs"])

    params = {
        "query": "AI ethics society technology policy",
        "fieldsOfStudy": fields_of_study,
        "fields": "title,abstract,authors,publicationDate,externalIds,citationCount",
        "limit": max_results,
        "sort": "publicationDate:desc",
    }
    if period != "all":
        days = PERIOD_DAYS.get(period, 7)
        start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        params["publicationDateOrYear"] = f"{start_date}:{end_date}"

    res = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        headers=_api_headers(),
        params=params,
        timeout=15,
    )
    res.raise_for_status()
    data = res.json().get("data", [])

    papers = []
    for item in data:
        if not item.get("abstract"):
            continue
        arxiv_id = ""
        if item.get("externalIds", {}).get("ArXiv"):
            arxiv_id = "https://arxiv.org/abs/" + item["externalIds"]["ArXiv"]

        papers.append({
            "arxiv_id": arxiv_id,
            "ss_id": item.get("paperId", ""),
            "title": item.get("title", ""),
            "abstract": item.get("abstract", ""),
            "authors": [a["name"] for a in item.get("authors", [])],
            "submitted": item.get("publicationDate", ""),
            "citation_count": item.get("citationCount", 0),
        })

    _cache[cache_key] = {"papers": papers, "expires": now + timedelta(minutes=CACHE_TTL_MINUTES)}
    return papers


def get_field_groups() -> dict:
    """利用可能なフィールドグループの定義を返す（app.py / テンプレート用）。"""
    return FIELD_GROUPS
