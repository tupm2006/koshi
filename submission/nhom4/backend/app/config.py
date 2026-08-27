import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Koshi PM API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Database configuration (SQLite default, can be Postgres)
    DATABASE_URL: str = "sqlite:///./data/koshi.db"
    
    # JWT & Auth
    JWT_SECRET: str = "koshi_super_secret_jwt_key_2026_academic_spec"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # AI Service Configuration
    AI_API_URL: str = "https://api.openai.com/v1/chat/completions"
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL_NAME: str = "gpt-4o-mini"
    
    # Local Ollama Fallback Configuration
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
