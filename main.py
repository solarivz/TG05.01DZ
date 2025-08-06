import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest
from config import TOKEN, WS_URL, ADMIN_CHAT_ID
import websockets

# Настройка логирования для отслеживания событий бота
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("aiogram")  # Логгер для записи действий бота

# Инициализация бота с токеном из конфига
bot = Bot(token=TOKEN)  # Создаем экземпляр бота для взаимодействия с Telegram API
dp = Dispatcher()  # Диспетчер для обработки входящих сообщений

# Обновленный список валидных торговых пар (основан на популярных парах EXMO)
VALID_TRADING_PAIRS = [
    "ETH_USDT", "BTC_USDT", "LTC_USD", "XRP_USDT", "ADA_USDT",
    "DOGE_USDT", "BNB_USDT", "SOL_USDT"  # Убраны сомнительные пары, оставлены проверенные
]

# Глобальные словари для хранения данных
trade_data = {}  # Данные о сделках
# Флаг для отслеживания состояния подключения
is_connected = False


# Асинхронная функция для обработки WebSocket-соединения с диагностикой
async def websocket_handler():
    global trade_data, is_connected
    while True:
        try:
            uri = WS_URL
            async with websockets.connect(uri) as websocket:
                is_connected = True
                logger.info("WebSocket соединение успешно установлено")
                try:
                    await bot.send_message(chat_id=ADMIN_CHAT_ID, text="✅ WebSocket подключен к EXMO!")
                except TelegramBadRequest as e:
                    logger.error(f"Не удалось отправить уведомление: {e}")

                # Сообщение для подписки на данные о торгах
                subscribe_msg = {
                    "id": 1,
                    "method": "subscribe",
                    "topics": [f"spot/trades:{pair}" for pair in VALID_TRADING_PAIRS]
                }
                await websocket.send(json.dumps(subscribe_msg))
                logger.info(f"Отправлено сообщение подписки: {json.dumps(subscribe_msg)}")

                while True:
                    message = await websocket.recv()
                    logger.debug(f"Получено необработанное сообщение: {message}")
                    try:
                        data = json.loads(message)
                        logger.debug(f"Распарсено сообщение: {data}")
                        if "data" in data and "trades" in data["data"]:
                            for trade in data["data"]["trades"]:
                                pair = trade.get("pair", "").replace("-", "_")
                                if pair in VALID_TRADING_PAIRS:
                                    if pair not in trade_data:
                                        trade_data[pair] = []
                                    trade_data[pair].append(trade)
                                    trade_data[pair] = trade_data[pair][-10:]  # Ограничиваем до 10 сделок
                                    logger.info(f"Обновлены данные по паре {pair}: {trade}")
                        elif "event" in data and data["event"] == "error":
                            logger.warning(f"Ошибка от сервера: {data}")
                            # Продолжаем обработку других пар, игнорируя ошибочные
                        elif "code" in data and data["code"] == 1:
                            logger.info("Подписка на данные успешно подтверждена")
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка декодирования JSON: {e}, сообщение: {message}")

        except websockets.ConnectionClosed as e:
            is_connected = False
            logger.error(f"WebSocket соединение разорвано: {e}")
            try:
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ WebSocket разорвано: {e}")
            except TelegramBadRequest as e:
                logger.error(f"Не удалось отправить уведомление: {e}")
            await asyncio.sleep(5)
        except websockets.WebSocketException as e:
            is_connected = False
            logger.error(f"Ошибка WebSocket: {e}")
            try:
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ Ошибка WebSocket: {e}")
            except TelegramBadRequest as e:
                logger.error(f"Не удалось отправить уведомление: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            is_connected = False
            logger.error(f"Неизвестная ошибка WebSocket: {e}")
            try:
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ Ошибка: {e}")
            except TelegramBadRequest as e:
                logger.error(f"Не удалось отправить уведомление: {e}")
            await asyncio.sleep(5)


# Хэндлер для получения chat_id
@dp.message(Command("getid"))
async def get_chat_id(message: Message):
    await message.answer(f"Ваш chat_id: {message.chat.id}")


# Хэндлер для обработки команды /Trades
@dp.message(Command("Trades"))
async def get_trades_handler(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Пожалуйста, укажите торговую пару, например: /Trades ETH/USDT")
        return

    trading_pair = parts[1].strip().upper().replace("/", "_")

    if trading_pair not in VALID_TRADING_PAIRS:
        await message.answer(f"Пара {trading_pair} не поддерживается. Доступные пары: {', '.join(VALID_TRADING_PAIRS)}")
        return

    if not is_connected:
        await message.answer("⚠️ WebSocket не подключен. Данные недоступны.")
        return

    trades = trade_data.get(trading_pair, [])
    if not trades:
        await message.answer(
            f"Данные о сделках по паре {trading_pair.replace('_', '/')} еще не получены. Подождите немного или проверьте логи.")
        return

    # Формируем ответ с информацией о сделках
    response_text = f"Последние сделки по паре {trading_pair.replace('_', '/')}:\n\n"
    for trade in trades[-3:]:  # Берем последние 3 сделки
        response_text += (
            f"⏰ Время: {trade.get('date', 'N/A')}\n"
            f"💰 Цена: {trade.get('price', 'N/A')} {trading_pair.split('_')[1]}\n"
            f"📊 Объем: {trade.get('quantity', 'N/A')} {trading_pair.split('_')[0]}\n"
            f"🔄 Тип: {trade.get('type', 'N/A')}\n"
            f"--------------------\n"
        )

    await message.answer(response_text)


# Главная асинхронная функция для запуска бота и WebSocket
async def main():
    try:
        logger.info("Бот и WebSocket запущены!")
        asyncio.create_task(websocket_handler())
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")


if __name__ == "__main__":
    asyncio.run(main())