#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных с явными SQL запросами
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.database import init_db, close_db
from app.config import settings

async def initialize():
    print("\n" + "=" * 70)
    print("🐾 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ВЕТКЛИНИКИ")
    print("=" * 70)
    
    print(f"\n📡 Подключение к PostgreSQL: {settings.database_url.split('@')[1]}")
    
    # Выполняем инициализацию с явными SQL запросами
    await init_db()
    
    print("\n" + "=" * 70)
    print("✨ БАЗА ДАННЫХ ГОТОВА К РАБОТЕ!")
    print("=" * 70)
    
    print("\n💡 Полезные команды для проверки:")
    print("   psql -U vet_user -d vet_clinic")
    print("   \\dt                    # показать таблицы")
    print("   SELECT * FROM users;    # посмотреть пользователей")
    print("   SELECT * FROM vet_clinic_info;  # информацию о клинике")

if __name__ == "__main__":
    asyncio.run(initialize())