from typing import Dict, Set
from fastapi import WebSocket
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        print(f"✅ Пользователь {user_id} подключен. Всего соединений: {sum(len(v) for v in self.active_connections.values())}")
    
    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"❌ Пользователь {user_id} отключен")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Отправить сообщение конкретному пользователю"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                    print(f"📤 Отправлено WebSocket пользователю {user_id}: {message.get('type', 'unknown')}")
                except Exception as e:
                    print(f"❌ Ошибка отправки пользователю {user_id}: {e}")
        else:
            print(f"⚠️ Пользователь {user_id} не в сети (нет активных WebSocket соединений)")

manager = ConnectionManager()