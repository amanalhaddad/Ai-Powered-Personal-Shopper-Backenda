from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

# 1. Connect to Client
client = AsyncIOMotorClient(settings.MONGODB_URI)

# 2. FORCE the specific DB Name from Config (personal_shopper)
db = client[settings.MONGODB_DBNAME] 

# 3. Define Collections (All in one DB now)
users_collection = db["users"]
products_collection = db["products"]

# Chat & History Collections
sessions_collection = db["sessions"]       # Was going to ai_shopper, now going to personal_shopper
search_logs_collection = db["search_logs"] 

async def get_db():
    return db