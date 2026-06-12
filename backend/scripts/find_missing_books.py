import os

STATIC_DIR = r"h:\Seffin\Benjamin\Logos Bible Study Chatbot\backend\static_data"
VECTOR_DIR = os.path.join(STATIC_DIR, "vectorstores", "gemini")

csv_files = [f for f in os.listdir(STATIC_DIR) if f.startswith("tq_") and f.endswith(".csv")]
csv_books = [f.replace("tq_", "").replace(".csv", "") for f in csv_files]

compiled_books = os.listdir(VECTOR_DIR)

missing_books = sorted(list(set(csv_books) - set(compiled_books)))

print(f"Total CSV Books: {len(csv_books)}")
print(f"Compiled FAISS Books: {len(compiled_books)}")
print(f"Missing Books: {missing_books}")
