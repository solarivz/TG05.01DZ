import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from config import TOKEN, KLADR_API_TOKEN, KLADR_API_URL

# Настройка логирования для отслеживания событий бота
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("aiogram")  # Логгер для записи действий бота

# Инициализация бота с токеном из конфига
bot = Bot(token=TOKEN)  # Создаем экземпляр бота для взаимодействия с Telegram API
dp = Dispatcher()  # Диспетчер для обработки входящих сообщений





# Главная функция с обработкой ошибок
async def main():
    try:
        logger.info("Бот запущен!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")

if __name__ == "__main__":
    asyncio.run(main())