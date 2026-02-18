from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify
from fetcher import fetch_papers

app = Flask(__name__)

PERIODS = {
    "day":   "1日",
    "week":  "1週間",
    "month": "1ヶ月",
    "year":  "1年",
}

PERIOD_MAX = {"day": 20, "week": 40, "month": 40, "year": 40}


@app.route("/")
def index():
    period = request.args.get("period", "week")
    sort = request.args.get("sort", "new")

    if period not in PERIODS:
        period = "week"

    max_results = PERIOD_MAX.get(period, 30)
    papers = fetch_papers(category="cs.CY", max_results=max_results, period=period)

    if sort == "popularity":
        from semantic_scholar import fetch_citation_counts
        papers = fetch_citation_counts(papers)
        papers.sort(key=lambda p: p["citation_count"], reverse=True)

    from llm import translate_titles
    papers = translate_titles(papers)

    return render_template(
        "index.html",
        papers=papers,
        periods=PERIODS,
        period=period,
        sort=sort,
    )


@app.route("/translate_abstract", methods=["POST"])
def translate_abstract():
    from llm import translate_abstract
    data = request.json
    result = translate_abstract(data["abstract"])
    return jsonify({"abstract_ja": result})


@app.route("/summarize", methods=["POST"])
def summarize():
    from llm import summarize
    data = request.json
    result = summarize(data["title"], data["abstract"])
    return jsonify({"summary": result})


@app.route("/importance", methods=["POST"])
def importance():
    from llm import explain_importance
    data = request.json
    result = explain_importance(data["title"], data["abstract"])
    return jsonify({"importance": result})


if __name__ == "__main__":
    app.run(debug=True)
