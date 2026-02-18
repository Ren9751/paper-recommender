import anthropic

_client = anthropic.Anthropic()
_MODEL = "claude-haiku-4-5-20251001"


def translate_titles(papers: list[dict]) -> list[dict]:
    titles = "\n".join(
        f"{i+1}. {p['title']}" for i, p in enumerate(papers)
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
    for i, p in enumerate(papers):
        if i < len(lines):
            p["title_ja"] = lines[i].split(". ", 1)[-1].strip()
        else:
            p["title_ja"] = p["title"]
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
