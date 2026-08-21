# agent_tools.py
import base64
import json
import os
from datetime import datetime
import gspread

import cjSales_loggers
import cjOrder_loggers

STATIC_INVENTORY = [
    {"สินค้า": "เสื้อแบบที่ 1", "ไซส์": "M", "ราคา": "569", "จำนวน": "1", "ตำหนิ": "ตำหนิหนึ่งจุด"},
    {"สินค้า": "เสื้อแบบที่ 2", "ไซส์": "L", "ราคา": "599", "จำนวน": "2", "ตำหนิ": "ไม่มีตำหนิ"},
    {"สินค้า": "กางเกงแบบที่ 1", "ไซส์": "L", "ราคา": "669", "จำนวน": "1", "ตำหนิ": "ตำหนิหนึ่งจุด"},
    {"สินค้า": "กางเกงแบบที่ 2", "ไซส์": "XL", "ราคา": "699", "จำนวน": "3", "ตำหนิ": "ไม่มีตำหนิ"},
    {"สินค้า": "เสื้อ Custom", "ไซส์": "S, M, L, XL, Custom", "ราคา": "799", "จำนวน": "ผลิตตามออร์เดอร์", "ตำหนิ": "ราคาปรับตามสี/วัสดุ"},
    {"สินค้า": "กางเกง Custom", "ไซส์": "S, M, L, XL, Custom", "ราคา": "869", "จำนวน": "ผลิตตามออร์เดอร์", "ตำหนิ": "ราคาปรับตามสี/วัสดุ"},
    {"สินค้า": "อื่นๆ Custom", "ไซส์": "Custom", "ราคา": "769", "จำนวน": "ผลิตตามออร์เดอร์", "ตำหนิ": "ราคาปรับตามชิ้นงาน"},
]


def fetch_inventory_from_sheet() -> list[dict]:
    """Fetch live product inventory from Sheet tab 2 (ตารางสินค้าที่มี)."""
    try:
        creds_str = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        if not creds_str:
            return []
        if not creds_str.strip().startswith("{"):
            try:
                creds_str = base64.b64decode(creds_str).decode("utf-8")
            except Exception:
                pass
        creds_dict = json.loads(creds_str)
        gc = gspread.service_account_from_dict(creds_dict)

        sheet_id = os.getenv("GOOGLE_SHEETS_ID") or os.getenv("GOOGLESHEET_ID")
        if sheet_id:
            sh = gc.open_by_key(sheet_id)
        else:
            sh = gc.open("CJSSSlogs_orders")

        try:
            ws = sh.worksheet("ตารางสินค้าที่มี")
        except Exception:
            ws = sh.get_worksheet(1)

        all_values = ws.get_all_values()
        if not all_values:
            return []

        header_idx = -1
        for idx, row in enumerate(all_values):
            if any("สินค้า" in str(cell) for cell in row):
                header_idx = idx
                break

        if header_idx == -1:
            return []

        headers = [str(c).strip() for c in all_values[header_idx]]
        items = []
        for row in all_values[header_idx + 1:]:
            if not any(row):
                continue
            item = {}
            for h, val in zip(headers, row):
                if h:
                    item[h] = val.strip()
            if item.get("สินค้า"):
                items.append(item)
        return items
    except Exception as e:
        print(f"Notice: Live sheet inventory fetch skipped ({e})")
        return []


def _validate_sale(name, qty, price):
    if qty <= 0:
        return 'qty > 0'
    if price < 0:
        return 'price >= 0'
    if qty > 500:
        return 'qty too large'
    return None


def log_sale(menu, quantity, price, size="-"):
    err = _validate_sale(menu, quantity, price)
    if err:
        return {'ok': False, 'tool': 'log_sale', 'error': err}

    try:
        res = cjSales_loggers.append_to_sheet(name=menu, size=size, qty=quantity, price=price)
        return {"ok": True, "tool": "log_sale", "result": res}
    except Exception:
        return {
            "ok": True,
            "tool": "log_sale",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": menu,
            "size": size,
            "qty": quantity,
            "price": price,
            "total": quantity * price,
        }


def log_order(order_type, quantity, price, size="-", requirement="-", deadline="-"):
    err = _validate_sale(order_type, quantity, price)
    if err:
        return {'ok': False, 'tool': 'log_order', 'error': err}

    try:
        res = cjOrder_loggers.append_order_to_sheet(
            order_type=order_type, size=size, requirement=requirement, deadline=deadline, qty=quantity, price=price
        )
        return {"ok": True, "tool": "log_order", "result": res}
    except Exception:
        return {
            "ok": True,
            "tool": "log_order",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": order_type,
            "size": size,
            "requirement": requirement,
            "deadline": deadline,
            "qty": quantity,
            "price": price,
            "total": quantity * price,
        }


def query_inventory(query=""):
    inventory = fetch_inventory_from_sheet()
    if not inventory:
        inventory = STATIC_INVENTORY

    if not query:
        return {"ok": True, "tool": "query_inventory", "inventory": inventory}

    matched = [
        item for item in inventory
        if query.lower() in item.get("สินค้า", "").lower() or query.lower() in item.get("ไซส์", "").lower()
    ]
    return {"ok": True, "tool": "query_inventory", "query": query, "results": matched}


def get_yesterday_summary():
    return {'ok': True, 'tool': 'get_yesterday_summary', 'result': 'Mock: สรุปยอดขายเมื่อวาน...'}


def send_telegram_report(message, confirm):
    if not confirm:
        return {'ok': False, 'tool': 'send_telegram_report', 'error': 'ยกเลิกการส่ง เพราะไม่ได้ยืนยัน (confirm=False)'}
    return {'ok': True, 'tool': 'send_telegram_report', 'result': f'Mock: ส่งข้อความ "{message}" เรียบร้อย'}


TOOL_REGISTRY = {
    'log_sale': {
        'fn': log_sale,
        'args': ('menu', 'quantity', 'price'),
        'coerce': {'menu': str, 'quantity': int, 'price': float},
    },
    'log_order': {
        'fn': log_order,
        'args': ('order_type', 'quantity', 'price'),
        'coerce': {'order_type': str, 'quantity': int, 'price': float},
    },
    'query_inventory': {
        'fn': query_inventory,
        'args': ('query',),
        'coerce': {'query': str},
    },
    'get_yesterday_summary': {
        'fn': get_yesterday_summary,
        'args': (),
        'coerce': {},
    },
    'send_telegram_report': {
        'fn': send_telegram_report,
        'args': ('message', 'confirm'),
        'coerce': {'message': str, 'confirm': bool},
    },
}
