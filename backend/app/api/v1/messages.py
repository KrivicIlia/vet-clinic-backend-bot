from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User, Message
from app.schemas import SiteMessageRequest, SiteMessageResponse, MessageDirection, MessageSource
from app.websocket_manager import manager  # Добавь этот импорт
import httpx
from app.config import settings
import uuid
from datetime import datetime

router = APIRouter(prefix="/messages", tags=["Messages"])

async def request_bot_response(user_id: int, vk_id: str, message_text: str, temp_id: str, db: AsyncSession):
    """
    Фоновая задача: отправить сообщение VK боту и получить ответ
    """
    async with httpx.AsyncClient() as client:
        try:
            # Отправляем запрос к боту
            response = await client.post(
                f"{settings.vk_bot_url}/api/process-message",
                json={
                    "user_id": vk_id if vk_id else str(user_id),
                    "message_text": message_text,
                    "source": "site",
                    "temp_id": temp_id
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                bot_data = response.json()
                bot_response_text = bot_data.get("response", "Извините, не могу ответить")
                print(f"✅ Бот ответил: {bot_response_text[:50]}...")
                
                # ============================================
                # ВАЖНО: Сохраняем ответ бота в БД
                # ============================================
                bot_message = Message(
                    user_id=user_id,
                    message_text=bot_response_text,
                    direction=MessageDirection.outgoing,
                    source=MessageSource.bot,
                    is_synced_to_vk=False
                )
                db.add(bot_message)
                await db.commit()
                await db.refresh(bot_message)
                
                # ============================================
                # ВАЖНО: Отправляем ответ через WebSocket на фронтенд
                # ============================================
                # Находим пользователя по user_id
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if user and user.site_id:
                    # Отправляем сообщение через WebSocket менеджер
                    await manager.send_to_user(user.site_id, {
                        "type": "message",
                        "data": {
                            "id": bot_message.id,
                            "text": bot_response_text,
                            "direction": "outgoing",
                            "source": "bot",
                            "timestamp": bot_message.created_at.isoformat()
                        }
                    })
                    print(f"📤 WebSocket отправлен пользователю {user.site_id}")
                else:
                    print(f"⚠️ Пользователь {user_id} не имеет site_id для WebSocket")
                    
            else:
                print(f"❌ Ошибка при запросе к боту: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Ошибка при вызове VK бота: {e}")

# ============================================
# ОСНОВНОЙ ЭНДПОИНТ ДЛЯ ОТПРАВКИ СООБЩЕНИЙ
# ============================================

@router.post("/", response_model=SiteMessageResponse)
async def send_message(
    request: SiteMessageRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Отправить сообщение от пользователя с сайта
    """
    # 1. Находим или создаем пользователя
    result = await db.execute(
        select(User).where(User.site_id == request.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            site_id=request.user_id,
            username=f"user_{request.user_id[:8]}",
            role="user"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"✅ Создан новый пользователь: {user.site_id}")
    
    # 2. Сохраняем сообщение пользователя
    user_message = Message(
        user_id=user.id,
        message_text=request.message_text,
        direction=MessageDirection.incoming,
        source=MessageSource.site,
        is_synced_to_vk=False
    )
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)
    print(f"📝 Сохранено сообщение пользователя: {user_message.id}")
    
    # 3. Отправляем ответ пользователю (временный статус)
    temp_id = str(uuid.uuid4())[:8]
    
    # 4. В фоне отправляем запрос к VK боту
    background_tasks.add_task(
        request_bot_response,
        user.id,
        user.vk_id,
        request.message_text,
        temp_id,
        db
    )
    
    return SiteMessageResponse(
        status="processing",
        message_id=user_message.id,
        temp_id=temp_id
    )


@router.get("/history/{user_id}")
async def get_message_history(
    user_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить историю сообщений пользователя
    """
    # Находим пользователя
    result = await db.execute(
        select(User).where(
            (User.site_id == user_id) | (User.vk_id == user_id)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return {"user_id": user_id, "messages": []}
    
    # Получаем сообщения
    result = await db.execute(
        select(Message)
        .where(Message.user_id == user.id)
        .order_by(Message.created_at)
        .limit(limit)
    )
    messages = result.scalars().all()
    
    return {
        "user_id": user_id,
        "messages": [
            {
                "id": m.id,
                "text": m.message_text,
                "direction": m.direction.value,
                "source": m.source.value,
                "timestamp": m.created_at.isoformat(),
                "is_synced_to_vk": m.is_synced_to_vk
            }
            for m in messages
        ]
    }