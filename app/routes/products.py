from fastapi import APIRouter, HTTPException
from typing import List
from app.models.product import Product
from app.persistence.mongo_manager import MongoManager
from app.core.database import products_collection  # <--- Imported from database.py

router = APIRouter(prefix="/products", tags=["Products"])

# Pass the actual collection object
mongo = MongoManager(products_collection)

@router.post("/", response_model=Product)
async def add_product(product: Product):
    product_id = await mongo.insert_one(product.dict())
    
    new_prod = product.dict()
    new_prod["id"] = product_id
    return new_prod

@router.get("/", response_model=List[Product])
async def get_all_products():
    # Use generic name: find_many
    products = await mongo.find_many({}, limit=100)
    return products

@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await mongo.get_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product