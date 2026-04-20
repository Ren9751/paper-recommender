# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 起動方法

```bash
pip install -r requirements.txt
python app.py
```

ブラウザで `http://127.0.0.1:5000` にアクセス。

## 環境変数

`.env` に以下を設定：

```
ANTHROPIC_API_KEY=your_key_here
```

## アーキテクチャ

```
app.py              # Flaskルーティング。各モジュールを呼び出す
arxiv_source.py     # arXiv APIで論文取得。メモリキャッシュ（1時間TTL）あり
llm.py              # Claude Haiku（claude-haiku-4-5-20251001）でタイトル翻訳・要約・重要性説明。タイトル翻訳は永続メモリキャッシュあり
templates/index.html # Jinja2テンプレート。全UIロジック（CSS・JSインライン）を含む
```

### データフロー

1. `arxiv_source.py` が arXiv API から論文を検索（カテゴリ・期間・キーワードフィルタあり、新着順）
2. `llm.py` でタイトルを一括日本語翻訳してからテンプレートに渡す（未翻訳タイトルのみAPI呼び出し）
3. アブストラクト翻訳・AI要約・重要性説明はボタン押下時にAjaxで個別取得（`/translate_abstract`, `/summarize`, `/importance`）

### 既知の制限

- `max_results=40` 固定のため、長期間の検索でも最新40件しか返らない
- arXiv には人文系カテゴリがほぼ無いため、`field_group=humanities` は `cs.CY`（Computers and Society）+ 経済・金融系で近似
- 被引用数は arXiv API で取得不可のため、ソートは新着順のみ
