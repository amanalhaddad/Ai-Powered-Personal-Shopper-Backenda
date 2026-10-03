import asyncio
from app.models.product import Product
from app.persistence.mongo_manager import MongoManager
from app.persistence.vector_manager import vector_manager
# [CRITICAL] This imports the 'personal_shopper' collection we defined in database.py
from app.core.database import products_collection

# Helper to clean text
try:
    from app.utils.preprocess import clean_text
except ImportError:
    def clean_text(text): return text.strip() if text else ""

# 1. Initialize Manager with the correct Collection
mongo = MongoManager(products_collection)

async def ingest_product_async(product_data: dict):
    """
    Ingest flow: Clean -> Validate -> Mongo -> ChromaDB
    """
    # ---------- 1. CLEAN ----------
    product_data["title"] = clean_text(product_data.get("title", ""))
    product_data["description"] = clean_text(product_data.get("description", ""))

    # ---------- 2. MODEL VALIDATION ----------
    product = Product(**product_data)
    
    # ---------- 3. MONGO INSERT ----------
    product_id = await mongo.insert_one(product.dict())

    # ---------- 4. VECTOR DB INSERT ----------
    await vector_manager.add_product_async(
        product_id=product_id,
        title=product.title,
        description=product.description,
        url=getattr(product, "url", "") 
    )

    return {"status": "ingested", "id": product_id}