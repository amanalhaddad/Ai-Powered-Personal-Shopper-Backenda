from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Personal Shopper"
    APP_VERSION: str = "1.0.0"

    # Backend
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # MongoDB
    # [FIX 1] Use 'localhost' for local testing (change to 'mongo' only if using Docker Compose)
    MONGODB_URI: str = "mongodb://localhost:27017"
    
    # [FIX 2] Match the exact name from your Screenshot (with underscore)
    MONGODB_DBNAME: str = "personal_shopper"

    # ChromaDB
    CHROMA_DB_DIR: str = "./vector_store"
    CHROMA_COLLECTION: str = "products"

    # AI Config 
    GOOGLE_API_KEY: str = "AIzaSyD3kBnDwem2OyQPXD4ZtTRjTBn_EtGIWCw" 
    
    # Embeddings model 
    EMBEDDINGS_MODEL: str = "sentence-transformers/gtr-t5-base"
    USE_CUDA: bool = True

    # ---------------------------------------------------------
    # CONFIGURATION
    # ---------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # This tells Pydantic: "If the .env has extra variables I don't know, just ignore them."
        extra="ignore" 
    )

settings = Settings()