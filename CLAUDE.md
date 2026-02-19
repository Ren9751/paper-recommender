# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 起動方法

```bash
cd paper-recommender
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
fetcher.py          # arXiv APIで論文取得。メモリキャッシュ（1時間TTL）あり
llm.py              # Claude Haiku（claude-haiku-4-5-20251001）でタイトル翻訳・要約・重要性説明
semantic_scholar.py # Semantic Scholar APIで被引用数を取得
templates/index.html # Jinja2テンプレート。全UIロジックを含む
```

### データフロー

1. `fetcher.py` が arXiv から cs.CY カテゴリの論文を取得（期間フィルタあり）
2. `sort=popularity` のとき `semantic_scholar.py` で被引用数を付与してソート
3. `llm.py` でタイトルを一括日本語翻訳してからテンプレートに渡す
4. アブストラクト翻訳・AI要約・重要性説明はボタン押下時にAjaxで個別取得（`/translate_abstract`, `/summarize`, `/importance`）

### 既知の制限

- arXiv の submittedDate フィルタが不安定なため、期間フィルタは Python 側で cutoff 日付と比較する方式
- FETCH_MAX が 40 固定のため、1ヶ月・1年の期間では最新40件しか返らない
- Semantic Scholar API はキーなしで使用中（レート制限あり）。APIキー申請済み・承認待ち
