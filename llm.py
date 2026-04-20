import anthropic

_client = anthropic.Anthropic()
_MODEL = "claude-haiku-4-5-20251001"

_title_cache: dict[str, str] = {}


def translate_titles(papers: list[dict]) -> list[dict]:
    uncached = [p for p in papers if p["title"] not in _title_cache]

    if uncached:
        titles = "\n".join(
            f"{i+1}. {p['title']}" for i, p in enumerate(uncached)
        )
        message = _client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    "以下の論文タイトルを日本語に翻訳してください。\n"
                    "番号付きリストの形式のまま、翻訳結果だけを出力してください。\n\n"
                    + titles
                )
            }]
        )
        lines = message.content[0].text.strip().split("\n")
        for i, p in enumerate(uncached):
            if i < len(lines):
                _title_cache[p["title"]] = lines[i].split(". ", 1)[-1].strip()
            else:
                _title_cache[p["title"]] = p["title"]

    for p in papers:
        p["title_ja"] = _title_cache.get(p["title"], p["title"])
    return papers


def translate_abstract(abstract: str) -> str:
    message = _client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": (
                "以下の論文アブストラクトを日本語に翻訳してください。"
                "翻訳文のみ出力してください。\n\n"
                + abstract
            )
        }]
    )
    return message.content[0].text


def summarize(title: str, abstract: str) -> str:
    message = _client.messages.create(
        model=_MODEL,
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": (
                "以下の論文を1〜2文の日本語で要約してください。"
                "この研究が何をして、何を達成したかを簡潔に伝えてください。"
                "要約文のみ出力してください。\n\n"
                f"タイトル: {title}\n\n"
                f"アブストラクト: {abstract}"
            )
        }]
    )
    return message.content[0].text


def explain_importance(title: str, abstract: str) -> str:
    message = _client.messages.create(
        model=_MODEL,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                "以下の論文が社会やAIの発展にとってなぜ重要なのかを、"
                "AIや研究に詳しくない文系の人にもわかるように1〜2文の日本語で説明してください。"
                "「なぜ重要か」の説明文のみ出力してください。\n\n"
                f"タイトル: {title}\n\n"
                f"アブストラクト: {abstract}"
            )
        }]
    )
    return message.content[0].text
