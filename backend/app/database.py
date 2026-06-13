from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.config import settings
import asyncpg
from urllib.parse import urlparse

Base = declarative_base()

engine = None
AsyncSessionLocal = None

async def create_database_if_not_exists():
    """Создает базу данных если она не существует"""
    parsed = urlparse(settings.database_url)
    db_name = parsed.path[1:]
    host = parsed.hostname
    port = parsed.port or 5432
    user = parsed.username
    password = parsed.password
    
    # URL для подключения к системной БД (без указания конкретной БД)
    system_conn_str = f"postgresql://{user}:{password}@{host}:{port}/postgres"
    
    try:
        conn = await asyncpg.connect(system_conn_str)
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        
        if not result:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"✅ База данных '{db_name}' успешно создана!")
        else:
            print(f"📦 База данных '{db_name}' уже существует")
        
        await conn.close()
        
    except Exception as e:
        print(f"⚠️ Ошибка при создании БД: {e}")
        raise

async def init_engine():
    """Инициализация engine после создания БД"""
    global engine
    if engine is None:
        # ВАЖНО: URL должен заканчиваться на ?async_fallback=true
        # или использовать правильный asyncpg драйвер
        db_url = settings.database_url
        if 'postgresql://' in db_url and '+asyncpg' not in db_url:
            # Заменяем postgresql:// на postgresql+asyncpg://
            db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
        
        engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            pool_size=10,
            max_overflow=20
        )
    return engine

async def create_tables():
    """Создание всех таблиц"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Все таблицы созданы")

async def init_db():
    """Полная инициализация базы данных"""
    print("=" * 60)
    print("🚀 НАЧАЛО ИНИЦИАЛИЗАЦИИ БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    print("\n📁 Шаг 1: Проверка/создание базы данных...")
    await create_database_if_not_exists()
    
    print("\n🔌 Шаг 2: Подключение к базе данных...")
    await init_engine()
    
    print("\n📊 Шаг 3: Создание таблиц...")
    await create_tables()
    
    print("\n" + "=" * 60)
    print("✅ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ЗАВЕРШЕНА")
    print("=" * 60)

async def get_db():
    """Dependency для получения сессии БД"""
    global AsyncSessionLocal
    
    if AsyncSessionLocal is None:
        if engine is None:
            await init_engine()
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def close_db():
    """Закрыть соединение с БД"""
    global engine
    if engine:
        await engine.dispose()
        print("\n🔌 Соединение с базой данных закрыто")