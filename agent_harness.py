import json
import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv
import agent_tools

# แก้บั๊ก: Sheet ไม่อัปเดต เพราะลืมโหลด .env
load_dotenv()

# ตั้งค่า Logging ให้บันทึก trace log เป็นรูปแบบที่ต้องการ
logging.basicConfig(
    filename='agent_trace.log', 
    level=logging.INFO, 
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M',
    encoding='utf-8'
)

# ตั้งค่า LLM Model
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# แก้บั๊ก: action ผิดทุกครั้ง เพราะขาด Example (เพิ่ม Few-shot)
SYSTEM_INSTRUCTION = '''
You are CJStoreSoldSomething Agent Router.
Convert one Thai user message into ONE JSON action.

Allowed actions:
- log_sale(menu, quantity, price)
- log_order(order_type, quantity, price)
- query_inventory(query)
- get_yesterday_summary()
- send_telegram_report(message, confirm)
- unknown

Return JSON only. No markdown. Numbers numeric.
Schema:
{ "action":..., "arguments":{}, "confidence":0.0,
  "reason":"<short Thai>" }

Examples:
User: บันทึกขายเสื้อแบบที่ 1 จำนวน 1 ตัว ราคา 569
{"action": "log_sale", "arguments": {"menu": "เสื้อแบบที่ 1", "quantity": 1, "price": 569.0}, "confidence": 1.0, "reason": "บันทึกขายสินค้า Handmade ชัดเจน"}

User: บันทึกออร์เดอร์สั่งทำเสื้อ 1 ตัว ราคา 799
{"action": "log_order", "arguments": {"order_type": "เสื้อ", "quantity": 1, "price": 799.0}, "confidence": 1.0, "reason": "บันทึกออร์เดอร์สั่งทำ Custom ชัดเจน"}

User: เช็คสต็อกเสื้อหน่อยว่าเหลือเท่าไหร่
{"action": "query_inventory", "arguments": {"query": "เสื้อ"}, "confidence": 1.0, "reason": "สอบถามสต็อกสินค้า"}

User: ขอสรุปยอดขายเมื่อวานหน่อย
{"action": "get_yesterday_summary", "arguments": {}, "confidence": 1.0, "reason": "ต้องการดูสรุป"}

User: ขายดีไหมวันนี้
{"action": "unknown", "arguments": {}, "confidence": 0.3, "reason": "คำถามไม่ชัดเจนว่าให้ทำอะไร"}
'''

model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=SYSTEM_INSTRUCTION)

def write_trace(data):
    stage = data.get('stage', 'unknown')
    
    if stage == 'user_input':
        content = data.get('input', '')
    elif stage == 'plan':
        stage = 'llm_response'
        content = json.dumps(data.get('plan', {}), ensure_ascii=False)
    elif stage == 'result':
        stage = 'tool_result'
        content = json.dumps(data.get('result', {}), ensure_ascii=False)
    else:
        content = str(data)

    trace_msg = f"| {stage} | {content}"
    logging.info(trace_msg)
    print(f"{logging.Formatter('%(asctime)s').format(logging.LogRecord('', 0, '', 0, '', (), None))} {trace_msg}")

def classify_message(message):
    try:
        response = model.generate_content(message)
        raw_text = response.text.strip()
        
        # แก้บั๊ก: json.loads() fail เพราะมี markdown (Strip markdown)
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        return json.loads(raw_text.strip())
    except Exception as e:
        return {"action": "unknown", "arguments": {}, "confidence": 0.0, "reason": f"Parse Error: {str(e)}"}

def dispatch(plan):
    action = plan.get('action', 'unknown')
    confidence = plan.get('confidence', 1.0)
    
    # แก้บั๊ก: qty หรือ price ผิดพลาด ดึงเลขผิด ขอ confidence + ถามกลับ
    if confidence < 0.7:
        return {'ok': False, 'tool': 'unknown', 'error': 'ฉันไม่แน่ใจว่าคุณต้องการทำอะไร (Confidence < 0.7) โปรดระบุให้ชัดเจนขึ้นครับ'}

    if action == 'unknown':
        return {'ok': False, 'tool': 'unknown', 'error': 'คำสั่งอยู่นอกเหนือความสามารถ หรือไม่ชัดเจน'}

    if action not in agent_tools.TOOL_REGISTRY:
        return {'ok': False, 'tool': action, 'error': 'ไม่พบ Tool นี้ในระบบ'}
        
    tool_info = agent_tools.TOOL_REGISTRY[action]
    fn = tool_info['fn']
    args_keys = tool_info['args']
    coerce_types = tool_info['coerce']
    
    arguments = plan.get('arguments', {})
    
    try:
        prepared_args = []
        for key in args_keys:
            val = arguments.get(key)
            if val is not None and key in coerce_types:
                val = coerce_types[key](val)
            prepared_args.append(val)
            
        # รันฟังก์ชันจริง
        result = fn(*prepared_args)
        return result
    except Exception as e:
        return {'ok': False, 'tool': action, 'error': str(e)}

def run(message):
    write_trace({'stage':'user_input', 'input':message})
    plan = classify_message(message)  
    write_trace({'stage':'plan', 'plan':plan})
    result = dispatch(plan)           
    write_trace({'stage':'result', 'result':result})
    return result

if __name__ == "__main__":
    run("บันทึกขายเสื้อแบบที่ 1 จำนวน 1 ตัว ราคา 569")
