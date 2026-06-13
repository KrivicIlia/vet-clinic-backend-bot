from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    database_url: str
    vk_bot_url: str = "http://localhost:5000"
    secret_key: str
    environment: str = "development"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost"]
    
    def get_async_database_url(self) -> str:
        """Возвращает URL с asyncpg драйвером"""
        url = self.database_url
        if 'postgresql://' in url and '+asyncpg' not in url:
            url = url.replace('postgresql://', 'postgresql+asyncpg://')
        return url
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()