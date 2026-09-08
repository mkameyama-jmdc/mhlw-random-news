# mhlw-random-news

官公庁サイトや競合サービス・業界団体サイトを定期巡回し、PHR（Personal Health Record）関連の
新着記事を検知してSlackに自動投稿するBotです。GitHub Actions上で動作します。

## 何をしているか

`main.py` が `TARGET_SITES` に登録された各サイトへアクセスし、記事一覧のリンクを取得します。
サイトごとに設定された条件でタイトルを判定し、条件に合致した記事だけをSlackへ通知します。
一度通知した記事のURLは `post_history.txt` に記録され、次回以降は重複投稿しません。

## 監視対象サイト

| サイト | 判定方法 |
| --- | --- |
| 厚労省 | 全体`KEYWORDS`に一致した記事のみ通知 |
| デジタル庁ニュース | 同上 |
| 総務省 | 同上 |
| 経産省 | 同上 |
| 日本人間ドック・予防医療学会 | キーワード判定なし。新着記事を無条件で全件通知 |
| DeSCヘルスケア(Kencom) | サイト専用の`keywords`（`kencom`関連語）のみで判定。会社名で判定すると学会ブース出展や研究受賞など無関係な記事まで拾ってしまうため、専用キーワードに絞っている |
| 全国健康保険協会(協会けんぽ) | 全体`KEYWORDS`に一致した記事のみ通知 |

## キーワード判定の仕組み

- `KEYWORDS`：全サイト共通のデフォルトキーワード（PHR、マイナ保険証、マイナポータル、医療DX、健保連、Kencom関連語など）
- サイトごとの設定（`TARGET_SITES`の各要素）に`"keywords"`を指定すると、そのサイトだけは全体`KEYWORDS`の代わりにそのリストで判定される（例：DeSCヘルスケア）
- `"filter_required": False`を指定すると、キーワード判定自体を行わず新着記事を無条件で通知する（例：日本人間ドック・予防医療学会）
- 判定は大文字・小文字を区別しない（例：`Kencom`表記でも`kencom`表記でもマッチする）

## ファイル構成

- `main.py`：本体のスクリプト
- `requirements.txt`：依存ライブラリ（`requests`、`beautifulsoup4`）
- `post_history.txt`：通知済み記事URLの履歴（重複投稿防止用）
- `.github/workflows/daily_check.yml`：GitHub Actionsの設定（毎日1回の自動実行＋手動実行に対応）

## 実行タイミング

- 毎日1回、日本時間9時ごろに自動実行（cronスケジュール）
- GitHubの「Actions」タブから`Run workflow`で手動実行も可能

## セットアップに必要な設定

- リポジトリの `Settings > Secrets and variables > Actions` に `SLACK_WEBHOOK_URL` を登録する
- `Settings > Actions > General` の `Workflow permissions` を `Read and write permissions` にしておく
  （`post_history.txt` の更新をコミット・pushするために必要）

## 監視サイトを追加する場合

`TARGET_SITES` に以下の形式で辞書を追加する。

```python
{
    "name": "表示名（Slack通知時の見出しに使われる）",
    "url": "巡回対象のURL",
    "filter_required": True,   # Falseにすると無条件で全件通知
    "selector": "a",           # 記事リンクを取得するCSSセレクタ
    "keywords": ["専用キーワード1", "専用キーワード2"]  # 省略時は全体のKEYWORDSを使用
}
```

追加する際は、対象ページのHTML構造（記事一覧がどのセレクタで取れるか）を事前に確認すること。
会社名など広すぎる語をキーワードにすると、無関係な記事まで拾ってノイズになりやすいので注意。
