import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from services.embedding import get_embeddings_model
from services.retrieval import hybrid_search

async def test():
    query = "What did God make on the second day?"
    book_code = "GEN"
    embeddings_model = get_embeddings_model("gemini")
    en_embedding = embeddings_model.embed_query(query)
    
    print(f"Query Dim: {len(en_embedding)}")
    
    candidates = await hybrid_search(query, en_embedding, book_code, "en", k=10)
    print(f"Found {len(candidates)} candidates.")
    for c in candidates:
        print(f"  - [Score: {c.get('score')}, VScore: {c.get('vector_score')}, TScore: {c.get('text_score')}] Q: {c['question']} | A: {c['response']}")
        
if __name__ == "__main__":
    asyncio.run(test())
