# app/models/product.py

from pydantic import BaseModel
from typing import Optional, List

class Product(BaseModel):
    product_id: str
    name: str
    price: float
    rating: Optional[float] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    source: str  # Lazada / Shopee
    description: Optional[str] = None
    categories: Optional[List[str]] = None
