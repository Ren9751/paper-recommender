import json
import os
from pathlib import Path

import anthropic

_client = anthropic.Anthropic()
_MODEL = "claude-haiku-4-5-20251001"

_TITLE_CACHE_FILE = Path(__file__).parent / "title_cache.json"


def _load_title_cache() -> dict[str, str]:
    try:
        with open(_TITLE_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {}


def _save_title_cache() -> None:
    tmp = _TITLE_CACHE_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_title_cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _TITLE_CACHE_FILE)


_title_cache: dict[str, str] = _load_title_cache()
_abstract_cache: dict[str, str] = {}
_summary_cache: dict[str, str] = {}
_importance_cache: dict[str, str] = {}


def translate_title_strings(titles: list[str]) -> dict[str, str]:
    """英語タイトルのリストを受け取り、{英語: 日本語} の辞書を返す。
    キャッシュ済みのものは API を呼ばずに即返却する。"""
    uncached = [t for t in titles if t not in _title_cache]

    if uncached:
        joined = "\n".join(f"{i+1}. {t}" for i, t in enumerate(uncached))
        message = _client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    "以下の論文タイトルを日本語に翻訳してください。\n"
                    "番号付きリストの形式のまま、翻訳結果だけを出力してください。\n\n"
                    + joined
                )
            }]
        )
        lines = message.content[0].text.strip().split("\n")
        for i, t in enumerate(uncached):
            if i < len(lines):
                _title_cache[t] = lines[i].split(". ", 1)[-1].strip()
            else:
                _title_cache[t] = t
        _save_title_cache()

    return {t: _title_cache.get(t, t) for t in titles}


def translate_abstract(abstract: str) -> str:
    if abstract in _abstract_cache:
        return _abstract_cache[abstract]
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
    result = message.content[0].text
    _abstract_cache[abstract] = result
    return result


def summarize(title: str, abstract: str) -> str:
    if title in _summary_cache:
        return _summary_cache[title]
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
    result = message.content[0].text
    _summary_cache[title] = result
    return result


def explain_importance(title: str, abstract: str) -> str:
    if title in _importance_cache:
        return _importance_cache[title]
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
    result = message.content[0].text
    _importance_cache[title] = result
    return result
