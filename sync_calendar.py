import datetime
import json
import os.path
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 設定ファイルのファイル名
CONFIG_FILENAME = 'config.json'

# Google Calendar APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_base_path():
    """スクリプトのあるディレクトリの絶対パスを取得"""
    return os.path.dirname(os.path.abspath(__file__))

def load_config():
    """config.jsonから設定を読み込む"""
    base_dir = get_base_path()
    config_path = os.path.join(base_dir, CONFIG_FILENAME)
    
    if not os.path.exists(config_path):
        print(f"Error: 設定ファイルが見つかりません: {config_path}")
        print(f"同ディレクトリに {CONFIG_FILENAME} を作成してください。")
        sys.exit(1)
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: {CONFIG_FILENAME} の形式が正しくありません。\n{e}")
        sys.exit(1)

def authenticate_google_calendar(config):
    """Google Calendar API認証"""
    creds = None
    base_dir = get_base_path()
    
    # configからファイル名を取得
    token_file = config.get('token_file', 'token.json')
    creds_file = config.get('credentials_file', 'credentials.json')
    
    token_path = os.path.join(base_dir, token_file)
    creds_path = os.path.join(base_dir, creds_file)

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                print(f"Error: 認証情報ファイルが見つかりません: {creds_path}")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def format_event(event):
    """イベント情報を整形して返す"""
    start = event['start']
    summary = event.get('summary', '(No Title)')
    
    # 時刻情報の取得
    if 'dateTime' in start:
        # 時間指定イベント
        # 【修正】辞書からキーを指定して文字列を取り出す
        dt_obj = datetime.datetime.fromisoformat(start['dateTime'])
        time_str = dt_obj.strftime('%H:%M')
        
        end = event['end']
        if 'dateTime' in end:
            # 【修正】辞書からキーを指定して文字列を取り出す
            end_obj = datetime.datetime.fromisoformat(end['dateTime'])
            time_str += f"-{end_obj.strftime('%H:%M')}"
            
        return f"- {time_str} {summary}", dt_obj.timestamp()
    
    elif 'date' in start:
        # 終日イベント
        date_obj = datetime.datetime.strptime(start['date'], '%Y-%m-%d')
        return f"- [終日] {summary}", date_obj.timestamp()
    
    return f"- {summary}", 0

def get_todays_events(service, config):
    """全設定カレンダーから今日の予定を取得・マージ・ソート"""
    now = datetime.datetime.now()
    start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = now.replace(hour=23, minute=59, second=59, microsecond=0)
    
    time_min = start_dt.isoformat() + 'Z'
    time_max = end_dt.isoformat() + 'Z'
    
    calendar_ids = config.get('calendar_ids', ['primary'])
    
    # 【修正】空リストで初期化
    all_events = []

    for cal_id in calendar_ids:
        try:
            events_result = service.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            # 【修正】getの第二引数を空リストに
            items = events_result.get('items', [])
            
            for item in items:
                formatted_text, timestamp = format_event(item)
                all_events.append({'text': formatted_text, 'ts': timestamp})
                
        except HttpError as error:
            print(f"Calendar ID '{cal_id}' error: {error}")

    all_events.sort(key=lambda x: x['ts'])
    return [e['text'] for e in all_events]

def update_obsidian_note(event_lines, config):
    """Obsidianノートへの書き込み（冪等性あり）"""
    obsidian_path = config.get('obsidian_daily_path')
    target_header = config.get('target_header', '## 今日の予定')

    if not obsidian_path:
        print("Error: config.json に 'obsidian_daily_path' が設定されていません。")
        return

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    file_path = os.path.join(obsidian_path, f"{today_str}.md")

    if not os.path.exists(obsidian_path):
        print(f"Error: Obsidianのフォルダが見つかりません: {obsidian_path}")
        return

    # ファイルがなければ作成
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# {today_str}\n\n")

    # ファイル読み込み
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        content = "".join(lines)

    # 【修正】空リストで初期化
    new_lines = []
    
    header_exists = target_header in content
    
    for event_line in event_lines:
        if event_line not in content:
            new_lines.append(event_line)

    if new_lines:
        with open(file_path, 'a', encoding='utf-8') as f:
            if content and not content.endswith('\n'):
                f.write('\n')
            
            if not header_exists:
                f.write(f"\n{target_header}\n")
            
            for line in new_lines:
                f.write(f"{line}\n")
        print(f"Added {len(new_lines)} events to {today_str}.md")
    else:
        print("No new events to add.")

def main():
    # 1. 設定読み込み
    config = load_config()
    
    # 2. 認証
    service = authenticate_google_calendar(config)
    
    # 3. イベント取得
    events = get_todays_events(service, config)
    
    # 4. Obsidian更新
    update_obsidian_note(events, config)

if __name__ == '__main__':
    main()