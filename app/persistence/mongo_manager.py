from typing import Dict, Any, List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

class MongoManager:
    def __init__(self, collection: AsyncIOMotorCollection):
        """
        Initialize with a specific Motor collection (from database.py)
        """
        self.collection = collection

    # Helper: Convert Mongo _id (ObjectId) -> string "id"
    def serialize(self, document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not document:
            return None
        document["id"] = str(document["_id"])
        del document["_id"]
        return document

    async def insert_one(self, data: Dict[str, Any]) -> str:
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)

    async def insert_many(self, data: List[Dict[str, Any]]):
        result = await self.collection.insert_many(data)
        return [str(_id) for _id in result.inserted_ids]

    async def find_one(self, query: Dict[str, Any]):
        doc = await self.collection.find_one(query)
        return self.serialize(doc)

    async def get_by_id(self, id_str: str):
        try:
            oid = ObjectId(id_str)
            doc = await self.collection.find_one({"_id": oid})
            return self.serialize(doc)
        except Exception:
            # Invalid ID format or not found
            return None

    async def find_many(self, query: Dict[str, Any], limit: int = 50, sort: List = None):
        # [UPDATED] Added sort support for chat history (Newest first)
        cursor = self.collection.find(query)
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.limit(limit)
        
        results = []
        async for doc in cursor:
            results.append(self.serialize(doc))
        return results

    async def update_one(self, query: Dict[str, Any], data: Dict[str, Any]):
        # $set prevents overwriting the whole document
        result = await self.collection.update_one(query, {"$set": data})
        return result.modified_count > 0

    # [NEW] Critical for Chat History: Appends to a list instead of replacing it
    async def update_push(self, query: Dict[str, Any], field: str, value: Any):
        """
        Example: Push a new message object into the 'messages' array
        """
        result = await self.collection.update_one(query, {"$push": {field: value}})
        return result.modified_count > 0

    async def delete_one(self, query: Dict[str, Any]):
        result = await self.collection.delete_one(query)
        return result.deleted_count > 0