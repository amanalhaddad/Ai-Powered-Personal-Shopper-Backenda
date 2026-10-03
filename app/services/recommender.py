# FILE: app/services/recommender.py
from typing import List, Optional, Dict
from bson import ObjectId
import asyncio 
from google import genai
from datetime import datetime

from app.persistence.vector_manager import vector_manager
from app.persistence.mongo_manager import MongoManager
from app.core.database import products_collection
from app.core.config import settings

# --- 1. SETUP AI CLIENT ---
ai_client = None
if settings.GOOGLE_API_KEY:
    ai_client = genai.Client(api_key=settings.GOOGLE_API_KEY)

class RecommenderService:
    def __init__(self):
        self.mongo = MongoManager(products_collection)

    # ---------------------------------------------------
    # NEW: AI "Brain" - Generates Buying Advice
    # ---------------------------------------------------
    async def generate_buying_advice(self, user_query: str, product_data: Dict) -> str:
        if not ai_client:
            return "AI Advice unavailable (API Key missing)."

        prompt = f"""
        You are an expert Personal Shopper AI.
        User's Request: "{user_query}"
        
        Product to Analyze:
        Name: {product_data.get('name', 'Unknown Product')}
        Price: {product_data.get('currency', 'MYR')} {product_data.get('price', '0.00')}
        Description: {product_data.get('description', '')[:800]}... (truncated)
        
        Task:
        1. Analyze if this product is a good match for the user.
        2. Write a short, honest advice paragraph and include bullet points (max 3 sentences and below 70 words).
        3. Mention specific features from the description that help the user.
        4. If the product seems unrelated or bad, say so politely.
        """

        # --- RETRY LOOP ---
        for attempt in range(3):
            try:
                # [NOTE] Using 1.5-flash as 2.0/2.5 often hit quotas
                response = await ai_client.aio.models.generate_content(
                    model='gemini-2.5-flash-lite', 
                    contents=prompt
                )
                return response.text

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    wait_time = 4 * (attempt + 1) 
                    print(f"AI Busy (429). Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"AI Generation Error: {e}")
                    return "Could not generate advice at this moment."
        
        return "AI is currently too busy. Please try again later."

    # ---------------------------------------------------
    # 1. Search products (FIXED: Brand Filter + Stricter Threshold)
    # ---------------------------------------------------
    async def search_products(self, query: str, max_price: Optional[float] = None, brand: Optional[str] = None, top_k: int = 5):
        # 1. Query Vector DB
        vector_results = await vector_manager.query_similar_async(query, top_k=top_k)

        final = []
        for item in vector_results:
            # [FIX] Stricter Threshold (Lower = More Strict)
            # If distance > 0.40, it's too different. Force new search.
            if item["score"] > 0.40:
                print(f"⚠️ Skipped '{item['title']}' - Low Relevance ({item['score']:.4f})")
                continue

            product = await self.mongo.get_by_id(item["id"])
            if not product: continue

            # [FIX] Brand Filtering Logic
            if brand:
                # Check if the requested brand is inside the product title (Case Insensitive)
                prod_title = product.get("title", "").lower()
                prod_brand = product.get("brand", "").lower()
                target_brand = brand.lower()
                
                # If the product title/brand DOES NOT contain the requested brand, skip it.
                if target_brand not in prod_title and target_brand not in prod_brand:
                    print(f"⚠️ Skipped '{product['title']}' - Brand Mismatch (Wanted: {brand})")
                    continue

            if max_price is not None:
                p_price = product.get("price")
                if p_price and float(p_price) > max_price: continue

            product["similarity_score"] = item["score"]
            final.append(product)

        return final

    # ---------------------------------------------------
    # 2. Add product (With Image)
    # ---------------------------------------------------
    async def add_product(self, title: str, description: str, price: float, brand: str, url: str, image_url: str = ""):
        product_id = await self.mongo.insert_one({
            "title": title,
            "description": description,
            "price": price,
            "brand": brand,
            "url": url,
            "image": image_url 
        })

        await vector_manager.add_product_async(
            product_id=product_id,
            title=title,
            description=description,
            url=url
        )
        return product_id
    
    # ---------------------------------------------------
    # 3. Add product (UPDATED: Now saves session_id! 🆔)
    # ---------------------------------------------------
    async def add_product(self, title: str, description: str, price: float, brand: str, url: str, image_url: str = "", session_id: str = None):
        
        product_data = {
            "title": title,
            "description": description,
            "price": price,
            "brand": brand,
            "url": url,
            "image": image_url,
            "last_session_id": session_id,  # <--- NEW: Tracks the latest session 
            "updated_at": datetime.utcnow()
        }

        # We use update_one with upsert=True to update existing products or insert new ones
        # This prevents duplicates but updates the session_id
        await self.mongo.collection.update_one(
            {"url": url}, 
            {"$set": product_data}, 
            upsert=True
        )
        
        # We need the ID for Vector DB
        saved_product = await self.mongo.collection.find_one({"url": url})
        product_id = str(saved_product["_id"])

        await vector_manager.add_product_async(
            product_id=product_id,
            title=title,
            description=description,
            url=url
        )
        return product_id

    # ---------------------------------------------------
    # 4. Remove product
    # ---------------------------------------------------
    async def delete_product(self, product_id: str):
        try:
            oid = ObjectId(product_id)
            await self.mongo.delete_one({"_id": oid})
        except: pass
            
        vector_manager.delete_product(product_id)
        return True

recommender_service = RecommenderService()