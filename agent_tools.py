# agent_tools.py
from datetime import datetime
import sales_logger

def _validate_sale(menu, qty, price):
    if qty <= 0:         return 'qty > 0'
    if price < 0:        return 'price >= 0'
    if qty > 500:        return 'qty too large'
    return None

def log_sale(menu, quantity, price):
    err = _validate_sale(menu, quantity, price)
    if err: return {'ok': False, 'tool':'log_sale', 'error': err}
    
    # ในสไลด์เขียนว่า append_sale แต่โค้ดใน sales_logger.py ใช้ชื่อ append_to_sheet ครับ
    # Mocking for fast test execution
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "menu": menu,
        "qty": quantity,
        "price": price,
        "total": quantity * price
    }

def get_yesterday_summary():
    # เรียกใช้ morning_report 
    # (ในแล็บนี้อาจจะเป็นแค่ mock ไปก่อนหรือเรียกโค้ดจริงก็ได้)
    return {'ok': True, 'tool': 'get_yesterday_summary', 'result': 'Mock: สรุปยอดขายเมื่อวาน...'}

def send_telegram_report(message, confirm):
    # แก้บั๊ก: Telegram ส่งเอง (เช็ค confirm flag)
    if not confirm:
        return {'ok': False, 'tool': 'send_telegram_report', 'error': 'ยกเลิกการส่ง เพราะไม่ได้ยืนยัน (confirm=False)'}
    return {'ok': True, 'tool': 'send_telegram_report', 'result': f'Mock: ส่งข้อความ "{message}" เรียบร้อย'}

TOOL_REGISTRY = {
    'log_sale': {'fn': log_sale,
                 'args': ('menu','quantity','price'),
                 'coerce': {'menu':str,'quantity':int,'price':float}},
    'get_yesterday_summary': {'fn': get_yesterday_summary,
                              'args': (),
                              'coerce': {}},
    'send_telegram_report': {'fn': send_telegram_report,
                             'args': ('message', 'confirm'),
                             'coerce': {'message':str, 'confirm':bool}},
}
