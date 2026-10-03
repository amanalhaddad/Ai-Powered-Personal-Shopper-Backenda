# FILE: app/services/user_service.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId

from app.models.user import ChatSession, ChatMessage, SearchLog, User
from app.persistence.mongo_manager import MongoManager
from app.core.database import sessions_collection, users_collection, search_logs_collection

class UserService:
    def __init__(self):
        self.sessions = MongoManager(sessions_collection)
        self.users = MongoManager(users_collection)
        self.logs = MongoManager(search_logs_collection)

    async def register_user_if_new(self, user_id: str):
        existing = await self.users.find_one({"user_id": user_id})
        if not existing:
            new_user = User(user_id=user_id)
            await self.users.insert_one(new_user.dict())
            return {"status": "created", "user_id": user_id}
        return {"status": "exists", "user_id": user_id}

    async def log_search(self, log: SearchLog):
        await self.logs.insert_one(log.dict())
        return {"status": "logged"}

    async def get_user_sessions(self, user_id: str):
        # Sort by last_updated desc
        return await self.sessions.find_many({"user_id": user_id}, sort=[("last_updated", -1)])

    async def get_session_history(self, session_id: str):
        session = await self.sessions.get_by_id(session_id)
        if session:
            return session.get("messages", [])
        return []

    async def create_session(self, user_id: str, first_message: str) -> str:
        # Create a clean title
        title = first_message[:40] + "..." if len(first_message) > 40 else first_message
        
        session = ChatSession(
            user_id=user_id,
            title=title,
            messages=[]
        )
        # insert_one returns the string ID
        return await self.sessions.insert_one(session.dict(exclude={"id"}))

    # [CRITICAL FIX] Added 'products' parameter here!
    async def add_message(self, session_id: str, sender: str, text: str, products: Optional[List[Dict[str, Any]]] = None):
        
        message = ChatMessage(
            sender=sender,
            text=text,
            products=products  # <--- Saving products to DB
        )
        
        # Use $push to append to the array
        try:
            oid = ObjectId(session_id)
            await sessions_collection.update_one(
                {"_id": oid},
                {
                    "$push": {"messages": message.dict()},
                    "$set": {"last_updated": datetime.utcnow()}
                }
            )
        except Exception as e:
            print(f"❌ Error saving message to DB: {e}")

user_service = UserService()