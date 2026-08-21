"""CJStoreSoldSomething RAG Chatbot (S3).

Run locally: streamlit run app.py
Deploy: push to GitHub then Actions deploys to HuggingFace Space

นักศึกษาต้องเติม TODO 5 จุด ใน Session 3 Lab 2.2
"""

import os
import streamlit as st
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from google import genai


from agent_tools import fetch_inventory_from_sheet


def get_kb_text() -> str:
    """Fetch live KB text from Google Sheet tab 2 if available, fallback to CJStore_kb.md."""
    sheet_items = fetch_inventory_from_sheet()
    if sheet_items:
        lines = [
            "# CJStoreSoldSomething Knowledge Base (จาก Google Sheet หน้า 2)",
            "",
            "## เกี่ยวกับร้าน",
            "CJStoreSoldSomething เป็นแบรนด์เสื้อผ้า Handmade และงาน Custom by orders ของ ชลสิทธิ์ จิตมาตย์ (CJ)",
            "ตอบโจทย์คนที่ชอบเสื้อผ้าสไตล์เฉพาะตัว งานดีไซน์ที่มีเอกลักษณ์ไม่ซ้ำใคร",
            "",
            "## รายการสินค้า Handmade (อัปเดตสดจาก Google Sheet ตารางสินค้าที่มี)",
            "",
            "| สินค้า | ไซส์ | ราคา (บาท) | จำนวนคงเหลือ | ตำหนิ / หมายเหตุ |",
            "|---|---|---|---|---|",
        ]
        for item in sheet_items:
            product = item.get("สินค้า", "-")
            size = item.get("ไซส์", "-")
            price = item.get("ราคา", "-")
            qty = item.get("จำนวน", "-")
            defect = item.get("ตำหนิ", "ไม่มี")
            lines.append(f"| {product} | {size} | {price} | {qty} | {defect} |")

        lines.extend([
            "",
            "## บริการทำเสื้อตาม Order (Custom Made)",
            "| ประเภทสินค้า | ไซส์ที่รองรับ | จำนวนที่มี | ราคาเริ่มต้น (บาท) | หมายเหตุ |",
            "|---|---|---|---|---|",
            "| เสื้อ Custom | S, M, L, XL, Custom | ผลิตตามออร์เดอร์ | 799 | ราคาปรับตามสีหรือวัสดุที่เลือกใช้ |",
            "| กางเกง Custom | S, M, L, XL, Custom | ผลิตตามออร์เดอร์ | 869 | ราคาปรับตามสีหรือวัสดุที่เลือกใช้ |",
            "| งาน Custom อื่นๆ | ตามตกลง | ผลิตตามออร์เดอร์ | 769 | ราคาปรับตามชิ้นงานที่ต้องการ custom |",
            "",
            "## การติดต่อสั่งซื้อ",
            "- ทักแชทสอบถาม หรือส่งรายละเอียดไซส์และดีไซน์ให้ CJ ได้ทันทีผ่าน LINE OA / Telegram / Chat",
        ])
        return "\n".join(lines)

    kb_file = "CJStore_kb.md" if os.path.exists("CJStore_kb.md") else "menu_kb.md"
    with open(kb_file, "r", encoding="utf-8") as f:
        return f.read()


@st.cache_resource
def load_index():
    """Load KB, split into chunks, encode with sentence-transformers, create faiss index."""
    text = get_kb_text()
    chunks_list = [c.strip() for c in text.split("\n\n") if c.strip()]

    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    embeddings = model.encode(chunks_list, convert_to_numpy=True)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    return model, index, chunks_list


def retrieve_top_k(query: str, model, index, chunks: list[str], k: int = 3) -> list[str]:
    """Encode query, search index, return top-k chunks."""
    query_embedding = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, k)
    
    top_chunks = []
    for idx in indices[0]:
        if idx < len(chunks):
            top_chunks.append(chunks[idx])
    return top_chunks


def generate_answer(query: str, context_chunks: list[str]) -> str:
    """Send query + context to Gemini, return answer."""
    client = genai.Client()
    context = "\n\n".join(context_chunks)
    prompt = f"""ตอบคำถามจากข้อมูลต่อไปนี้เท่านั้น โดยใช้ภาษาที่สุภาพ เป็นกันเอง ลงท้ายประโยคด้วยครับพี่ หรือครับผม และให้ความช่วยเหลือ หากไม่มีข้อมูลใน context ให้ตอบกลับอย่างสุภาพว่า 'ขออภัยด้วยนะครับ ทางร้านยังไม่มีข้อมูลในส่วนนี้ครับผม' หรือใกล้เคียง

ข้อมูล:
{context}

คำถาม: {query}"""
    
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt,
    )
    return response.text


def main():
    st.set_page_config(page_title="CJStoreSoldSomething RAG", page_icon="👕")
    st.title("CJStoreSoldSomething RAG Chatbot")
    st.caption("ถามอะไรเกี่ยวกับ CJStoreSoldSomething ได้ ตอบจาก CJStore_kb.md")

    try:
        model, index, chunks = load_index()
    except NotImplementedError as exc:
        st.error(f"TODO not implemented: {exc}")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("ถามอะไรเกี่ยวกับ CJStoreSoldSomething"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("กำลังค้นข้อมูล..."):
                context = retrieve_top_k(prompt, model, index, chunks)
                try:
                    answer = generate_answer(prompt, context)
                except Exception as e:
                    error_str = str(e).lower()
                    if "404" in error_str or "not_found" in error_str or "not found" in error_str:
                        answer = "🚨 **Error: ไม่พบโมเดลที่ระบุ (Model Not Found)**\nโปรดตรวจสอบชื่อโมเดลในไฟล์ `app.py` ว่าถูกต้องหรือไม่"
                    elif "429" in error_str or "quota" in error_str or "exhausted" in error_str:
                        answer = "🚨 **Error: โควต้า API หมด (Quota Exceeded)**\nโปรดตรวจสอบโควต้าการใช้งาน Google API ของคุณ"
                    elif "400" in error_str or "api key" in error_str:
                        answer = "🚨 **Error: API Key ไม่ถูกต้อง (Invalid API Key)**\nโปรดตรวจสอบ API Key อีกครั้ง"
                    elif "503" in error_str or "unavailable" in error_str:
                        answer = "🚨 **Error: เซิร์ฟเวอร์ทำงานหนัก (503 Service Unavailable)**\nขณะนี้มีผู้ใช้งาน AI จำนวนมาก กรุณารอสักครู่แล้วลองถามใหม่อีกครั้งค่ะ"
                    else:
                        answer = f"🚨 **Error ระบบขัดข้อง:** {str(e)}"
            st.write(answer)
            with st.expander("Source chunks"):
                for i, c in enumerate(context, 1):
                    st.markdown(f"**[{i}]** {c}")
        st.session_state.messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
