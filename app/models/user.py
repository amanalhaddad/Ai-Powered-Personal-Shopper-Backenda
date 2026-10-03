# FILE: app/models/user.py
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime

# 1. Standard User Profile
class User(BaseModel):
    user_id: str
    name: Optional[str] = "Shopper"
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# 2. Search Log
class SearchLog(BaseModel):
    user_id: str
    keyword: str
    platform: Literal["shopee", "lazada", "other"]
    url: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# 3. Chat Message Structure (UPDATED 🛠️)
class ChatMessage(BaseModel):
    sender: Literal["user", "ai"]
    text: str
    # [FIX] This field lets us save product cards in history!
    products: Optional[List[Dict[str, Any]]] = None 
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# 4. Chat Session
class ChatSession(BaseModel):
    id: Optional[str] = None
    user_id: str
    title: str
    messages: List[ChatMessage] = []
    last_updated: datetime = Field(default_factory=datetime.utcnow)

# 5. Request Model for the API
class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None