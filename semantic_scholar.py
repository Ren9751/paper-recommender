import requests


def fetch_citation_counts(papers: list[dict]) -> list[dict]:
    """arXiv IDのリストをSemantic Scholar APIに渡して引用数を取得する"""
    # arXiv IDを抽出（URLから末尾のIDだけ取り出す）
    arxiv_ids = []
    for p in papers:
        aid = p["arxiv_id"].split("/abs/")[-1]  # "2601.12345v1" の形式
        aid = aid.split("v")[0]                  # バージョン番号を除去 → "2601.12345"
        arxiv_ids.append(f"ArXiv:{aid}")

    try:
        res = requests.post(
            "https://api.semanticscholar.org/graph/v1/paper/batch",
            params={"fields": "citationCount"},
            json={"ids": arxiv_ids},
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()
    except Exception:
        # 失敗しても引用数なしで続行
        for p in papers:
            p["citation_count"] = 0
        return papers

    for i, p in enumerate(papers):
        entry = data[i] if i < len(data) else None
        if entry and entry.get("citationCount") is not None:
            p["citation_count"] = entry["citationCount"]
        else:
            p["citation_count"] = 0

    return papers
