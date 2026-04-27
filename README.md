# AI論文まとめ

社会・倫理系の学術論文を、文系向けにやさしく届ける Web アプリ。

Semantic Scholar API で論文を検索し、Claude Haiku でタイトル翻訳・要約・重要性の説明を生成する。

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env` ファイルを作成：

```
ANTHROPIC_API_KEY=your_key_here
SEMANTIC_SCHOLAR_API_KEY=your_key_here  # 任意。なくても動くがレート制限あり
```

### 3. 起動

```bash
python app.py
```

ブラウザで `http://127.0.0.1:5000` にアクセス。

## 機能

- **論文検索** — キーワード・分野・期間でフィルタリング
- **タイトル日本語翻訳** — 一覧表示時に自動翻訳
- **アブストラクト翻訳** — ボタン押下で個別に翻訳
- **AI要約** — 論文の内容を1〜2文で要約
- **なぜ重要？** — AI・研究に詳しくない人にもわかる重要性の説明
- **ソート** — 新着順 / 引用数順
- **プリセット検索** — AI safety、フェイクニュース、プライバシーなどワンクリック検索

## 技術スタック

- **バックエンド**: Flask + Jinja2
- **論文データ**: Semantic Scholar API
- **AI機能**: Anthropic Claude Haiku（claude-haiku-4-5-20251001）
- **フロントエンド**: バニラ HTML/CSS/JS（単一テンプレート）
