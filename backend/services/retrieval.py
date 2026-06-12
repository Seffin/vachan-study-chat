"""
Vachan Study Bible Chatbot — Retrieval Service
Handles Hybrid Search (BM25 + Vector) and result merging.
"""

from typing import List, Dict, Any
from db.mongodb import get_database


async def atlas_text_search(query: str, book_code: str, lang_code: str, k: int = 10) -> List[Dict[str, Any]]:
    """Performs BM25 lexical search using MongoDB Atlas Search."""
    db = get_database()
    if db is None:
        return []
        
    collection = db["qa_dataset"]
    
    pipeline = [
        {
            "$search": {
                "index": "qa_text_search",
                "compound": {
                    "must": [
                        {
                            "text": {
                                "query": query,
                                "path": ["search_text", "question"]
                            }
                        }
                    ],
                    "filter": [
                        {"text": {"query": book_code, "path": "book_code"}},
                        {"text": {"query": lang_code, "path": "lang_code"}}
                    ]
                }
            }
        },
        {"$limit": k},
        {
            "$project": {
                "_id": 1,
                "book_code": 1,
                "lang_code": 1,
                "reference": 1,
                "question": 1,
                "response": 1,
                "score": {"$meta": "searchScore"}
            }
        }
    ]
    
    try:
        results = []
        async for doc in collection.aggregate(pipeline):
            results.append(doc)
        return results
    except Exception as e:
        print(f"Atlas Text Search Error: {e}")
        return []


async def atlas_vector_search(query_embedding: List[float], book_code: str, lang_code: str, k: int = 10) -> List[Dict[str, Any]]:
    """Performs semantic vector search using MongoDB Atlas Vector Search."""
    db = get_database()
    if db is None:
        return []
        
    collection = db["qa_dataset"]
    
    pipeline = [
        {
            "$vectorSearch": {
                "index": "qa_vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": k * 5,
                "limit": k,
                "filter": {
                    "$and": [
                        {"book_code": book_code},
                        {"lang_code": lang_code}
                    ]
                }
            }
        },
        {
            "$project": {
                "_id": 1,
                "book_code": 1,
                "lang_code": 1,
                "reference": 1,
                "question": 1,
                "response": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    
    try:
        results = []
        async for doc in collection.aggregate(pipeline):
            results.append(doc)
        return results
    except Exception as e:
        print(f"Atlas Vector Search Error: {e}")
        return []


def deduplicate(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merges and deduplicates search results by _id."""
    seen = set()
    merged = []
    
    for doc in results:
        doc_id = str(doc["_id"])
        if doc_id not in seen:
            seen.add(doc_id)
            merged.append(doc)
            
    return merged


async def hybrid_search(query: str, query_embedding: List[float], book_code: str, lang_code: str, k: int = 10) -> List[Dict[str, Any]]:
    """Combines BM25 and Vector search results."""
    bm25_results = []
    vector_results = []
    
    if query:
        bm25_results = await atlas_text_search(query, book_code, lang_code, k=k)
        
    if query_embedding:
        vector_results = await atlas_vector_search(query_embedding, book_code, lang_code, k=k)
        
    # Merge, prioritizing vector search for semantic relevance, then text search
    # This is a naive merge before cross-encoder re-ranking
    merged = deduplicate(vector_results + bm25_results)
    
    return merged[:k]
