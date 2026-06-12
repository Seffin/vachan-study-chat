import os
import sys
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
VECTORSTORES_DIR = os.path.join(BACKEND_DIR, "static_data", "vectorstores", "gemini")

MONGO_URI = os.getenv("MONGO_URI")

def extract_and_migrate():
    if not MONGO_URI:
        print("Error: MONGO_URI is missing in .env")
        sys.exit(1)
        
    print("Connecting to MongoDB Atlas...")
    client = MongoClient(MONGO_URI)
    db = client["vachan_study"]
    collection = db["qa_dataset"]
    
    # Initialize embedding model wrapper (it will not call the API to embed, just required by LangChain to load the local index)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    total_inserted = 0
    
    if not os.path.exists(VECTORSTORES_DIR):
        print(f"Error: Vectorstores directory not found at {VECTORSTORES_DIR}")
        sys.exit(1)
    
    for book_code in os.listdir(VECTORSTORES_DIR):
        index_path = os.path.join(VECTORSTORES_DIR, book_code)
        if not os.path.isdir(index_path):
            continue
            
        faiss_file = os.path.join(index_path, "index.faiss")
        if not os.path.exists(faiss_file):
            continue
            
        print(f"\nLoading FAISS index for {book_code}...")
        try:
            vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
            faiss_index = vectorstore.index
            
            existing_count = collection.count_documents({"book_code": book_code})
            if existing_count >= faiss_index.ntotal:
                print(f"Skipping {book_code}: Already migrated ({existing_count} docs in DB).")
                continue
                
            docstore = vectorstore.docstore._dict
            index_to_docstore_id = vectorstore.index_to_docstore_id
            
            docs_to_insert = []
            
            for i in range(faiss_index.ntotal):
                doc_id = index_to_docstore_id[i]
                document = docstore[doc_id]
                vector = faiss_index.reconstruct(i)
                
                # Parse metadata
                meta = document.metadata
                reference = meta.get("reference", "")
                question = meta.get("question", "")
                response = meta.get("response", "")
                
                # Best-effort parsing of chapter and verse from reference string (e.g., "MAT 1:1" or "MAT 1:1-2")
                chapter, verse = 1, 1
                try:
                    parts = reference.split()
                    if len(parts) > 1:
                        cv = parts[-1].split(':')
                        chapter = int(cv[0])
                        if len(cv) > 1:
                            import re
                            verse_nums = re.findall(r'\d+', cv[1])
                            if verse_nums:
                                verse = int(verse_nums[0])
                except Exception:
                    pass
                
                search_text = f"{reference} {question} {response}"
                
                doc = {
                    "book_code": book_code,
                    "lang_code": "en", # Standard ISO code expected by API
                    "reference": reference,
                    "chapter": chapter,
                    "verse": verse,
                    "question": question,
                    "response": response,
                    "paraphrases": [],
                    "search_text": search_text,
                    "embedding": vector.tolist()[:768],  # TRUNCATE to 768 dims (Matryoshka Representation)
                }
                docs_to_insert.append(doc)
            
            if docs_to_insert:
                print(f"Extracted {len(docs_to_insert)} vectors! Pushing to MongoDB Atlas...")
                operations = [
                    UpdateOne(
                        {"book_code": doc["book_code"], "lang_code": doc["lang_code"], "question": doc["question"]},
                        {"$set": doc},
                        upsert=True
                    ) for doc in docs_to_insert
                ]
                collection.bulk_write(operations)
                total_inserted += len(docs_to_insert)
                print(f"Successfully migrated {book_code}.")
                
        except Exception as e:
            print(f"Error migrating {book_code}: {e}")

    print(f"\n✅ FAISS to MongoDB Migration complete! Total documents inserted: {total_inserted}")

if __name__ == "__main__":
    extract_and_migrate()
