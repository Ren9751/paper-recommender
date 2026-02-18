import re


# 数式記号パターン
_MATH_PATTERN = re.compile(r"[$∑∫∂∇αβγδεζηθλμνπρσωΩ]|\\[a-zA-Z]+")

# prior を上げるキーワード（数学的論文）
_MATH_KEYWORDS = re.compile(
    r"\b(theorem|lemma|proof|corollary|proposition|we prove|we show that|optimal|convergence)\b",
    re.IGNORECASE,
)

# prior を下げるキーワード（サーベイ・入門系）
_SURVEY_KEYWORDS = re.compile(
    r"\b(survey|review|overview|tutorial|introduction to|comprehensive|systematically review)\b",
    re.IGNORECASE,
)


def _prior_score(title: str, abstract: str) -> int:
    """前提知識スコア（1〜5）"""
    text = title + " " + abstract

    math_symbols = len(_MATH_PATTERN.findall(abstract))
    math_keywords = len(_MATH_KEYWORDS.findall(text))
    is_survey = bool(_SURVEY_KEYWORDS.search(text))

    score = 1
    score += min(math_symbols // 3, 2)   # 記号数で最大+2
    score += min(math_keywords, 2)        # 数学キーワードで最大+2

    if is_survey:
        score -= 1

    return max(1, min(5, score))


def _complexity_score(abstract: str) -> int:
    """内容の複雑さスコア（1〜5）"""
    # 文に分割（.!? で区切る）
    sentences = [s.strip() for s in re.split(r"[.!?]", abstract) if s.strip()]
    if not sentences:
        return 3

    words = abstract.split()
    avg_sentence_length = len(words) / len(sentences)

    if avg_sentence_length < 15:
        return 1
    elif avg_sentence_length < 20:
        return 2
    elif avg_sentence_length < 27:
        return 3
    elif avg_sentence_length < 35:
        return 4
    else:
        return 5


def score_paper(paper: dict) -> dict:
    title = paper["title"]
    abstract = paper["abstract"]
    prior = _prior_score(title, abstract)
    complexity = _complexity_score(abstract)
    total = round((prior + complexity) / 2, 1)
    return {**paper, "prior": prior, "complexity": complexity, "total": total}
