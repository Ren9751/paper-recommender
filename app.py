import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify
from semantic_scholar import fetch_papers, is_cached

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
    "humanities": "哲学・法・社会",
    "all":        "全分野",
}


@app.route("/")
def index():
    period = request.args.get("period", "week")
    sort = request.args.get("sort", "new")
    field_group = request.args.get("field_group", "cs")
    query = request.args.get("query", "")

    if period not in PERIODS:
        period = "week"
    if field_group not in FIELD_GROUP_LABELS:
        field_group = "cs"

    cached = is_cached(period, field_group, query)
    papers = fetch_papers(period=period, max_results=40, field_group=field_group, query=query)

    if sort == "popularity":
        papers.sort(key=lambda p: p["citation_count"], reverse=True)

    from llm import translate_titles
    papers = translate_titles(papers)

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
    )


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
