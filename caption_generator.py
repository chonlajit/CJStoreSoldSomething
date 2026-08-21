"""CJStoreSoldSomething Caption Generator (S1).

Usage:
    python caption_generator.py

Reads GOOGLE_API_KEY from env. Generates a Thai caption for clothing products or custom order services.
"""

import os
import sys
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()


PROMPT_TEMPLATE = """
คุณคือ social media manager ของร้าน CJStoreSoldSomething แบรนด์เสื้อผ้า Handmade และงาน Custom by orders ของ CJ

จงเขียนแคปชั่นภาษาไทย 2 ถึง 3 ประโยคโปรโมตสินค้าหรือบริการ: {item}

เงื่อนไข:
- ชูจุดเด่นเรื่องงาน Handmade มีเอกลักษณ์ไม่ซ้ำใคร ดีไซน์เฉพาะตัว สำหรับคนที่ชอบสไตล์ที่ไม่เหมือนใคร
- โทนเสียงสร้างสรรค์ เท่ เป็นกันเอง ลงท้ายคำด้วย ครับพี่หรือครับผม
- ต้องมี call-to-action ปิดท้าย เช่น ทักแชทสั่งซื้อ หรือส่งดีไซน์/ไซส์ที่ต้องการได้ทันที
- ห้ามใช้ em dash
"""


def generate_caption(item: str, api_key: str | None = None) -> str:
    """Generate a Thai caption for the given product or custom service."""
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not set in env or argument")
    client = genai.Client(api_key=key)

    models = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]
    last_exc = None
    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=PROMPT_TEMPLATE.format(item=item),
            )
            if response and response.text:
                return response.text
        except Exception as exc:
            last_exc = exc
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                time.sleep(2)
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=PROMPT_TEMPLATE.format(item=item),
                    )
                    if response and response.text:
                        return response.text
                except Exception as exc2:
                    last_exc = exc2
                continue
            raise exc

    if last_exc:
        if "429" in str(last_exc) or "RESOURCE_EXHAUSTED" in str(last_exc):
            return "⚠️ [คำเตือน] ขณะนี้โควต้าฟรีของ Gemini API ติด Rate Limit (429) กรุณารอสักครู่ (ประมาณ 30 วินาที) แล้วรันใหม่อีกครั้งครับผม"
        raise last_exc
    return ""


def main() -> int:
    item = input("สินค้าหรือบริการที่จะโปรโมต: ").strip()
    if not item:
        print("กรุณาใส่ชื่อสินค้าหรือบริการ")
        return 1
    caption = generate_caption(item)
    print()
    print(caption)
    return 0


if __name__ == "__main__":
    sys.exit(main())
