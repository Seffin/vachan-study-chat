# Walkthrough: RAG Pipeline Architecture Refactoring

The backend has been completely rewritten following the approved implementation plan. We have moved from a 1300-line monolithic script to a clean, service-oriented architecture with a powerful new Hybrid Search pipeline.

## What Was Accomplished

1. **Clean Architecture Refactoring**
   - Extracted central configurations to [config.py](file:///h:/Seffin/Benjamin/Logos%20Bible%20Study%20Chatbot/backend/config.py)
   - Extracted Pydantic models to [schemas/](file:///h:/Seffin/Benjamin/Logos%20Bible%20Study%20Chatbot/backend/schemas)
   - Extracted database operations to [db/repositories.py](file:///h:/Seffin/Benjamin/Logos%20Bible%20Study%20Chatbot/backend/db/repositories.py)
   - Separated business logic into [services/](file:///h:/Seffin/Benjamin/Logos%20Bible%20Study%20Chatbot/backend/services):
     - `retrieval.py` (Hybrid Search logic)
     - `reranker.py` (Confidence scoring & LLM verification)
     - `translation.py` (Language detection & mapping)
     - `ai_generation.py` (Fallback generation)
     - `embedding.py` (Vector generation)
     - `rate_limiter.py` (Token tracking)
   - The main [api/index.py](file:///h:/Seffin/Benjamin/Logos%20Bible%20Study%20Chatbot/backend/api/index.py) is now a clean 380-line routing controller that orchestrates the services.

2. **New Hybrid Search Pipeline**
   - The system now performs a `hybrid_search` combining MongoDB Atlas Search (BM25 lexical) and MongoDB Vector Search (semantic).
   - This ensures exact keyword matches (e.g. "Genesis 1:1") and semantic matches (e.g. "active vs passive voice") are both retrieved.

3. **Confidence Thresholding**
   - **High Confidence (≥0.85)**: Returns the dataset native answer immediately.
   - **Medium Confidence (0.50 - 0.84)**: Uses LLM verification to confirm if the match is correct.
   - **Low Confidence (<0.50)**: Skips dataset and uses general AI generation.

4. **New Database Design**
   - Added `backend/scripts/setup_mongodb.py` updates to create the new `qa_dataset` collection.
   - The new schema supports `paraphrases`, `chapter`, `verse`, and a combined `search_text` field for improved BM25 performance.
   - Created migration scripts: `migrate_to_qa_dataset.py` and `generate_paraphrases.py`.

---

## 🛠️ Required Migration Steps

Because we changed the database schema and indexing strategy, you must run a few commands to initialize the new architecture. The old API might throw errors until this is complete.

### Step 1: Run MongoDB Setup
This will create the new collection (`qa_dataset`) and apply standard indexes:
```bash
cd backend
python scripts\setup_mongodb.py
```

### Step 2: Create Atlas Indexes (Manual step in Atlas UI)
You need to create two indexes for the new `qa_dataset` collection in your MongoDB Atlas Dashboard.

**1. Create the Atlas Search Index (for BM25)**
- Go to Atlas → Search → Create Search Index → JSON Editor
- Select Database: `vachan_study`, Collection: `qa_dataset`
- Index Name: `qa_text_search`
- Definition:
```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "search_text": { "type": "string", "analyzer": "luceneStandard", "searchAnalyzer": "luceneStandard" },
      "question": { "type": "string", "analyzer": "luceneStandard" },
      "book_code": { "type": "stringFacet" },
      "lang_code": { "type": "stringFacet" },
      "reference": { "type": "string", "analyzer": "luceneKeyword" }
    }
  }
}
```

**2. Create the Vector Search Index**
- Go to Atlas → Search → Create Search Index → JSON Editor
- Select Database: `vachan_study`, Collection: `qa_dataset`
- Index Name: `qa_vector_index`
- Definition:
```json
{
  "type": "vectorSearch",
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    },
    { "type": "filter", "path": "book_code" },
    { "type": "filter", "path": "lang_code" }
  ]
}
```
*(Note: I set numDimensions to 768 since we are keeping Gemini embeddings for now as per Option A).*

### Step 3: Run the Migration Script
This will load `tq_MAT.csv` and embed it into the new `qa_dataset` collection:
```bash
python scripts\migrate_to_qa_dataset.py
```

### Step 4: (Optional but Recommended) Run Paraphrase Generator
This will use Gemini to generate 4 variations (active/passive/synonyms) for every question in the dataset, significantly boosting retrieval accuracy:
```bash
python scripts\generate_paraphrases.py
```

---

## Verification

Once the migration is complete, you can start the backend (`python api\index.py`) and try asking:
- "What was Joseph's reason for wanting to divorce Mary?" (Passive/synonym check)
- "Does Matthew 1 mention Tamar?" (Lexical BM25 check)

The API should now be much faster for exact/high-confidence matches and will only invoke the LLM when in the "medium confidence" threshold zone.
