from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from enum import Enum

class MessageDirection(str, Enum):
    incoming = "incoming"
    outgoing = "outgoing"

class MessageSource(str, Enum):
    vk = "vk"
    site = "site"
    bot = "bot"

class AppointmentStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"

# === Схемы для пользователей ===
class UserBase(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    pet_name: Optional[str] = None
    pet_type: Optional[str] = None

class UserCreate(UserBase):
    vk_id: Optional[str] = None
    site_id: Optional[str] = None

class UserResponse(UserBase):
    id: int
    vk_id: Optional[str]
    site_id: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# === Схемы для сообщений ===
class MessageCreate(BaseModel):
    user_id: int
    message_text: str
    direction: MessageDirection
    source: MessageSource
    vk_message_id: Optional[int] = None

class MessageResponse(BaseModel):
    id: int
    user_id: int
    message_text: str
    direction: str
    source: str
    created_at: datetime
    is_synced_to_vk: bool = False
    
    class Config:
        from_attributes = True

# === Схемы для API сайта ===
class SiteMessageRequest(BaseModel):
    user_id: str  # site_id или vk_id
    message_text: str

class SiteMessageResponse(BaseModel):
    status: str
    message_id: int
    temp_id: Optional[str] = None

# === Схемы для синхронизации с VK ботом ===
class SyncMessageRequest(BaseModel):
    user_id: str  # vk_id
    message_text: str
    direction: MessageDirection
    source: MessageSource
    reply_to: Optional[str] = None

class SyncMessageResponse(BaseModel):
    status: str
    message_id: int

# === Схемы для истории ===
class HistoryRequest(BaseModel):
    user_id: str
    days: int = 7
    limit: int = 50

class HistoryResponse(BaseModel):
    user_id: str
    messages: list

# === Общие ответы ===
class HealthResponse(BaseModel):
    status: str
    database: str
    environment: str