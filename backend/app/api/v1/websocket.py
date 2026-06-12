from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_manager import manager

router = APIRouter(prefix="/ws", tags=["WebSocket"])

@router.websocket("/chat/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """
    WebSocket соединение для реалтайм чата
    """
    await manager.connect(user_id, websocket)
    
    try:
        while True:
            # Ждем сообщения от клиента
            data = await websocket.receive_text()
            print(f"Получено от клиента {user_id}: {data}")
            
            # Здесь можно обработать сообщение, но основная логика через HTTP
            # Отправляем подтверждение
            await websocket.send_json({"type": "pong", "data": "received"})
            
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)