#!/usr/bin/env python3
"""
Vachan Study Bible Study Chatbot - unfoldingWord Persistent Vector DB Pre-compiler CLI
This script reads all book TSV files, generates Gemini or OpenAI Embeddings, and pre-compiles 
persistent local FAISS vector stores to static_data/vectorstores, enabling instant startup and 
low-latency queries in Vercel.
"""

import os
import json
import shutil
import time
import pandas as pd
import subprocess
import urllib.request
import zipfile
import io
from dotenv import load_dotenv

# Load configurations
load_dotenv()

# Determine directories relative to this script's location (backend/scripts/build_vector_db.py)
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, "data")
STATIC_DATA_DIR = os.path.join(BACKEND_DIR, "static_data")
TQ_DIR = os.path.join(DATA_DIR, "en_tq")
VECTORSTORES_DIR = os.path.join(STATIC_DATA_DIR, "vectorstores")

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

CSV_PATH = os.path.join(STATIC_DATA_DIR, "tq_MAT.csv")
JSON_PATH = os.path.join(STATIC_DATA_DIR, "bible_MAT.json")

def bootstrap_data():
    """Generates standard datasets in static_data if they aren't in the directory yet."""
    os.makedirs(STATIC_DATA_DIR, exist_ok=True)
    
    # 1. Generate Q&A unfoldingWord CSV Dataset
    if not os.path.exists(CSV_PATH):
        print("[BOOTSTRAP] Creating tq_MAT.csv in static_data...")
        qa_data = [
            {
                "Reference": "1:1",
                "Question": "Why is the genealogy of Jesus important in Matthew 1?",
                "Response": "The genealogy of Jesus Christ serves as a legal and theological bridge. Matthew traces Jesus' lineage back to Abraham (covenant identity) and David (royal kingship), proving He legally inherits the messianic promises as the promised Messiah."
            },
            {
                "Reference": "1:18",
                "Question": "How did Mary become pregnant?",
                "Response": "Now the birth of Jesus Christ took place in this way. When His mother Mary had been betrothed to Joseph, before they came together she was found to be with child from the Holy Spirit."
            },
            {
                "Reference": "1:19",
                "Question": "Why did Joseph want to divorce Mary?",
                "Response": "And her husband Joseph, being a just man (upright keeper of the Law) and unwilling to put Mary to public shame or social disgrace, resolved to divorce her quietly through a private contract before two witnesses rather than exposing her to public judgment."
            },
            {
                "Reference": "1:20",
                "Question": "What did Joseph do next after the dream?",
                "Response": "But as he considered these things, behold, an angel of the Lord appeared to him in a dream, saying, 'Joseph, son of David, do not fear to take Mary as your wife, for that which is conceived in her is from the Holy Spirit.' Upon waking, Joseph immediately acted on faith and took Mary as his wife."
            },
            {
                "Reference": "1:21",
                "Question": "What will Mary do and what should the child be named?",
                "Response": "She will bear a son, and you shall call His name Jesus, for He will save His people from their sins, fulfilling the divine rescue plan."
            },
            {
                "Reference": "1:23",
                "Question": "Explain the significance of the name Immanuel.",
                "Response": "The prophet's words were fulfilled: 'Behold, the virgin shall conceive and bear a son, and they shall call His name Immanuel' (which means, God with us). It signifies God entering human history in physical form to dwell directly among His people."
            },
            {
                "Reference": "1:24",
                "Question": "What did Joseph do when he woke from sleep?",
                "Response": "When Joseph woke from sleep, he did as the angel of the Lord commanded him: he took his wife Mary, demonstrating absolute obedience and covenant trust."
            }
        ]
        df = pd.DataFrame(qa_data)
        df.to_csv(CSV_PATH, index=False)
        print("[BOOTSTRAP] tq_MAT.csv created successfully.")

    # 2. Generate Scripture Json Dataset
    if not os.path.exists(JSON_PATH):
        print("[BOOTSTRAP] Creating bible_MAT.json in static_data...")
        bible_mat = {
            "book": "Matthew",
            "chapter": 1,
            "verses": [
                {"verse": 1, "text": "The book of the genealogy of Jesus Christ, the son of David, the son of Abraham."},
                {"verse": 2, "text": "Abraham was the father of Isaac, and Isaac the father of Jacob, and Jacob the father of Judah and his brothers,"},
                {"verse": 3, "text": "and Judah the father of Perez and Zerah by Tamar, and Perez the father of Hezron, and Hezron the father of Ram,"},
                {"verse": 4, "text": "and Ram the father of Amminadab, and Amminadab the father of Nahshon, and Nahshon the father of Salmon,"},
                {"verse": 5, "text": "and Salmon the father of Boaz by Rahab, and Boaz the father of Obed by Ruth, and Obed the father of Jesse,"},
                {"verse": 6, "text": "and Jesse the father of David the king. And David was the father of Solomon by the wife of Uriah,"},
                {"verse": 7, "text": "and Solomon the father of Rehoboam, and Rehoboam the father of Abijah, and Abijah the father of Asaph,"},
                {"verse": 8, "text": "and Asaph the father of Jehoshaphat, and Jehoshaphat the father of Joram, and Joram the father of Uzziah,"},
                {"verse": 9, "text": "and Uzziah the father of Jotham, and Jotham the father of Ahaz, and Ahaz the father of Hezekiah,"},
                {"verse": 10, "text": "and Hezekiah the father of Manasseh, and Manasseh the father of Amos, and Amos the father of Josiah,"},
                {"verse": 11, "text": "and Josiah the father of Jechoniah and his brothers, at the time of the deportation to Babylon."},
                {"verse": 12, "text": "And after the deportation to Babylon: Jechoniah was the father of Shealtiel, and Shealtiel the father of Zerubbabel,"},
                {"verse": 13, "text": "and Zerubbabel the father of Abiud, and Abiud the father of Eliakim, and Eliakim the father of Azor,"},
                {"verse": 14, "text": "and Azor the father of Zadok, and Zadok the father of Achim, and Achim the father of Eliud,"},
                {"verse": 15, "text": "and Eliud the father of Eleazar, and Eleazar the father of Matthan, and Matthan the father of Jacob,"},
                {"verse": 16, "text": "and Jacob the father of Joseph the husband of Mary, of whom Jesus was born, who is called Christ."},
                {"verse": 17, "text": "So all the generations from Abraham to David were fourteen generations, and from David to the deportation to Babylon fourteen generations, and from the deportation to Babylon to the Christ fourteen generations."},
                {"verse": 18, "text": "This is how the birth of Jesus the Messiah came about: His mother Mary was pledged to be married to Joseph, but before they came together, she was found to be pregnant through the Holy Spirit."},
                {"verse": 19, "text": "Because Joseph her husband was faithful to the law, and yet did not want to expose her to public disgrace, he had in mind to divorce her quietly."},
                {"verse": 20, "text": "But after he had considered this, an angel of the Lord appeared to him in a dream and said, 'Joseph son of David, do not be afraid to take Mary home as your wife, because what is conceived in her is from the Holy Spirit."},
                {"verse": 21, "text": "She will give birth to a son, and you are to give him the name Jesus, because he will save his people from their sins."},
                {"verse": 22, "text": "All this took place to fulfill what the Lord had said through the prophet:"},
                {"verse": 23, "text": "'The virgin will conceive and give birth to a son, and they will call him Immanuel' (which means 'God with us')."},
                {"verse": 24, "text": "When Joseph woke up, he did what the angel of the Lord had commanded him and took Mary home as his wife."},
                {"verse": 25, "text": "But he did not consummate their marriage until she gave birth to a son. And he gave him the name Jesus."}
            ]
        }
        with open(JSON_PATH, "w") as f:
            json.dump(bible_mat, f, indent=4)
        print("[BOOTSTRAP] bible_MAT.json created successfully.")

def clone_en_tq():
    """Clones or downloads/extracts the unfoldingWord en_tq repository if not present."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(TQ_DIR) and any(f.endswith('.tsv') for f in os.listdir(TQ_DIR)):
        print("[BOOTSTRAP] unfoldingWord en_tq repository already present and populated.")
        return

    print("[BOOTSTRAP] unfoldingWord en_tq repository not found or unpopulated. Initializing acquisition...")
    
    # Method 1: Git Shallow Clone
    try:
        print("[BOOTSTRAP] Attempting git clone --depth 1...")
        if os.path.exists(TQ_DIR):
            shutil.rmtree(TQ_DIR)
            
        git_url = os.environ.get("TQ_SOURCE_URL", "https://git.door43.org/unfoldingWord/en_tq.git")
        subprocess.run(
            ["git", "clone", "--depth", "1", git_url, TQ_DIR],
            check=True,
            capture_output=True,
            text=True
        )
        print("[BOOTSTRAP] git clone --depth 1 completed successfully.")
        return
    except Exception as e:
        print(f"[BOOTSTRAP] Git clone failed or not available ({e}). Trying HTTP fallback download...")
        
    # Method 2: HTTP ZIP Download Failsafe
    zip_url = os.environ.get("TQ_ZIP_FALLBACK_URL", "https://git.door43.org/unfoldingWord/en_tq/archive/master.zip")

    try:
        print(f"[BOOTSTRAP] Fetching archive from {zip_url}...")
        req = urllib.request.Request(
            zip_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) VachanStudyBibleChatbot/1.0'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            zip_data = response.read()
            
        print("[BOOTSTRAP] Archive fetched successfully. Extracting ZIP...")
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
            temp_extract_dir = os.path.join(DATA_DIR, "en_tq_temp")
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            os.makedirs(temp_extract_dir, exist_ok=True)
            zip_ref.extractall(temp_extract_dir)
            
            # Locate root folder inside temp_extract_dir
            extracted_folders = os.listdir(temp_extract_dir)
            if extracted_folders:
                root_extracted = os.path.join(temp_extract_dir, extracted_folders[0])
                if os.path.exists(TQ_DIR):
                    shutil.rmtree(TQ_DIR)
                shutil.move(root_extracted, TQ_DIR)
                shutil.rmtree(temp_extract_dir)
                print("[BOOTSTRAP] unfoldingWord en_tq ZIP downloaded and extracted successfully.")
                return
            else:
                raise ValueError("Extracted zip archive was empty.")
    except Exception as zip_err:
        print(f"[BOOTSTRAP] Failsafe ZIP download/extract failed ({zip_err}).")
        print("[BOOTSTRAP] WARNING: Dynamic multi-book RAG will fall back to local hardcoded Matthew 1 context.")

def prebuild_vector_db():
    print("=" * 75)
    print("VACHAN STUDY BIBLE CHATBOT - PERSISTENT VECTOR DB PRE-COMPILER CLI")
    print("=" * 75)

    # Trigger Self-Healing data bootstrapping mechanisms
    bootstrap_data()
    clone_en_tq()

    if not OPENAI_KEY and not GEMINI_KEY:
        print("[ERROR] Neither OPENAI_API_KEY nor GEMINI_API_KEY is set in your env configs (.env).")
        print("        A live API Key is required to compile persistent FAISS vector stores.")
        print("        Please add your GEMINI_API_KEY or OPENAI_API_KEY to your '.env' file.")
        print("=" * 75)
        return

    # Verify source directory
    if not os.path.exists(TQ_DIR):
        print("[ERROR] unfoldingWord en_tq source directory is missing. Exiting.")
        return

    import sys
    
    # Check if a specific book argument was provided (e.g. 'GEN')
    target_book = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].upper().strip()
        if arg != "ALL":
            target_book = arg

    # Check if a specific provider argument was provided (e.g. 'gemini' or 'openai')
    target_provider = None
    if len(sys.argv) > 2:
        target_provider = sys.argv[2].lower().strip()

    # Find all Translation Questions TSV files
    tsv_files = [f for f in os.listdir(TQ_DIR) if f.startswith("tq_") and f.endswith(".tsv")]
    if not tsv_files:
        print("[ERROR] No tq_*.tsv files found in backend/data/en_tq/. Exiting.")
        return

    if target_book:
        target_file = f"tq_{target_book}.tsv"
        if target_file in tsv_files:
            tsv_files = [target_file]
            print(f"[INFO] Target Book Selected: {target_book}")
        else:
            available_books = ", ".join([f.replace('tq_', '').replace('.tsv', '') for f in sorted(tsv_files)])
            print(f"[ERROR] Book dataset '{target_book}' not found in backend/data/en_tq/.")
            print(f"        Available books: {available_books}")
            return

    print(f"[SUCCESS] Found {len(tsv_files)} book Q&A datasets. Initializing vector DB generation...")
    os.makedirs(VECTORSTORES_DIR, exist_ok=True)

    # Load LangChain libraries dynamically
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document as LCDocument
    except ImportError as e:
        print(f"[ERROR] Failed to import required RAG libraries. Run 'pip install -r requirements.txt': {e}")
        return

    # Build active environments list
    jobs = []
    
    if GEMINI_KEY and (not target_provider or target_provider == "gemini"):
        try:
            # Try GoogleGenerativeAIEmbeddings first (standard in langchain_google_genai)
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings as GeminiEmbeddings
            except ImportError:
                from langchain_google_genai import GoogleGenAIEmbeddings as GeminiEmbeddings
                
            jobs.append({
                "provider": "gemini",
                "embeddings": GeminiEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_KEY),
                "subdir": "gemini"
            })
            print("[INFO] Gemini API Key detected. Will compile Gemini FAISS Vectorstore.")
        except Exception as e:
            print(f"[WARNING] Failed to load Gemini embeddings ({e})")

    if OPENAI_KEY and (not target_provider or target_provider == "openai"):
        try:
            from langchain_openai import OpenAIEmbeddings
            jobs.append({
                "provider": "openai",
                "embeddings": OpenAIEmbeddings(openai_api_key=OPENAI_KEY),
                "subdir": "openai"
            })
            print("[INFO] OpenAI API Key detected. Will compile OpenAI FAISS Vectorstore.")
        except Exception as e:
            print(f"[WARNING] Failed to load OpenAIEmbeddings ({e})")

    for job in jobs:
        provider = job["provider"]
        embeddings = job["embeddings"]
        subdir = job["subdir"]
        
        print("\n" + "#" * 65)
        print("[Read TSV Folder] ---> [Apply Schema Filter] ---> [Compute Multi-Book Embeddings] ---> [Serialize Local Binary]")
        print(f"COMPILING VECTOR STORE FOR PROVIDER: {provider.upper()}")
        print("#" * 65)
        
        success_count = 0
        fail_count = 0
        consecutive_failures = 0
        dest_subdir_dir = os.path.join(VECTORSTORES_DIR, subdir)
        os.makedirs(dest_subdir_dir, exist_ok=True)

        for filename in sorted(tsv_files):
            book_code = filename.replace("tq_", "").replace(".tsv", "").upper().strip()
            tsv_path = os.path.join(TQ_DIR, filename)
            index_path = os.path.join(dest_subdir_dir, book_code)

            if consecutive_failures >= 3:
                # Calculate how many books are remaining to be compiled
                remaining_books = len(tsv_files) - sorted(tsv_files).index(filename)
                fail_count += remaining_books
                print(f"\n[ABORT] Skipping remaining {remaining_books} books for {provider.upper()} due to {consecutive_failures} consecutive failures (e.g. invalid key or quota limit).")
                break

            # Skip compilation if vector index already exists (Incremental Compilation)
            if os.path.exists(index_path) and os.path.exists(os.path.join(index_path, "index.faiss")):
                print(f"[SKIP] Vector index for '{book_code}' already exists at {index_path}. Skipping.")
                success_count += 1
                consecutive_failures = 0
                continue

            print(f"\n[PROCESSING] Book: {book_code} ({filename})")
            
            try:
                # Read TSV
                df = pd.read_csv(tsv_path, sep='\t')
                
                # Normalize column names
                df.rename(columns={
                    'reference': 'Reference',
                    'Reference': 'Reference',
                    'question': 'Question',
                    'Question': 'Question',
                    'response': 'Response',
                    'Response': 'Response'
                }, inplace=True)
                
                # Normalize column headers whitespace
                df.columns = df.columns.str.strip()
                
                # Fill missing values
                df['Reference'] = df['Reference'].fillna('1:1').astype(str)
                df['Question'] = df['Question'].fillna('').astype(str)
                df['Response'] = df['Response'].fillna('').astype(str)

                # Save cleaned CSV file in static_data for offline serverless fallback on Vercel
                clean_csv_filename = f"tq_{book_code}.csv"
                clean_csv_path = os.path.join(STATIC_DATA_DIR, clean_csv_filename)
                df.to_csv(clean_csv_path, index=False)

                # Skip empty datasets
                if df.empty or len(df.dropna(subset=['Question', 'Response'])) == 0:
                    print(f"[WARNING] Skipping '{book_code}': Dataset has no valid Q&A rows.")
                    continue

                # Convert to LangChain Documents
                lc_docs = []
                for _, row in df.iterrows():
                    page_content = f"Reference: {row['Reference']}\nQuestion: {row['Question']}\nResponse: {row['Response']}"
                    lc_docs.append(LCDocument(
                        page_content=page_content,
                        metadata={
                            "reference": str(row["Reference"]),
                            "question": str(row["Question"]),
                            "response": str(row["Response"])
                        }
                    ))

                # Build FAISS vector database with batching and retry logic for rate limits
                print(f"   Generating {provider} embeddings for {len(lc_docs)} Q&A chunks (batched to prevent rate limits)...")
                
                max_retries = 6
                base_delay = 20
                batch_size = 100  # Process in batches of 100 Q&A chunks to drastically minimize request volume
                vectorstore = None
                
                for i in range(0, len(lc_docs), batch_size):
                    batch = lc_docs[i:i + batch_size]
                    batch_num = (i // batch_size) + 1
                    total_batches = (len(lc_docs) + batch_size - 1) // batch_size
                    print(f"   Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
                    
                    for attempt in range(1, max_retries + 1):
                        try:
                            if vectorstore is None:
                                vectorstore = FAISS.from_documents(batch, embeddings)
                            else:
                                vectorstore.add_documents(batch)
                            break  # Success, move to next batch!
                        except Exception as embed_err:
                            err_msg = str(embed_err)
                            is_rate_limit = any(term in err_msg.lower() for term in ["429", "quota", "exhausted", "rate", "limit"])
                            is_temporary = any(term in err_msg.lower() for term in ["retry", "requestsperminute", "requestsperday", "requests per minute", "requests per day"])
                            is_permanent_quota = any(term in err_msg.lower() for term in ["insufficient_quota", "insufficient_funds", "billing"]) and not is_temporary
                            if is_rate_limit and not is_permanent_quota and attempt < max_retries:
                                sleep_dur = 65  # Sleep for 65 seconds to fully reset the 1-minute API rate limit window
                                print(f"   [RATE LIMIT] Hit temporary limit on batch {batch_num} (attempt {attempt}/{max_retries}).")
                                print(f"                Sleeping for {sleep_dur} seconds to completely reset the API window...")
                                time.sleep(sleep_dur)
                            else:
                                raise embed_err  # Re-raise if not a rate limit, or exhausted all retries
                    
                    # Pace the requests to stay well under 15 RPM
                    time.sleep(5)
                
                # Persist FAISS index to disk
                if os.path.exists(index_path):
                    shutil.rmtree(index_path)
                os.makedirs(index_path, exist_ok=True)
                vectorstore.save_local(index_path)
                
                # Introduce a small pre-emptive sleep between books
                time.sleep(4)
                
                print(f"[SUCCESS] Persistent Vector DB ({provider}) compiled and saved to disk for '{book_code}'!")
                success_count += 1
                consecutive_failures = 0
            except Exception as err:
                print(f"[ERROR] Failed to build index for '{book_code}' using {provider}: {err}")
                fail_count += 1
                consecutive_failures += 1

        print("\n" + "=" * 75)
        print(f"COMPLETE SUMMARY FOR {provider.upper()}")
        print(f"   - Total Books Successfully Compiled: {success_count}")
        print(f"   - Total Books Failed: {fail_count}")
        print(f"   - Persistent indices saved to: {dest_subdir_dir}")
        print("=" * 75)

if __name__ == "__main__":
    prebuild_vector_db()
