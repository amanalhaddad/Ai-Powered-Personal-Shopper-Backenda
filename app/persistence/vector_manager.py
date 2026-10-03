import chromadb
from chromadb.config import Settings
import asyncio
from typing import List, Dict, Any

from app.core.config import settings
from app.services.embeddings import embedding_service 

class VectorManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)

        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )

    # --------------------------
    #  Sync Method
    # --------------------------
    def add_product(self, product_id: str, title: str, description: str, url: str):
        text_to_embed = f"{title}. {description}"
        vector = embedding_service.encode(text_to_embed)

        self.collection.upsert(
            ids=[product_id],
            embeddings=[vector],
            metadatas=[{"title": title, "description": description[:1000], "url": url}],
            documents=[text_to_embed]
        )
        return True

    # --------------------------
    #  Async Wrapper
    # --------------------------
    async def add_product_async(self, product_id: str, title: str, description: str, url: str):
        text_to_embed = f"{title}. {description}"
        # Matches the method name in your embeddings.py
        vector = await embedding_service.embed_text_async(text_to_embed)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self.collection.upsert(
                ids=[product_id],
                embeddings=[vector],
                metadatas=[{"title": title, "description": description[:1000], "url": url}],
                documents=[text_to_embed]
            )
        )
        return True

    # --------------------------
    #  Querying
    # --------------------------
    async def query_similar_async(self, query: str, top_k: int = 5):
        query_vector = await embedding_service.embed_text_async(query)

        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None, 
            lambda: self.collection.query(
                query_embeddings=[query_vector],
                n_results=top_k
            )
        )

        formatted = []
        if results["ids"]:
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "id": results["ids"][0][i],
                    "title": results["metadatas"][0][i].get("title"),
                    "description": results["metadatas"][0][i].get("description"),
                    "url": results["metadatas"][0][i].get("url"),
                    "score": results["distances"][0][i],
                    "snippet": results["documents"][0][i]
                })

        return formatted
    
    # --------------------------
    #  Add this to VectorManager
    # --------------------------
    def delete_product(self, product_id: str):
        try:
            # We cast to str just to be safe
            self.collection.delete(ids=[str(product_id)])
            return True
        except Exception as e:
            print(f"Error deleting from Chroma: {e}")
            return False

# Initialize Singleton
vector_manager = VectorManager()