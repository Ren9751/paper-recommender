import math
import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify
from arxiv_source import fetch_papers, fetch_total_count, is_cached

app = Flask(__name__)

PERIODS = {
    "week":  "1週間",
    "month": "1ヶ月",
    "year":  "1年",
    "5year": "5年",
    "all":   "全期間",
}

FIELD_GROUP_LABELS = {
    "cs":         "CS",
    "humanities": "社会",
    "all":        "全分野",
}

PAGE_SIZE = 40


def build_pagination_window(current: int, total: int, around: int = 2) -> list:
    """ハイブリッド省略表示のページ番号リストを返す。
    ・総ページが7以下なら全ページ表示
    ・現在ページの前後 around 個を必ず含める
    ・1ページ目と最終ページは常に含める
    ・離れている部分は '...' でつなぐ
    例: current=10, total=36 → [1, '...', 8, 9, 10, 11, 12, '...', 36]"""
    if total <= 1:
        return [1] if total == 1 else []
    if total <= 7:
        return list(range(1, total + 1))

    pages = [1]
    start = max(2, current - around)
    end = min(total - 1, current + around)

    if start > 2:
        pages.append("...")
    pages.extend(range(start, end + 1))
    if end < total - 1:
        pages.append("...")
    pages.append(total)
    return pages


@app.route("/")
def index():
    period = request.args.get("period", "week")
    sort = request.args.get("sort", "new")
    field_group = request.args.get("field_group", "cs")
    query = request.args.get("query", "")

    try:
        page = max(1, int(request.args.get("page", "1")))
    except (TypeError, ValueError):
        page = 1

    if period not in PERIODS:
        period = "week"
    if field_group not in FIELD_GROUP_LABELS:
        field_group = "cs"

    cached = is_cached(period, field_group, query)

    # 総件数を先に取って総ページ数を計算（失敗時は0）
    total_count = fetch_total_count(period=period, field_group=field_group, query=query)
    total_pages = math.ceil(total_count / PAGE_SIZE) if total_count > 0 else 0

    # 不正なページ番号は1にクランプ（総ページ数を超えていてもそのまま受け入れて空表示）
    if total_pages > 0 and page > total_pages:
        page = total_pages

    # 「次ページがあるか」のフォールバック判定用に1件多く要求する
    all_papers = fetch_papers(
        period=period,
        max_results=page * PAGE_SIZE + 1,
        field_group=field_group,
        query=query,
    )

    start = (page - 1) * PAGE_SIZE
    end = page * PAGE_SIZE
    papers = all_papers[start:end]

    if total_pages > 0:
        has_next = page < total_pages
        has_prev = page > 1
    else:
        # 総件数が取れなかった場合は累積取得結果から推定
        has_next = len(all_papers) > end
        has_prev = page > 1

    page_numbers = build_pagination_window(page, total_pages) if total_pages > 0 else []

    return render_template(
        "index.html",
        papers=papers,
        periods=PERIODS,
        period=period,
        sort=sort,
        field_groups=FIELD_GROUP_LABELS,
        field_group=field_group,
        cached=cached,
        query=query,
        page=page,
        has_next=has_next,
        has_prev=has_prev,
        total_pages=total_pages,
        total_count=total_count,
        page_numbers=page_numbers,
        page_start=start + 1 if papers else 0,
        page_end=start + len(papers),
    )


@app.route("/translate_titles", methods=["POST"])
def translate_titles_route():
    from llm import translate_title_strings
    data = request.json
    if not data or "titles" not in data or not isinstance(data["titles"], list):
        return jsonify({"error": "titles (list) is required"}), 400
    result = translate_title_strings(data["titles"])
    return jsonify({"translations": result})


@app.route("/translate_abstract", methods=["POST"])
def translate_abstract():
    from llm import translate_abstract
    data = request.json
    if not data or "abstract" not in data:
        return jsonify({"error": "abstract is required"}), 400
    result = translate_abstract(data["abstract"])
    return jsonify({"abstract_ja": result})


@app.route("/summarize", methods=["POST"])
def summarize():
    from llm import summarize
    data = request.json
    if not data or "title" not in data or "abstract" not in data:
        return jsonify({"error": "title and abstract are required"}), 400
    result = summarize(data["title"], data["abstract"])
    return jsonify({"summary": result})


@app.route("/importance", methods=["POST"])
def importance():
    from llm import explain_importance
    data = request.json
    if not data or "title" not in data or "abstract" not in data:
        return jsonify({"error": "title and abstract are required"}), 400
    result = explain_importance(data["title"], data["abstract"])
    return jsonify({"importance": result})


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
