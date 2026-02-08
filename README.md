# obsidian-calendar-sync
## Googleカレンダー連携スクリプト 利用マニュアル

このドキュメントは、Googleカレンダーの「今日の予定」を取得し、Obsidianのデイリーノートに自動転記するPythonスクリプト（WSL環境用）のセットアップおよび運用ガイドです。

### 1. 動作環境

本システムは以下の環境で動作することを前提としています。
- OS: Windows 11 上で動作する WSL (Windows Subsystem for Linux)
- 推奨ディストリビューション: Ubuntu 22.04 LTS 以降
- Python: バージョン 3.10 以上
- Obsidian: インストール済みであること
- Google アカウント: カレンダーにアクセスできる権限があること

### 2. 使用方法

WSLのターミナルを開き、プロジェクトフォルダに移動して以下のコマンドを順に実行してください。source に与えるパスは適宜変更してください。
```
source ~/projects/obsidian-calendar-sync/venv/bin/activate && python3 sync_calendar.py
```

特定の日付の予定を取得したい場合は、以下のコマンドを実行してください。source に与えるパスは適宜変更してください。
```
source ~/projects/obsidian-calendar-sync/venv/bin/activate && python3 sync_calendar.py YYYY-MM-DD
```

### 3. セットアップと設定
#### 3.1 フォルダ構成の準備

WSL上の任意の場所にプロジェクトフォルダを作成し、以下のファイルを配置してください。
```
project_folder/
               ├── sync_calendar.py    # (配布されたスクリプト本体)
               ├── config.json         # (設定ファイル)
               ├── credentials.json    # (Google Cloudからダウンロードした認証情報)
               └── venv/               # (Python仮想環境・自動生成されます)
```

#### 3.2 Google認証情報の準備 (credentials.json)
1. Google Cloud Console (https://console.cloud.google.com/) にアクセスし、新規プロジェクトを作成します。
2. **APIとサービス > ライブラリ** から「**Google Calendar API**」を検索し、有効化します。
3. **Google Auth Platform > ブランディング（Branding）** に進み、以下を設定します。
   - **アプリ名**: 任意の文字列
   - **ユーザー サポートメール**: 自分のメールアドレス
   - **アプリのロゴ**: 空欄で可
   - **アプリのドメイン**: 空欄で可
   - **承認済みドメイン**: 空欄で可
   - **デベロッパーの連絡先情報**: 自分のメールアドレス
4. **Google Auth Platform > 対象（Audience）** に進み、以下を設定します。
   - **重要：公開ステータス**: デフォルトではステータスが「**Testing（テスト中）**」になっています。このままだと認証トークンが7日間で失効します。
   - 「**Publish App（アプリを公開）**」ボタンを押し、ステータスを「**In Production（本番環境）**」に変更してください。
   - 注記: 検証（Verification）は不要です。認証時に警告が出ますが、個人利用であれば問題ありません。
5. 認証情報の作成
   - **APIとサービス > 認証情報** から「認証情報を作成」→「OAuthクライアントID」を選択します。
   - **アプリケーションの種類**: **デスクトップアプリ**を選択します。
   - **名前**: 任意のアプリ名を入力します。(デフォルトのままでも問題ありません)
   - **作成**をクリックします。
6. **OAuthクライアントを作成しました**というポップアップが表示されます。
   - ポップアップ最下部の**JSONをダウンロード**をクリックし認証情報をダウンロードします。
   - ダウンロードしたファイルを**credentials.json**にリネームしてプロジェクトフォルダに配置します。

#### 3.3 設定ファイルの編集 (config.json)
config.json をテキストエディタで開き、環境に合わせて修正します。

```
{
  "obsidian_daily_path": "/mnt/c/Users/YOUR_NAME/Documents/Obsidian Vault/Daily",
  "calendar_ids": [
    "primary",
    "xxxxxxxx@group.calendar.google.com"
  ],
  "target_header": "## 今日の予定",
  "credentials_file": "credentials.json",
  "token_file": "token.json"
}
```
- obsidian_daily_path: Obsidianのデイリーノートが保存されているフォルダのパス。
重要: WSLからWindowsのフォルダを指定するため、C:\Users\... ではなく /mnt/c/Users/... の形式で記述してください。
- calendar_ids: 取得したいカレンダーのIDリスト。個人のメインカレンダーは "primary" です。追加カレンダーは、Googleカレンダー設定画面の「カレンダーの統合」項目にあるIDを使用します。
  
#### 3.4 Python環境の構築
WSLのターミナルを開き、プロジェクトフォルダに移動して以下のコマンドを順に実行してください。
``` 
# 1. 仮想環境の作成
python3 -m venv venv

# 2. 仮想環境の有効化
source venv/bin/activate

# 3. 必要なライブラリのインストール
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```
### 4. 動作確認（初回実行）
初回の実行では、Googleアカウントへのアクセス許可（認証）が必要です。WSLターミナルで（仮想環境が有効な状態で）以下を実行します。
```
python3 sync_calendar.py
```

ターミナルに以下のようなメッセージとURLが表示されます。
```
Please visit this URL to authorize this application: https://accounts.google.com/...
```
1. このURLをコピーし、Windowsのブラウザ（Chromeなど）に貼り付けて開きます。
2. Googleアカウントでログインし、アクセスを「許可」します。
3. 「このアプリはGoogleで確認されていません」という警告が出た場合は、「詳細」→「[アプリ名]（安全ではないページ）に移動」をクリックして進めてください。
4. 認証が成功すると、スクリプトが続きを実行し、「Added X events...」と表示されれば成功です。
5. 成功すると プロジェクトフォルダにtoken.json が生成されます。
6. Obsidianの「今日のデイリーノート」を確認し、予定が追記されているか確認してください。

### 5. 自動化の指定方法（Windowsタスクスケジューラ）
毎日決まった時刻に自動実行させるには、Windowsの「タスクスケジューラ」を使用します。このスクリプトは実行時点で当日のデイリーノートが存在することを前提にしているので、実行タイミングの設定はその点を考慮して行ってください。当日のデイリーノートが存在しない場合、スクリプトが新規にファイルを作成しますが、その場合はデイリーノート用に用意したObsidianのテンプレートが適用されない可能性があります。その場合は、手動でデイリーノートを作成し、テンプレートを適用してから、スクリプトを実行してください。

#### タスク登録手順
1. Windowsメニューで「タスクスケジューラ」を検索して起動します。
2. 右側の「基本タスクの作成」をクリックします。
- 名前: ObsidianSync など任意に入力。
- トリガー: 「毎日」を選択し、実行したい時刻（例: 7:00）を設定します。
- 操作: 「プログラムの開始」を選択します。プログラム/スクリプト: wsl.exe と入力します。
- 引数の追加: 以下のコマンドをコピーして入力します（パスは自分の環境に合わせて書き換えてください）。
```
-u <WSLユーザー名> -e bash -c "source /home/<WSLユーザー名>/<プロジェクトパス>/venv/bin/activate && python3 /home/<WSLユーザー名>/<プロジェクトパス>/sync_calendar.py"
```
例: ユーザー名が taro、パスが projects/obsidian-sync の場合:
```
-u taro -e bash -c "source /home/taro/projects/obsidian-sync/venv/bin/activate && python3 /home/taro/projects/obsidian-sync/sync_calendar.py"
```
- [完了] をクリックして作成します。
- 作成したタスクをダブルクリックし、「ユーザーがログオンしているかどうかにかかわらず実行する」にチェックを入れておくと、黒い画面が出ずにバックグラウンドで実行されます。
- 手動実行用ショートカット（オプション）デスクトップに Sync.bat というファイルを作成し、中身に上記「引数の追加」の内容を含むコマンドを書くことで、ダブルクリックで即時実行も可能です。
```
@echo off
wsl.exe -u <WSLユーザー名> -e bash -c "source /home/<パス>/venv/bin/activate && python3 /home/<パス>/sync_calendar.py"
pause
```

### 6. トラブルシューティング
**Q1.** 1週間（7日）ごとに認証エラーが起きて動かなくなる

**原因:** Google CloudのOAuth同意画面のステータスが「Testing（テスト中）」のままになっています。Testingステータスでは、リフレッシュトークンの有効期限が7日間に制限されます。

**対処:**
1. Google Cloud Consoleの「OAuth同意画面」設定へ移動します。
2. 「アプリを公開（Publish App）」ボタンを押し、ステータスを「In Production（本番）」に変更してください。
3. ローカルにある token.json を削除します。
4. 再度スクリプトを手動実行し、再認証を行ってください。これでトークンが無期限（厳密には6ヶ月未使用で失効）になります。

**Q2.** "Invalid Grant" エラーが出る

**原因:** トークンが失効している、パスワードを変更した、またはトークンファイルが破損しています。

**対処:** token.json を削除し、再度スクリプトを実行して再認証してください。

**Q3.** Obsidianに書き込まれない

**原因:** パスの記述ミス、またはWSLからWindows側ファイルシステムへの書き込み権限の問題。

**対処:** config.py の OBSIDIAN_VAULT_PATH が正しいか確認してください。WSLからは /mnt/c/Users/... のようにマウントポイント経由でアクセスする必要があります。

---

### 動作保証無し＆サポート無し（Disclaimer）

本ソフトウェアの使用にあたっては、以下の免責事項およびサポートポリシーに同意したものとみなされます。

#### 免責事項 (No Warranty)
本ソフトウェアは「現状有姿（AS IS）」で提供されます。明示的か黙示的かを問わず、商品性、特定目的への適合性、および権利侵害の不存在を含むいかなる保証も行いません。 作者および著作権者は、契約、不法行為、またはその他の法的根拠に関わらず、本ソフトウェアの使用または使用不能から生じるデータの損失（Googleカレンダーのデータ消失、Obsidianノートの破損など）、Googleアカウントの停止、API利用料金の発生、その他の損害について、一切の責任を負いません。 本ソフトウェアは実験的な実装であり、ユーザー自身の責任において使用してください。

#### サポート無し (No Support)
本プロジェクトは、作者の個人的な用途のために開発されたものであり、一般ユーザーへのサポート義務を負いません。

- 技術サポート: インストール方法、環境構築、エラーの解決に関する個別の問い合わせには対応いたしかねます。
- メンテナンス: Google Calendar APIの仕様変更、Google Cloud PlatformのUI変更、Pythonライブラリの更新、WSLの仕様変更等により、本ソフトウェアが予告なく動作しなくなる可能性がありますが、これらに追従して修正を行う義務を負いません。
- 機能追加: 個別の機能追加要望には応じられません。

ご自身でコードを解析・修正できる方、あるいは動作しなくなった場合に自己解決できる方のみご利用ください。