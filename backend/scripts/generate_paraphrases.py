"""
Vachan Study Bible Chatbot — Paraphrase Generation Script
Generates paraphrases for dataset questions to enrich lexical BM25 search.
"""

import os
import sys
import json
import asyncio
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not MONGO_URI:
    print("Error: MONGO_URI is missing in .env")
    sys.exit(1)
if not GEMINI_KEY:
    print("Error: GEMINI_API_KEY is missing in .env")
    sys.exit(1)

async def generate_paraphrases(question: str, client) -> list[str]:
    """Generates paraphrases using Gemini."""
    prompt = f"""Generate exactly 4 paraphrases of this question.
Include: active voice, passive voice, synonym replacement, and a casual rephrasing.
Output ONLY a valid JSON array of strings. No explanation, no markdown blocks.

Question: {question}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text.strip()
        # Clean up possible markdown formatting
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        paraphrases = json.loads(text.strip())
        if isinstance(paraphrases, list):
            return paraphrases
        return []
    except Exception as e:
        print(f"Error generating paraphrases for '{question}': {e}")
        return []

async def main():
    print("Connecting to MongoDB Atlas...")
    db_client = MongoClient(MONGO_URI)
    db = db_client["vachan_study"]
    collection = db["qa_dataset"]
    
    from google import genai
    ai_client = genai.Client(api_key=GEMINI_KEY)
    
    # Find documents that don't have paraphrases yet
    docs = list(collection.find({"paraphrases": {"$size": 0}}))
    print(f"Found {len(docs)} documents needing paraphrases.")
    
    for i, doc in enumerate(docs):
        print(f"Processing {i+1}/{len(docs)}: {doc['question']}")
        paraphrases = await generate_paraphrases(doc["question"], ai_client)
        
        if paraphrases:
            # Update the search_text to include the new paraphrases
            search_text = doc["question"] + " " + " ".join(paraphrases)
            
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "paraphrases": paraphrases,
                    "search_text": search_text
                }}
            )
            print(f"  -> Added {len(paraphrases)} paraphrases.")
        
        # Sleep to avoid rate limits
        await asyncio.sleep(2)
        
    print("Paraphrase generation complete.")

if __name__ == "__main__":
    asyncio.run(main())
