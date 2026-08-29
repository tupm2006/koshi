import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Koshi PM API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Database configuration (SQLite default, can be Postgres)
    # SQLite by default so a checkout runs with no database server. Production
    # uses MySQL:
    #   mysql+pymysql://koshi:<password>@koshi-db:3306/koshi?charset=utf8mb4
    # The charset matters — MySQL's "utf8" is three bytes and cannot store an
    # emoji or some CJK characters, which would truncate a task title silently.
    DATABASE_URL: str = "sqlite:///./data/koshi.db"

    # ---- Attachments --------------------------------------------------------
    # Where uploaded evidence is written. Inside the data volume, so it survives
    # a rebuild and is excluded from the image by .dockerignore.
    UPLOAD_DIR: str = "./data/uploads"
    # Per-file ceiling. Enforced while streaming, not after — reading an
    # unbounded body into memory to measure it is the denial of service.
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024
    
    # Deployment environment. Anything other than "development" is treated as
    # production for the purposes of the startup safety checks in main.py.
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # JWT & Auth
    # This default is a DEVELOPMENT CONVENIENCE ONLY. main.py refuses to start
    # outside development if it has not been overridden.
    DEV_JWT_SECRET: str = "koshi-insecure-development-secret-do-not-deploy"
    JWT_SECRET: str = os.getenv("JWT_SECRET", "") or DEV_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # AI Service Configuration
    AI_API_URL: str = "https://api.openai.com/v1/chat/completions"
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL_NAME: str = "gpt-4o-mini"
    
    # Accept Google ID tokens whose signature could not be verified, by decoding
    # the JWT payload directly. Required by the offline test-suite; catastrophic
    # in production, where it lets anyone forge a session for any email address.
    ALLOW_UNVERIFIED_GOOGLE_TOKENS: bool = os.getenv("ALLOW_UNVERIFIED_GOOGLE_TOKENS", "false").lower() in ("1", "true", "yes")

    # Comma-separated allowed CORS origins. "*" is rejected outside development.
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    # Seed demo users/project on an empty database. Development only.
    SEED_DEMO_DATA: bool = os.getenv("SEED_DEMO_DATA", "true").lower() in ("1", "true", "yes")

    # Local Ollama Fallback Configuration
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
