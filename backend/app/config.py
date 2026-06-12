from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    database_url: str
    vk_bot_url: str = "http://bot:5000"  # Внутри Docker сети
    secret_key: str
    environment: str = "production"
    cors_origins: List[str] = [
        "https://vet-clinic-frontend.vercel.app",  # Домен фронтенда
        "https://your-bot.onrender.com"           # Домен бота
    ]
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Игнорировать лишние переменные

settings = Settings()