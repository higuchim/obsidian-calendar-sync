import datetime
import json
import os.path
import sys
import argparse
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 設定ファイルのファイル名
CONFIG_FILENAME = 'config.json'

# Google Calendar APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
SYNC_BLOCK_START = '<!-- calendar-sync:start -->'
SYNC_BLOCK_END = '<!-- calendar-sync:end -->'

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

def parse_iso_datetime(value):
    """ISO日時文字列をdatetimeに変換"""
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    return datetime.datetime.fromisoformat(value)

def format_event(event, calendar_id, weather_calendar_ids):
    """イベント情報を整形して返す"""
    start = event['start']
    summary = event.get('summary', '(No Title)')
    is_weather = calendar_id in weather_calendar_ids
    
    # 時刻情報の取得
    if 'dateTime' in start:
        # 時間指定イベント
        dt_obj = parse_iso_datetime(start['dateTime'])
        time_str = dt_obj.strftime('%H:%M')
        
        end = event['end']
        if 'dateTime' in end:
            end_obj = parse_iso_datetime(end['dateTime'])
            time_str += f"-{end_obj.strftime('%H:%M')}"

        return {
            'text': f"- {time_str} {summary}",
            'start_ts': dt_obj.timestamp(),
            'is_all_day': False,
            'is_weather': is_weather,
        }
    
    elif 'date' in start:
        # 終日イベント
        date_obj = datetime.datetime.strptime(start['date'], '%Y-%m-%d')
        return {
            'text': f"- [終日] {summary}",
            'start_ts': date_obj.timestamp(),
            'is_all_day': True,
            'is_weather': is_weather,
        }
    
    return {
        'text': f"- {summary}",
        'start_ts': 0,
        'is_all_day': False,
        'is_weather': is_weather,
    }

def sort_events(events):
    """終日イベント、天気予報、時刻指定イベントの順でソート"""
    def sort_key(event):
        if event['is_all_day'] and not event['is_weather']:
            rank = 0
        elif event['is_weather']:
            rank = 1
        else:
            rank = 2
        return (rank, event['start_ts'], event['text'])

    return sorted(events, key=sort_key)

def get_events_for_date(service, config, target_date):
    """指定された日付の予定を取得・マージ・ソート"""
    start_dt = target_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone()
    end_dt = target_date.replace(hour=23, minute=59, second=59, microsecond=0).astimezone()

    time_min = start_dt.isoformat()
    time_max = end_dt.isoformat()
    
    calendar_ids = config.get('calendar_ids', ['primary'])
    weather_calendar_ids = set(config.get('weather_calendar_ids', []))
    
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
            
            items = events_result.get('items', [])
            
            for item in items:
                all_events.append(format_event(item, cal_id, weather_calendar_ids))
                
        except HttpError as error:
            print(f"Calendar ID '{cal_id}' error: {error}")

    sorted_events = sort_events(all_events)
    return [e['text'] for e in sorted_events]

def update_obsidian_note(event_lines, config, target_date):
    """Obsidianノートへの書き込み（管理ブロックを全置換）"""
    obsidian_path = config.get('obsidian_daily_path')
    target_header = config.get('target_header', '## 今日の予定').strip()
    if not target_header:
        target_header = '## 今日の予定'

    if not obsidian_path:
        print("Error: config.json に 'obsidian_daily_path' が設定されていません。")
        return

    today_str = target_date.strftime("%Y-%m-%d")
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

    def header_level(header_text):
        match = re.match(r'^#{1,6}(?=\s)', header_text)
        if match:
            return len(match.group(0))
        return None

    # ターゲットヘッダーの位置を探す（前後空白は無視）
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip() == target_header:
            header_idx = i
            break

    if header_idx is None:
        if lines and not lines[-1].endswith('\n'):
            lines[-1] = lines[-1] + '\n'
        if lines and lines[-1].strip():
            lines.append('\n')
        lines.append(f"{target_header}\n")
        header_idx = len(lines) - 1

    section_start = header_idx + 1
    section_end = len(lines)
    target_level = header_level(target_header)

    # 次の同レベル以上のヘッダーまでを対象セクションとする
    if target_level is not None:
        for i in range(section_start, len(lines)):
            match = re.match(r'^\s{0,3}(#{1,6})\s+', lines[i])
            if match and len(match.group(1)) <= target_level:
                section_end = i
                break

    # セクション内の管理ブロック範囲を探す
    block_start_idx = None
    block_end_idx = None
    for i in range(section_start, section_end):
        if lines[i].strip() == SYNC_BLOCK_START:
            block_start_idx = i
            break
    if block_start_idx is not None:
        for i in range(block_start_idx + 1, section_end):
            if lines[i].strip() == SYNC_BLOCK_END:
                block_end_idx = i
                break
        if block_end_idx is None:
            # 壊れたブロックはセクション末尾までを管理対象として復旧
            block_end_idx = section_end - 1

    managed_block_lines = [f"{SYNC_BLOCK_START}\n"]
    managed_block_lines.extend(f"{line}\n" for line in event_lines)
    managed_block_lines.append(f"{SYNC_BLOCK_END}\n")

    if block_start_idx is None:
        insert_at = section_start
        while insert_at < section_end and lines[insert_at].strip() == '':
            insert_at += 1
        new_file_lines = lines[:insert_at] + managed_block_lines + lines[insert_at:]
    else:
        new_file_lines = lines[:block_start_idx] + managed_block_lines + lines[block_end_idx + 1:]

    if new_file_lines == lines:
        print("No changes to sync block.")
        return

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_file_lines)
    print(f"Synced {len(event_lines)} events to {today_str}.md")

def main():
    # 引数解析
    parser = argparse.ArgumentParser(description='Google Calendarの予定をObsidianに同期します。')
    parser.add_argument('date', nargs='?', help='対象日付 (YYYY-MM-DD)。指定がない場合は今日。')
    args = parser.parse_args()

    target_date = datetime.datetime.now()
    if args.date:
        try:
            target_date = datetime.datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print("Error: 日付は YYYY-MM-DD の形式で指定してください。")
            sys.exit(1)

    # 1. 設定読み込み
    config = load_config()
    
    # 2. 認証
    service = authenticate_google_calendar(config)
    
    # 3. イベント取得
    events = get_events_for_date(service, config, target_date)
    
    # 4. Obsidian更新
    update_obsidian_note(events, config, target_date)

if __name__ == '__main__':
    main()
