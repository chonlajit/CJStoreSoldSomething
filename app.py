"""MilkLab RAG Chatbot (S3).

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


@st.cache_resource
def load_index():
    """TODO 1+2+3: โหลด menu_kb.md, split เป็น chunk, encode ด้วย sentence-transformers,
    สร้าง faiss index. Cache เพราะโหลด model ครั้งแรกใช้เวลา 30 วินาที

    Returns: (model, index, chunks_list)
    """
    with open("menu_kb.md", "r", encoding="utf-8") as f:
        text = f.read()
        
    chunks_list = [c.strip() for c in text.split("\n\n") if c.strip()]
    
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    embeddings = model.encode(chunks_list, convert_to_numpy=True)
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    return model, index, chunks_list


def retrieve_top_k(query: str, model, index, chunks: list[str], k: int = 3) -> list[str]:
    """TODO 4: encode query, search index, return top-k chunks"""
    query_embedding = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, k)
    
    top_chunks = []
    for idx in indices[0]:
        if idx < len(chunks):
            top_chunks.append(chunks[idx])
    return top_chunks


def generate_answer(query: str, context_chunks: list[str]) -> str:
    """TODO 5: ส่ง query + context ไป Gemini, return answer

    Hint: build prompt that says "ตอบจากข้อมูลต่อไปนี้เท่านั้น ถ้าไม่มีใน context ให้บอกว่าไม่รู้"
    """
    client = genai.Client()
    context = "\n\n".join(context_chunks)
    prompt = f"""ตอบคำถามจากข้อมูลต่อไปนี้เท่านั้น โดยใช้ภาษาที่สุภาพ เป็นกันเอง ลงท้ายประโยคด้วยครับพี่ และให้ความช่วยเหลือ หากไม่มีข้อมูลใน context ให้ตอบกลับอย่างสุภาพว่า 'ขออภัยด้วยนะคะ ทางร้านยังไม่มีข้อมูลในส่วนนี้ครับผม' หรือใกล้เคียง

ข้อมูล:
{context}

คำถาม: {query}"""
    
    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents=prompt,
    )
    return response.text


def main():
    st.set_page_config(page_title="MilkLab° RAG", page_icon="🥛")
    st.title("MilkLab° RAG Chatbot")
    st.caption("ถามอะไรเกี่ยวกับ MilkLab ได้ ตอบจาก menu_kb.md")

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

    if prompt := st.chat_input("ถามอะไรเกี่ยวกับ MilkLab"):
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
                    else:
                        answer = f"🚨 **Error ระบบขัดข้อง:** {str(e)}"
            st.write(answer)
            with st.expander("Source chunks"):
                for i, c in enumerate(context, 1):
                    st.markdown(f"**[{i}]** {c}")
        st.session_state.messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
