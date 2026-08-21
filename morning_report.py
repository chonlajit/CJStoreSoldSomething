import os
import sys
import json
import base64
import argparse
import requests
import gspread
from datetime import datetime, timedelta
from dotenv import load_dotenv

def get_credentials():
    creds_str = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_str:
        raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS not found in environment.")
    
    # รองรับทั้งแบบ JSON ธรรมดา (รันในเครื่อง) และ Base64 (รันบน GitHub Actions)
    if not creds_str.strip().startswith("{"):
        try:
            creds_str = base64.b64decode(creds_str).decode('utf-8')
        except Exception:
            pass
            
    return json.loads(creds_str)

def fetch_data():
    creds_dict = get_credentials()
    gc = gspread.service_account_from_dict(creds_dict)
    
    sheet_id = os.getenv("GOOGLESHEET_ID") or os.getenv("GOOGLE_SHEETS_ID")
    if sheet_id:
        sheet = gc.open_by_key(sheet_id).sheet1
    else:
        sheet = gc.open("CJSSSlogs_orders").sheet1
        
    return sheet.get_all_records()

def summarize_for_date(rows: list[dict], target_date: str) -> str:
    """
    Pure Function: รับข้อมูล rows และวันที่ที่ต้องการสรุป (YYYY-MM-DD)
    คืนค่าเป็นข้อความสรุปยอดขาย สามารถทำ Unit Test ได้ง่ายเพราะไม่ยุ่งกับ I/O
    """
    daily_total = 0
    menu_summary = {}
    
    for row in rows:
        timestamp_str = str(row.get('timestamp', ''))
        # เช็คว่า timestamp ขึ้นต้นด้วยวันที่ที่ต้องการหรือไม่
        if timestamp_str.startswith(target_date):
            menu = row.get('menu', 'Unknown')
            # ดึงค่าแบบเผื่อกรณีเป็น string ว่าง
            try:
                qty = int(row.get('qty', 0))
                total = float(row.get('total', 0.0))
            except ValueError:
                qty = 0
                total = 0.0
            
            daily_total += total
            if menu in menu_summary:
                menu_summary[menu]['qty'] += qty
                menu_summary[menu]['total'] += total
            else:
                menu_summary[menu] = {'qty': qty, 'total': total}
                
    if daily_total == 0:
        return f"📊 สรุปยอดขายวันที่ {target_date}\nไม่มีรายการขายครับ"
        
    lines = [f"📊 สรุปยอดขายวันที่ {target_date}"]
    for menu, data in menu_summary.items():
        lines.append(f"- {menu}: {data['qty']} รายการ ({data['total']:g} บาท)")
    lines.append(f"💰 ยอดรวมทั้งสิ้น: {daily_total:g} บาท")
    
    return "\n".join(lines)

def send_telegram(message: str):
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not telegram_token or not telegram_chat_id:
        print("[WARN] ไม่พบ TELEGRAM_BOT_TOKEN หรือ TELEGRAM_CHAT_ID ข้ามการส่งข้อความ")
        return
        
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {"chat_id": telegram_chat_id, "text": message}
    response = requests.post(url, json=payload)
    response.raise_for_status()

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Morning Report Generator")
    parser.add_argument("--date", help="วันที่ต้องการสรุป (YYYY-MM-DD) ค่าเริ่มต้นคือเมื่อวาน")
    parser.add_argument("--dry-run", action="store_true", help="แสดงผลสรุปโดยไม่ส่งข้อความจริง (Idempotency)")
    args = parser.parse_args()
    
    # ถ้าไม่ระบุวันที่ ให้สรุปยอดของ "เมื่อวาน"
    if args.date:
        target_date = args.date
    else:
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
        
    try:
        rows = fetch_data()
    except Exception as e:
        print(f"[ERROR] ไม่สามารถดึงข้อมูลจาก Google Sheets ได้: {e}")
        sys.exit(1)
        
    summary_text = summarize_for_date(rows, target_date)
    print(summary_text)
    print("-" * 30)
    
    if args.dry_run:
        print("[INFO] โหมด --dry-run: ข้ามการส่งข้อความไปยัง Telegram")
    else:
        try:
            send_telegram(summary_text)
            print("[OK] ส่งข้อความสรุปยอดขายเรียบร้อยแล้ว")
        except Exception as e:
            print(f"[ERROR] ส่งข้อความล้มเหลว: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
