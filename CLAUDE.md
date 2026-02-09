# obsidian-calendar-sync

Google Calendar の予定を Obsidian のデイリーノートに同期する Python スクリプト。

## 構成

- `sync_calendar.py` — メインスクリプト（唯一のソースファイル）
- `config.json` — 設定ファイル（カレンダーID、Obsidianパス、認証ファイル名等）
- `credentials.json` — Google OAuth クライアント認証情報（git管理外）
- `token.json` — 認証済みトークン、自動生成・更新（git管理外）
- `venv/` — Python仮想環境

## 処理フロー

1. 引数解析（`YYYY-MM-DD` で日付指定可、未指定なら今日）
2. `config.json` から設定読み込み
3. Google Calendar API に OAuth2 認証（トークン自動リフレッシュあり）
4. 複数カレンダーから指定日のイベントを取得し、開始時刻でソート
5. Obsidian デイリーノート（`YYYY-MM-DD.md`）に `## 今日の予定` ヘッダー下へ追記

## 設計ポイント

- **冪等性**: 既にノートに存在するイベント行は重複追加しない
- **複数カレンダー対応**: `calendar_ids` 配列でマージ（現在4つ: primary、グループ、インポート、日本の祝日）
- **イベント形式**: 時間指定 → `- HH:MM-HH:MM イベント名` / 終日 → `- [終日] イベント名`
- **ファイル自動作成**: デイリーノートが無い場合は `# YYYY-MM-DD` ヘッダー付きで新規作成
- **パス解決**: スクリプト配置ディレクトリ基準で設定ファイルを参照（`get_base_path()`）

## 既知の注意点

- **タイムゾーン**: Google Calendar API への時刻送信時、ローカルタイムゾーン（JST）を正しく付与する必要がある。`isoformat() + 'Z'` でUTC扱いにするとクエリ範囲がずれ、翌日の終日イベント（祝日等）が混入するバグが発生した（修正済み: `.astimezone()` を使用）
- **git管理外ファイル**: `credentials.json`、`token.json`、`venv/`、`.claude/` は `.gitignore` で除外。`config.json` はgit管理対象だが、カレンダーIDなど個人情報を含む点に注意

## 実行方法

```bash
# 仮想環境を使用
source venv/bin/activate
python sync_calendar.py            # 今日の予定を同期
python sync_calendar.py 2026-02-10 # 指定日の予定を同期
```
