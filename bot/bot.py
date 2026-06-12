from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import uuid
import threading
import os
import time

# ===== ИМПОРТЫ ДЛЯ VK =====
try:
    import vk_api
    from vk_api.longpoll import VkLongPoll, VkEventType
    VK_AVAILABLE = True
except ImportError:
    VK_AVAILABLE = False
    print("⚠️ vk-api не установлен. Установи: pip install vk-api")

app = Flask(__name__)
CORS(app)

# ===== КОНФИГУРАЦИЯ =====
EXTERNAL_API_URL = os.environ.get('EXTERNAL_API_URL', 'http://localhost:8000/api/v1')
CLINIC_PHONE = os.environ.get('CLINIC_PHONE', '+7 (982) 717-82-67')
VK_TOKEN = os.environ.get('VK_ACCESS_TOKEN', '')
VK_CONFIRMATION_CODE = os.environ.get('VK_CONFIRMATION_CODE', 'ваш_код_подтверждения')

# Инициализация VK
vk = None
longpoll = None

if VK_TOKEN and VK_AVAILABLE:
    try:
        vk_session = vk_api.VkApi(token=VK_TOKEN)
        vk = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)
        print("✅ VK бот инициализирован")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации VK: {e}")
else:
    print("⚠️ VK_TOKEN не задан, бот не сможет отправлять сообщения в VK")

# Хранилище сессий
sessions = {}

# ===== ФУНКЦИИ СИНХРОНИЗАЦИИ =====
def save_to_external_api(user_id, message_text, direction, source):
    try:
        response = requests.post(
            f"{EXTERNAL_API_URL}/sync/message",
            json={
                "user_id": str(user_id),
                "message_text": message_text,
                "direction": direction,
                "source": source
            },
            timeout=3
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")
        return False

def get_history_from_external_api(user_id, limit=20):
    try:
        response = requests.get(
            f"{EXTERNAL_API_URL}/sync/history/{user_id}",
            params={"limit": limit},
            timeout=3
        )
        if response.status_code == 200:
            return response.json().get("messages", [])
    except Exception as e:
        print(f"Ошибка получения истории: {e}")
    return []

# ===== ФУНКЦИИ ДЛЯ VK =====
def send_to_vk(user_id, message):
    """Отправить сообщение в VK"""
    if not vk:
        print("❌ VK не инициализирован")
        return False
    
    try:
        vk.messages.send(
            user_id=int(user_id),
            message=message[:4096],  # VK ограничение на длину сообщения
            random_id=int(time.time() * 1000)
        )
        print(f"📤 Отправлено в VK пользователю {user_id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки в VK: {e}")
        return False

# ===== ОСНОВНАЯ ЛОГИКА БОТА =====
def bot_response(msg, user_id):
    msg_lower = msg.lower().strip()
    
    print(f"🔍 [ДИАГНОСТИКА] Пользователь {user_id} написал: '{msg}'")
    
    if user_id not in sessions:
        sessions[user_id] = {'step': 'main'}
        print(f"🔍 [ДИАГНОСТИКА] Новая сессия для {user_id}, шаг = main")
    
    session = sessions[user_id]
    step = session.get('step', 'main')
    print(f"🔍 [ДИАГНОСТИКА] Текущий шаг для {user_id}: '{step}'")

    # ===== ШАГ: ПОЛЬЗОВАТЕЛЬ НАПИСАЛ "да" =====
    if step == 'waiting_for_confirm':
        print(f"🔍 [ДИАГНОСТИКА] ВОШЛИ В БЛОК waiting_for_confirm для {user_id}")
        sessions[user_id]['step'] = 'main'
        print(f"🔍 [ДИАГНОСТИКА] Сбрасываем шаг для {user_id} на 'main'")
        answer = f"📞 Запись на приём!\n\nПозвоните нам по телефону:\n{CLINIC_PHONE}\n\nНаш администратор запишет вас на удобное время.\n\nЗдоровья вашему питомцу! 🐾"
        print(f"🔍 [ДИАГНОСТИКА] ОТВЕТ: {answer[:50]}...")
        return answer

    # ===== ПОЛЬЗОВАТЕЛЬ НАПИСАЛ "ЗАПИСАТЬСЯ" =====
    if any(w in msg_lower for w in ['запись', 'записаться', 'записать', 'хочу записаться', 'запишите', 'на приём', 'на прием']):
        print(f"🔍 [ДИАГНОСТИКА] ПОЛЬЗОВАТЕЛЬ ХОЧЕТ ЗАПИСАТЬСЯ. Устанавливаем шаг 'waiting_for_confirm' для {user_id}")
        sessions[user_id]['step'] = 'waiting_for_confirm'
        return "📝 Запись на приём!\n\nЯ дам вам номер телефона, по которому можно записаться. Напишите 'да' или любой символ, чтобы продолжить."

    # ===== ОСТАЛЬНЫЕ ОТВЕТЫ =====
    if any(w in msg_lower for w in ['прием', 'приём']) and 'запис' not in msg_lower:
        return "🩺 Стоимость приёма:\n• Первичный приём — от 800 ₽\n• Повторный приём — от 600 ₽\n• Консультация по уходу и кормлению — от 500 ₽"
    
    if 'терапи' in msg_lower:
        return "🩺 Терапия:\n• Первичный приём — от 800 ₽\n• Повторный — от 600 ₽\n• Диспансеризация — от 4 200 ₽"
    
    if any(w in msg_lower for w in ['анализ', 'крови', 'мочи']):
        return "🧪 Анализы:\n• Общий анализ крови — от 500 ₽\n• Биохимия крови — от 800 ₽\n• Общий анализ мочи — от 650 ₽"
    
    if 'узи' in msg_lower:
        return "🩺 УЗИ:\n• УЗИ брюшной полости — от 1 100 ₽\n• УЗИ крипторха — от 500 ₽"
    
    if any(w in msg_lower for w in ['вакцин', 'прививк']):
        return "💉 Вакцинация:\n• Кошки — от 1 500 ₽\n• Собаки — от 1 800 ₽\n• Ежедневно с 10:00 до 14:00"
    
    if any(w in msg_lower for w in ['хирург', 'операц', 'стерил', 'кастр']):
        return "🏥 Хирургия:\n• Стерилизация кошек — от 3 000 ₽\n• Стерилизация собак — от 4 500 ₽\n• Кастрация — от 2 500 ₽"
    
    if 'стационар' in msg_lower:
        return "🏥 Стационар:\n• 1 час — от 80 ₽\n• 12 часов — от 800 ₽"
    
    if any(w in msg_lower for w in ['вызов', 'на дом']):
        return "🏠 Вызов врача на дом:\n• Северная часть — от 500 ₽\n• Южная часть — от 750 ₽\n• Красная горка — от 650 ₽\n• Полдневая — от 1 650 ₽"
    
    if 'катетер' in msg_lower:
        return "💉 Установка внутривенного катетера — от 300 ₽"
    
    if any(w in msg_lower for w in ['капельниц', 'инфузи']):
        return "💧 Внутривенные инфузии:\n• Первый час — от 330 ₽\n• Последующие часы — от 200 ₽"
    
    if any(w in msg_lower for w in ['укол', 'инъекц']):
        return "💉 Внутримышечная/подкожная инъекция — от 35 ₽"
    
    if 'клещ' in msg_lower:
        return "🕷️ Удаление клеща:\n• До 5 шт — от 200 ₽\n• От 5 до 20 шт — от 500 ₽"
    
    if 'чипир' in msg_lower:
        return "🔖 Чипирование — от 1 500 ₽"
    
    if 'клизм' in msg_lower:
        return "💩 Клизма:\n• Кошки — от 660 ₽\n• Средние собаки — от 880 ₽\n• Крупные собаки — от 1 650 ₽"
    
    if any(w in msg_lower for w in ['оператор', 'человек', 'админ']):
        return f"👩‍⚕️ Связь с администратором\n\nПозвоните нам по телефону: {CLINIC_PHONE}"
    
    if 'не ест' in msg_lower:
        return "🍽 Если животное не ест больше суток — срочно к врачу. Напишите 'записаться' для записи."

    # ===== ПРИВЕТСТВИЕ =====
    return ("🐾 Здравствуйте! Вас приветствует клиника Добрый Доктор в Полевском.\n\n"
            "Опишите, пожалуйста, проблему, и мы с удовольствием вам поможем.\n\n"
            "Наши услуги:\n"
            "• Терапия\n"
            "• Хирургия\n"
            "• Плановая вакцинация\n"
            "• УЗИ\n\n"
            "Я могу записать вас на приём, рассказать о услугах или связать с администратором.\n\n"
            "Просто напишите свой вопрос!")


# ===== ФУНКЦИЯ ДЛЯ LONG POLL (обработка сообщений из VK) =====
def start_longpoll():
    """Запуск Long Poll в отдельном потоке для получения сообщений из VK"""
    if not vk or not longpoll:
        print("⚠️ VK Long Poll не запущен: VK не инициализирован")
        return
    
    print("🔄 Запуск Long Poll для получения сообщений из VK...")
    try:
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_id = str(event.user_id)
                user_msg = event.text
                
                print(f"📨 Long Poll: получено из VK от {user_id}: {user_msg}")
                
                # Сохраняем сообщение в бэкенд
                save_to_external_api(user_id, user_msg, "incoming", "vk")
                
                # Генерируем ответ
                answer = bot_response(user_msg, user_id)
                
                # Отправляем ответ в VK
                send_to_vk(user_id, answer)
                
                # Сохраняем ответ в бэкенд
                save_to_external_api(user_id, answer, "outgoing", "vk")
    except Exception as e:
        print(f"❌ Ошибка в Long Poll: {e}")


# ===== API ДЛЯ ФРОНТЕНДА =====
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get('message', '')
        user_id = data.get('user_id', str(uuid.uuid4()))
        
        save_to_external_api(user_id, user_msg, "incoming", "web")
        answer = bot_response(user_msg, user_id)
        save_to_external_api(user_id, answer, "outgoing", "web")
        
        return jsonify({'reply': answer, 'status': 'ok', 'user_id': user_id})
    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({'error': str(e)}), 500


# ===== API ДЛЯ ВНЕШНЕГО БЭКЕНДА =====
@app.route('/api/process-message', methods=['POST'])
def process_message():
    try:
        data = request.get_json()
        user_msg = data.get('message_text', '')
        user_id = data.get('user_id', 'unknown')
        print(f"📨 Запрос от внешнего бэкенда от {user_id}: {user_msg}")
        answer = bot_response(user_msg, user_id)
        return jsonify({'response': answer, 'action': 'reply', 'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== VK WEBHOOK (Callback API) =====
@app.route('/vk/callback', methods=['GET', 'POST'])
def vk_callback():
    """
    VK отправляет сюда запросы для подтверждения и новые сообщения
    Callback API альтернатива Long Poll
    """
    if request.method == 'GET':
        # VK отправляет код подтверждения при настройке
        return VK_CONFIRMATION_CODE
    
    data = request.get_json()
    
    if data.get('type') == 'confirmation':
        return VK_CONFIRMATION_CODE
    
    if data.get('type') == 'message_new':
        message = data['object']['message']
        user_id = str(message['from_id'])
        user_msg = message.get('text', '')
        
        print(f"📨 Callback: получено из VK от {user_id}: {user_msg}")
        
        # Сохраняем сообщение в бэкенд
        save_to_external_api(user_id, user_msg, "incoming", "vk")
        
        # Генерируем ответ
        answer = bot_response(user_msg, user_id)
        
        # Отправляем ответ в VK
        send_to_vk(user_id, answer)
        
        # Сохраняем ответ в бэкенд
        save_to_external_api(user_id, answer, "outgoing", "vk")
    
    return "ok"


# ===== ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ =====
@app.route('/api/sync_history', methods=['GET'])
def sync_history():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    history = get_history_from_external_api(user_id)
    return jsonify({'history': history})

@app.route('/api/sessions/<user_id>', methods=['GET'])
def get_session(user_id):
    step = sessions.get(user_id, {}).get('step', 'main')
    return jsonify({'user_id': user_id, 'step': step})

@app.route('/api/sessions/<user_id>', methods=['DELETE'])
def clear_session(user_id):
    if user_id in sessions:
        del sessions[user_id]
    return jsonify({'status': 'ok'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'external_api': EXTERNAL_API_URL,
        'sessions': len(sessions),
        'vk_configured': bool(vk),
        'clinic_phone': CLINIC_PHONE
    })


# ===== ЗАПУСК =====
if __name__ == '__main__':
    print("=" * 50)
    print("🐕 Бот 'Добрый Доктор'")
    print(f"📍 Локальный адрес: http://localhost:5000")
    print(f"🔗 Бэкенд: {EXTERNAL_API_URL}")
    print(f"📞 Телефон клиники: {CLINIC_PHONE}")
    print(f"🤖 VK бот: {'✅ Активен' if vk else '❌ Не настроен'}")
    print("=" * 50)
    
    # Запускаем Long Poll в отдельном потоке (если VK настроен)
    if vk and longpoll:
        longpoll_thread = threading.Thread(target=start_longpoll, daemon=True)
        longpoll_thread.start()
        print("🔄 Long Poll поток запущен")
    else:
        print("⚠️ Long Poll не запущен (VK не настроен)")
    
    # Запускаем Flask сервер
    app.run(host='0.0.0.0', port=5000, debug=False)