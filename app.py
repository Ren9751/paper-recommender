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
# arXiv API は start < 10000 までしか結果を返さない仕様（2024年8月以降）
# つまり最初の 10,000 件 = 250 ページが物理的な閲覧上限
ARXIV_API_RESULT_LIMIT = 10000
MAX_PAGE = ARXIV_API_RESULT_LIMIT // PAGE_SIZE


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
    total_pages_real = math.ceil(total_count / PAGE_SIZE) if total_count > 0 else 0
    # arXiv API は最初の 10,000 件しか返さないので、ページ番号も 250 でキャップ
    total_pages = min(total_pages_real, MAX_PAGE)
    is_capped = total_pages_real > MAX_PAGE

    # キャップを超えるページ番号は最終ページに引き戻す
    if total_pages > 0 and page > total_pages:
        page = total_pages

    # offset を使って 1 ページ分だけ取得する（深いページでも 1 回の HTTP で済む）
    offset = (page - 1) * PAGE_SIZE
    # 総件数が取れていないときは「次ページがあるか」判定用に 1 件多く取る
    fetch_count = PAGE_SIZE if total_pages > 0 else PAGE_SIZE + 1
    fetched = fetch_papers(
        period=period,
        max_results=fetch_count,
        field_group=field_group,
        query=query,
        offset=offset,
    )
    papers = fetched[:PAGE_SIZE]

    has_prev = page > 1
    if total_pages > 0:
        has_next = page < total_pages
    else:
        has_next = len(fetched) > PAGE_SIZE

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
        is_capped=is_capped,
        accessible_count=min(total_count, ARXIV_API_RESULT_LIMIT),
        page_numbers=page_numbers,
        page_start=offset + 1 if papers else 0,
        page_end=offset + len(papers),
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
