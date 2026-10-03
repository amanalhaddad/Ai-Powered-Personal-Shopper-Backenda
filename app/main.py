from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Import Routers
from app.routes import users, products, search
from app.routes import scraper as shopee_scraper
# [FIX] Use the exact filename from your screenshot
from app.routes import lazada_scraper 

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

# CORS (Allows Chrome Extension to talk to Backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

# 1. User & Tracking
app.include_router(users.router, prefix="/api/v1/users", tags=["Users & Tracking"])

# 2. Products
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])

# 3. Search & AI Analysis
app.include_router(search.router, prefix="/api/v1/search", tags=["AI Search"])

# 4. Scrapers
app.include_router(shopee_scraper.router, prefix="/api/v1", tags=["Shopee Scraper"])
app.include_router(lazada_scraper.router, prefix="/api/v1", tags=["Lazada Scraper"])

# ---------------------------------------------------------
# EVENTS
# ---------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("✅ Application is starting up...")
    print(f"✅ Loaded Settings: {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Verify DB Connection
    print(f"✅ Connected to DB: {settings.MONGODB_DBNAME}")

@app.get("/")
def root():
    return {
        "message": "AI Personal Shopper API is running 🚀", 
        "docs": "/docs"
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": settings.APP_VERSION}