import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

nb = new_notebook()

cells = []

# Title
cells.append(new_markdown_cell("# Mini Eval: RAG Retrieval Layer\n\nThis notebook evaluates the RAG retrieval layer by calculating Precision@3 and Recall@3 over a set of 10 ground truth questions."))

# Imports and setup
cells.append(new_code_cell("""import sys
import os
import matplotlib.pyplot as plt
import numpy as np

# Import functions from app.py
from app import load_index, retrieve_top_k

# Load index and model
print("Loading model and index...")
model, index, chunks = load_index()
print(f"Loaded {len(chunks)} chunks from knowledge base.")
"""))

# Ground Truth
cells.append(new_code_cell("""# 10 Ground Truth Questions and their expected exact chunk matches
ground_truths = [
    {
        "question": "ร้านเปิดวันไหนบ้างและกี่โมง?",
        "expected_chunk": "## เกี่ยวกับร้าน\\n\\nMilkLab° เป็นร้านนมสดกลางคืน เปิดทุกวันยกเว้นจันทร์ เวลา 20:00 ถึง 01:00 น.\\nตั้งอยู่หน้ามหาวิทยาลัย รับ delivery ผ่าน LINE OA"
    },
    {
        "question": "ร้านตั้งอยู่ที่ไหน?",
        "expected_chunk": "## เกี่ยวกับร้าน\\n\\nMilkLab° เป็นร้านนมสดกลางคืน เปิดทุกวันยกเว้นจันทร์ เวลา 20:00 ถึง 01:00 น.\\nตั้งอยู่หน้ามหาวิทยาลัย รับ delivery ผ่าน LINE OA"
    },
    {
        "question": "นมหมีฮอกไกโดราคาเท่าไหร่?",
        "expected_chunk": "- นมหมีฮอกไกโด: 65 บาท (นมสดฮอกไกโด + วิปครีม) ขนาด 350 ml\\n- นมโกโก้บราวนี่: 70 บาท (นมสด + ผงโกโก้พรีเมียม + ก้อนบราวนี่) ขนาด 400 ml\\n- นมเสาวรส: 60 บาท (นมสด + น้ำเสาวรสสด) ขนาด 350 ml\\n- นมเย็นใส่วุ้นนม: 55 บาท (นมสด + วุ้นนม) ขนาด 400 ml"
    },
    {
        "question": "มีเมนูอะไรที่มีส่วนผสมของโกโก้บ้าง?",
        "expected_chunk": "- นมหมีฮอกไกโด: 65 บาท (นมสดฮอกไกโด + วิปครีม) ขนาด 350 ml\\n- นมโกโก้บราวนี่: 70 บาท (นมสด + ผงโกโก้พรีเมียม + ก้อนบราวนี่) ขนาด 400 ml\\n- นมเสาวรส: 60 บาท (นมสด + น้ำเสาวรสสด) ขนาด 350 ml\\n- นมเย็นใส่วุ้นนม: 55 บาท (นมสด + วุ้นนม) ขนาด 400 ml"
    },
    {
        "question": "คนแพ้กลูเตนกินบราวนี่ได้ไหม?",
        "expected_chunk": "## Allergen\\n\\n- ทุกเมนูมี lactose จาก milk\\n- บราวนี่มี gluten (wheat)\\n- วิปครีมมี dairy\\n- ลูกค้าแพ้ถั่ว: เมนูทั้งหมดปลอดถั่ว"
    },
    {
        "question": "มีเมนูสำหรับคนกินเจ (vegan) หรือไม่?",
        "expected_chunk": "## FAQ\\n\\n**ส่งได้ไกลแค่ไหน**: รัศมี 5 กม. ค่าส่ง 30 บาท\\n**จองล่วงหน้าได้ไหม**: ได้ ผ่าน LINE OA สั่งก่อน 19:00\\n**กิน vegan ได้ไหม**: ไม่มีเมนู vegan ทุกเมนูใส่นมวัว\\n**ออเดอร์ขั้นต่ำ**: ไม่มี"
    },
    {
        "question": "ค่าส่งเท่าไหร่ และส่งได้ไกลแค่ไหน?",
        "expected_chunk": "## FAQ\\n\\n**ส่งได้ไกลแค่ไหน**: รัศมี 5 กม. ค่าส่ง 30 บาท\\n**จองล่วงหน้าได้ไหม**: ได้ ผ่าน LINE OA สั่งก่อน 19:00\\n**กิน vegan ได้ไหม**: ไม่มีเมนู vegan ทุกเมนูใส่นมวัว\\n**ออเดอร์ขั้นต่ำ**: ไม่มี"
    },
    {
        "question": "จองล่วงหน้าทำยังไง?",
        "expected_chunk": "## FAQ\\n\\n**ส่งได้ไกลแค่ไหน**: รัศมี 5 กม. ค่าส่ง 30 บาท\\n**จองล่วงหน้าได้ไหม**: ได้ ผ่าน LINE OA สั่งก่อน 19:00\\n**กิน vegan ได้ไหม**: ไม่มีเมนู vegan ทุกเมนูใส่นมวัว\\n**ออเดอร์ขั้นต่ำ**: ไม่มี"
    },
    {
        "question": "เมนูไหนปลอดภัยสำหรับคนแพ้ถั่ว?",
        "expected_chunk": "## Allergen\\n\\n- ทุกเมนูมี lactose จาก milk\\n- บราวนี่มี gluten (wheat)\\n- วิปครีมมี dairy\\n- ลูกค้าแพ้ถั่ว: เมนูทั้งหมดปลอดถั่ว"
    },
    {
        "question": "นมเย็นใส่วุ้นนมปริมาณกี่ ml?",
        "expected_chunk": "- นมหมีฮอกไกโด: 65 บาท (นมสดฮอกไกโด + วิปครีม) ขนาด 350 ml\\n- นมโกโก้บราวนี่: 70 บาท (นมสด + ผงโกโก้พรีเมียม + ก้อนบราวนี่) ขนาด 400 ml\\n- นมเสาวรส: 60 บาท (นมสด + น้ำเสาวรสสด) ขนาด 350 ml\\n- นมเย็นใส่วุ้นนม: 55 บาท (นมสด + วุ้นนม) ขนาด 400 ml"
    }
]
"""))

# Evaluation execution
cells.append(new_code_cell("""k = 3
precisions = []
recalls = []
top1_distances = []

for gt in ground_truths:
    query = gt["question"]
    expected = gt["expected_chunk"].strip()
    
    # Retrieve top-k chunks
    retrieved_chunks = retrieve_top_k(query, model, index, chunks, k=k)
    
    # Check match (exact match after stripping)
    retrieved_cleaned = [c.strip() for c in retrieved_chunks]
    
    # In our case, each question has exactly 1 expected chunk.
    hits = 1 if expected in retrieved_cleaned else 0
    
    precision = hits / k
    recall = hits / 1.0 # Total ground truth chunks for the query is 1
    
    precisions.append(precision)
    recalls.append(recall)
    
    # Calculate top-1 distance manually to plot histogram
    query_embedding = model.encode([query], convert_to_numpy=True)
    distances, _ = index.search(query_embedding, 1)
    top1_distances.append(distances[0][0])
    
    print(f"Q: {query}")
    print(f"  -> Hits: {hits}, Precision@{k}: {precision:.2f}, Recall@{k}: {recall:.2f}, Top-1 Dist: {distances[0][0]:.4f}")
"""))

# Metrics results
cells.append(new_code_cell("""avg_precision = np.mean(precisions)
avg_recall = np.mean(recalls)

print(f"\\n--- Overall Metrics (Average over {len(ground_truths)} questions) ---")
print(f"Mean Precision@{k}: {avg_precision:.4f}")
print(f"Mean Recall@{k}: {avg_recall:.4f}")
"""))

# Histogram
cells.append(new_code_cell("""plt.figure(figsize=(8, 5))
plt.hist(top1_distances, bins=10, color='skyblue', edgecolor='black')
plt.title('Histogram of Top-1 Similarity Distances (L2)')
plt.xlabel('L2 Distance (Lower is more similar)')
plt.ylabel('Frequency')
plt.grid(axis='y', alpha=0.75)
plt.show()
"""))

# Reflection placeholder
cells.append(new_markdown_cell("""## Reflection (S3 Worksheet)

*Write your reflections on the evaluation results here...*
- Are the precision and recall scores good?
- What kind of queries does the system struggle with?
- How could we improve the retrieval layer? (e.g., chunk size, different embedding model)
"""))

nb['cells'] = cells

with open('eval.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)
    
print("Notebook eval.ipynb generated successfully!")
