#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    print("1. Проверка здоровья...")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"   ✅ {resp.status_code} - {resp.json()['status']}")

def test_send_message():
    print("\n2. Отправка сообщения с сайта...")
    resp = requests.post(f"{BASE_URL}/api/v1/messages",
                        json={"user_id": "test_user_123", "message_text": "Привет, бот!"})
    print(f"   ✅ {resp.status_code} - {resp.json()['status']}, id={resp.json()['message_id']}")

def test_get_history():
    print("\n3. Получение истории...")
    resp = requests.get(f"{BASE_URL}/api/v1/messages/history/test_user_123?limit=5")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   ✅ {resp.status_code} - {len(data['messages'])} сообщений")

def test_sync_from_vk():
    print("\n4. Синхронизация сообщения от VK бота...")
    resp = requests.post(f"{BASE_URL}/api/v1/sync/message",
                        json={
                            "user_id": "123456789",
                            "message_text": "Здравствуйте!",
                            "direction": "incoming",
                            "source": "vk"
                        })
    print(f"   ✅ {resp.status_code} - {resp.json()['status']}")

def test_get_sync_history():
    print("\n5. Получение истории для синхронизации...")
    resp = requests.get(f"{BASE_URL}/api/v1/sync/history/123456789")
    if resp.status_code == 200:
        print(f"   ✅ {resp.status_code} - {len(resp.json()['messages'])} сообщений для синхронизации")

def test_active_users():
    print("\n6. Получение активных пользователей...")
    resp = requests.get(f"{BASE_URL}/api/v1/sync/active-users")
    if resp.status_code == 200:
        print(f"   ✅ {resp.status_code} - {len(resp.json()['users'])} активных пользователей")

def main():
    print("=" * 50)
    print("🔍 ПРОВЕРКА БЭКЕНДА")
    print("=" * 50)
    
    test_health()
    test_send_message()
    time.sleep(0.5)
    test_get_history()
    test_sync_from_vk()
    test_get_sync_history()
    test_active_users()
    
    print("\n" + "=" * 50)
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 50)
    print("\n📚 Swagger UI: http://localhost:8000/docs")
    print("💾 Проверить БД: psql -U vet_user -d vet_clinic -h localhost")

if __name__ == "__main__":
    main()