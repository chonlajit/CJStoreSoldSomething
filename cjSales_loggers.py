"""CJStoreSoldSomething Sales Logger - สินค้า Handmade.

Usage:
    python cjSales_loggers.py --name "เสื้อแบบที่ 1" --size "M" --qty 1 --price 569

Appends row [เวลา, ชื่อ, ไซส์, จำนวน, ราคารวม, รวม] to Columns A:F in Google Sheet "CJSSSlogs_orders",
then sends a notification via Telegram or LINE bot.
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
import gspread
import requests
from dotenv import load_dotenv

load_dotenv()


def get_gspread_client():
    creds_str = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_str:
        raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS is not set in environment.")

    if not creds_str.strip().startswith("{"):
        try:
            creds_str = base64.b64decode(creds_str).decode("utf-8")
        except Exception:
            pass

    creds_dict = json.loads(creds_str)
    return gspread.service_account_from_dict(creds_dict)


def get_worksheet():
    gc = get_gspread_client()
    sheet_id = os.getenv("GOOGLE_SHEETS_ID") or os.getenv("GOOGLESHEET_ID")
    if sheet_id:
        return gc.open_by_key(sheet_id).sheet1
    return gc.open("CJSSSlogs_orders").sheet1


def append_to_sheet(name: str, size: str = "-", qty: int = 1, price: float = 0.0) -> dict:
    """Append a handmade sales row to Columns A:F in Google Sheet."""
    sheet = get_worksheet()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = qty * price

    col_a_values = sheet.col_values(1)
    next_row = len(col_a_values) + 1
    if next_row < 4:
        next_row = 4

    range_name = f"A{next_row}:F{next_row}"
    values = [[timestamp, name, size, qty, price, total]]

    try:
        sheet.update(range_name, values)
    except TypeError:
        try:
            sheet.update(range_name=range_name, values=values)
        except Exception:
            sheet.update(values=values, range_name=range_name)

    return {
        "timestamp": timestamp,
        "name": name,
        "size": size,
        "qty": qty,
        "price": price,
        "total": total,
        "row": next_row,
    }


def send_notification(message: str) -> str:
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    line_token = os.getenv("LINE_CHANNEL_TOKEN")

    if telegram_token and telegram_chat_id:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {"chat_id": telegram_chat_id, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return "telegram"
    elif line_token:
        url = "https://api.line.me/v2/bot/message/broadcast"
        headers = {
            "Authorization": f"Bearer {line_token}",
            "Content-Type": "application/json",
        }
        payload = {"messages": [{"type": "text", "text": message}]}
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return "line"
    else:
        raise RuntimeError("No TELEGRAM_BOT_TOKEN+CHAT_ID or LINE_CHANNEL_TOKEN found in environment.")


def main() -> int:
    parser = argparse.ArgumentParser(description="CJStore Handmade Sales Logger")
    parser.add_argument("--name", required=True, help="ชื่อสินค้า (เช่น เสื้อแบบที่ 1)")
    parser.add_argument("--size", default="-", help="ไซส์สินค้า (เช่น M, L, Free size)")
    parser.add_argument("--qty", type=int, default=1, help="จำนวนชิ้น")
    parser.add_argument("--price", type=float, required=True, help="ราคาต่อชิ้น")
    args = parser.parse_args()

    try:
        row = append_to_sheet(args.name, args.size, args.qty, args.price)
        total = row["total"]
    except Exception as exc:
        print(f"[ERROR] บันทึก Sheet ล้มเหลว: {exc}", file=sys.stderr)
        print("[HINT] ตรวจ GOOGLE_SHEETS_CREDENTIALS และ share Sheet กับ service account email", file=sys.stderr)
        return 1

    msg = (
        f"🛍️ [บันทึกยอดขาย สินค้า Handmade]\n"
        f"สินค้า: {args.name}\n"
        f"ไซส์: {args.size}\n"
        f"จำนวน: {args.qty}\n"
        f"ราคาต่อชิ้น: {args.price:,.2f} บาท\n"
        f"ยอดรวม: {total:,.2f} บาท"
    )

    try:
        provider = send_notification(msg)
    except Exception as exc:
        print(f"[WARN] บันทึก Sheet สำเร็จแต่ส่งแจ้งเตือนล้มเหลว: {exc}", file=sys.stderr)
        return 0

    print(f"[OK] บันทึกสินค้า Handmade ลงแถว {row['row']} และแจ้งเตือนผ่าน {provider} เรียบร้อย ยอด {total:,.2f} บาท")
    return 0


if __name__ == "__main__":
    sys.exit(main())
