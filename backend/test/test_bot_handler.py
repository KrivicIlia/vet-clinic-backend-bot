import pytest
from app.handlers.bot_handler import BotResponseHandler

@pytest.mark.asyncio
async def test_generate_response_for_appointment():
    response = await BotResponseHandler.generate_response("хочу записаться")
    assert "запись" in response.lower()
    assert "прием" in response.lower()

@pytest.mark.asyncio
async def test_generate_response_for_address():
    response = await BotResponseHandler.generate_response("где вы находитесь")
    assert "адрес" in response.lower()

@pytest.mark.asyncio
async def test_generate_response_for_prices():
    response = await BotResponseHandler.generate_response("сколько стоит")
    assert "стоимость" in response.lower() or "руб" in response.lower()

@pytest.mark.asyncio
async def test_generate_response_default():
    response = await BotResponseHandler.generate_response("случайный текст")
    assert "ветклиники" in response
    assert "написать" in response

@pytest.mark.asyncio
async def test_escalate_to_human():
    result = await BotResponseHandler.should_escalate_to_human("у меня жалоба")
    assert result is True
    
    result = await BotResponseHandler.should_escalate_to_human("обычный вопрос")
    assert result is False