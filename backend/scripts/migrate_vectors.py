import os
import sys
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

# Load env
load_dotenv()

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, "data")
STATIC_DATA_DIR = os.path.join(BACKEND_DIR, "static_data")

MONGO_URI = os.getenv("MONGO_URI")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not MONGO_URI:
    print("Error: MONGO_URI is missing in .env")
    sys.exit(1)
if not GEMINI_KEY:
    print("Error: GEMINI_API_KEY is missing in .env")
    sys.exit(1)

def get_embeddings_model():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_KEY)

def migrate_vectors():
    print("Connecting to MongoDB Atlas...")
    client = MongoClient(MONGO_URI)
    db = client["vachan_study"]
    collection = db["vector_embeddings"]
    
    print("Initializing Gemini Embedding Model...")
    embeddings_model = get_embeddings_model()
    
    # We will migrate MAT (Matthew) first as a proof of concept. 
    # You can expand this loop to all TSV files in DATA_DIR later.
    book_code = "MAT"
    lang_code = "en"
    
    csv_path = os.path.join(STATIC_DATA_DIR, f"tq_{book_code}.csv")
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        sys.exit(1)
        
    print(f"Reading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    docs_to_embed = []
    for index, row in df.iterrows():
        question = str(row.get("Question", "")).strip()
        response = str(row.get("Response", "")).strip()
        reference = str(row.get("Reference", "1:1")).strip()
        
        if not question or not response:
            continue
            
        embed_text = f"Question: {question}\nAnswer: {response}"
        docs_to_embed.append({
            "book_code": book_code,
            "lang_code": lang_code,
            "reference": reference,
            "question": question,
            "response": response,
            "embed_text": embed_text
        })

    docs_to_insert = []
    import time
    
    batch_size = 20
    print(f"Total documents to embed: {len(docs_to_embed)}")
    
    i = 0
    while i < len(docs_to_embed):
        batch = docs_to_embed[i:i+batch_size]
        texts = [d["embed_text"] for d in batch]
        print(f"Embedding batch {i} to {i+len(batch)}...")
        
        success = False
        retries = 0
        while not success and retries < 5:
            try:
                vectors = embeddings_model.embed_documents(texts)
                for j, doc in enumerate(batch):
                    doc_copy = doc.copy()
                    del doc_copy["embed_text"]
                    doc_copy["embedding"] = vectors[j]
                    docs_to_insert.append(doc_copy)
                    
                success = True
                i += batch_size
                time.sleep(2) # Prevent spamming
            except Exception as e:
                retries += 1
                wait_time = 15 * retries
                print(f"Network or API Error ({e}). Sleeping {wait_time}s before retry {retries}/5...")
                time.sleep(wait_time)
                
        if not success:
            print(f"Failed to embed batch {i} after 5 retries. Aborting.")
            sys.exit(1)
        
    if docs_to_insert:
        print(f"Inserting {len(docs_to_insert)} vectorized documents into MongoDB Atlas...")
        # Upsert based on question to prevent duplicates
        for doc in docs_to_insert:
            collection.update_one(
                {"book_code": doc["book_code"], "lang_code": doc["lang_code"], "question": doc["question"]},
                {"$set": doc},
                upsert=True
            )
        print("Migration complete!")
    else:
        print("No documents to insert.")

if __name__ == "__main__":
    migrate_vectors()
