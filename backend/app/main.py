from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db
from app.api.v1 import messages, sync, websocket

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения"""
    print("🚀 Инициализация базы данных...")
    await init_db()
    print("✅ База данных готова")
    yield
    print("👋 Завершение работы приложения")

app = FastAPI(
    title="Vet Clinic API",
    description="Бэкенд для ветклиники (синхронизация с VK ботом)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация роутеров
app.include_router(messages.router, prefix="/api/v1")
app.include_router(sync.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Vet Clinic API",
        "version": "2.0.0",
        "docs": "/docs",
        "architecture": "backend_for_vk_bot"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "environment": settings.environment,
        "database": "connected",
        "service": "backend"
    }