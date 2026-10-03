from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Personal Shopper"
    APP_VERSION: str = "1.0.0"

    # Backend
    HOST: str = "0.0.0.0"
    PORT: int = "8000"

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DBNAME: str = "personal_shopper"

    # ChromaDB
    CHROMA_DB_DIR: str = "./vector_store"
    CHROMA_COLLECTION: str = "products"

    # AI Config (reads strictly from .env)
    GOOGLE_API_KEY: str = "" 
    
    # Embeddings model 
    EMBEDDINGS_MODEL: str = "sentence-transformers/gtr-t5-base"
    USE_CUDA: bool = True

    # ---------------------------------------------------------
    # CONFIGURATION
    # ---------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" 
    )

settings = Settings()