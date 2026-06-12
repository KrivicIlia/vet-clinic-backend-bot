from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User, Message
from app.schemas import SyncMessageRequest, SyncMessageResponse, MessageDirection, MessageSource
from app.websocket_manager import manager

router = APIRouter(prefix="/sync", tags=["Sync"])

@router.post("/message", response_model=SyncMessageResponse)
async def sync_message(
    request: SyncMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Синхронизация сообщения от VK бота
    VK бот отправляет сюда сообщения для сохранения в БД
    """
    # 1. Находим или создаем пользователя по vk_id
    result = await db.execute(
        select(User).where(User.vk_id == request.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            vk_id=request.user_id,
            username=f"vk_user_{request.user_id[:8]}",
            role="user"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # 2. Сохраняем сообщение
    message = Message(
        user_id=user.id,
        message_text=request.message_text,
        direction=request.direction,
        source=request.source,
        is_synced_to_vk=True  # От VK бота уже синхронизировано
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    
    # 3. Если пользователь онлайн на сайте, отправляем через WebSocket
    if user.site_id:
        await manager.send_message_update(user.site_id, {
            "id": message.id,
            "text": message.message_text,
            "direction": message.direction.value,
            "source": message.source.value,
            "timestamp": message.created_at.isoformat()
        })
    
    return SyncMessageResponse(
        status="synced",
        message_id=message.id
    )

@router.get("/history/{vk_id}")
async def get_sync_history(
    vk_id: str,
    days: int = 7,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить историю сообщений для синхронизации с VK
    (используется VK ботом при запуске)
    """
    from datetime import datetime, timedelta
    
    # Находим пользователя
    result = await db.execute(
        select(User).where(User.vk_id == vk_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return {"user_id": vk_id, "messages": []}
    
    # Получаем сообщения с сайта за последние days дней
    since_date = datetime.now() - timedelta(days=days)
    
    result = await db.execute(
        select(Message)
        .where(Message.user_id == user.id)
        .where(Message.source == MessageSource.site)
        .where(Message.created_at >= since_date)
        .where(Message.is_synced_to_vk == False)
        .order_by(Message.created_at)
        .limit(limit)
    )
    messages = result.scalars().all()
    
    # Отмечаем как синхронизированные
    for msg in messages:
        msg.is_synced_to_vk = True
    await db.commit()
    
    return {
        "user_id": vk_id,
        "messages": [
            {
                "text": msg.message_text,
                "direction": msg.direction.value,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }

@router.get("/active-users")
async def get_active_users(
    days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список активных пользователей для синхронизации
    """
    from datetime import datetime, timedelta
    since_date = datetime.now() - timedelta(days=days)
    
    result = await db.execute(
        select(User)
        .where(User.vk_id.isnot(None))
        .where(User.updated_at >= since_date)
    )
    users = result.scalars().all()
    
    return {
        "users": [
            {
                "vk_id": user.vk_id,
                "site_id": user.site_id,
                "username": user.username
            }
            for user in users
        ]
    }