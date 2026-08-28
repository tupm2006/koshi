import os
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Koshi Project Management Engine"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = Field(default="development")
    
    # Database configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./app/data/koshi.db"
    )
    
    # JWT & Auth
    JWT_SECRET: str = Field(
        default="koshi_super_secret_jwt_key_2026_academic_spec"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    
    # CORS Origins
    ALLOWED_ORIGINS: Union[str, List[str]] = Field(
        default=[
            "https://koshi.felixsu.qzz.io",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080"
        ]
    )
    
    # AI Service Configuration
    AI_API_URL: str = "https://api.openai.com/v1/chat/completions"
    AI_API_KEY: str = Field(default="")
    AI_MODEL_NAME: str = "gpt-4o-mini"
    
    # Local Ollama Fallback Configuration
    OLLAMA_URL: str = Field(default="http://localhost:11434/v1/chat/completions")
    OLLAMA_MODEL: str = Field(default="qwen2.5:7b")

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        is_test = bool(os.getenv("PYTEST_CURRENT_TEST"))
        if env == "production" and not is_test:
            if v == "koshi_super_secret_jwt_key_2026_academic_spec" or len(v) < 32:
                raise ValueError("Production JWT_SECRET must be at least 32 characters and cannot use default key")
        return v

    @property
    def cors_origins(self) -> List[str]:
        if isinstance(self.ALLOWED_ORIGINS, list):
            return self.ALLOWED_ORIGINS
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
