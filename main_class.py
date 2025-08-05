import asyncio
import logging
import requests
import random

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config_class import TOKEN, THE_CAT_API_KEY, NASA_API_KEY
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("aiogram")

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Кэширование данных пород
_breed_cache = None


def get_random_apod():
   end_date = datetime.now()
   start_date = end_date - timedelta(days=365)
   random_date = start_date + (end_date - start_date) * random.random()
   date_str = random_date.strftime("%Y-%m-%d")
   url = f'https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}&date={date_str}'
   response = requests.get(url)
   return response.json()

@dp.message(Command("random_apod"))
async def random_apod(message: Message):
   apod = get_random_apod()
   photo_url = apod['url']
   title = apod['title']

   await message.answer_photo(photo=photo_url, caption=f"{title}")


def get_cat_breeds():
    global _breed_cache
    if _breed_cache is None:
        url = "https://api.thecatapi.com/v1/breeds"
        headers = {"x-api-key": THE_CAT_API_KEY}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            _breed_cache = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе пород: {e}")
            return []
    return _breed_cache

def get_cat_image_by_breed(breed_id):
    url = f"https://api.thecatapi.com/v1/images/search?breed_ids={breed_id}"
    headers = {"x-api-key": THE_CAT_API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data[0]['url'] if data else None
    except (requests.exceptions.RequestException, IndexError) as e:
        logger.error(f"Ошибка при запросе изображения: {e}")
        return None

def get_breed_info(breed_name):
    breeds = get_cat_breeds()
    for breed in breeds:
        if breed['name'].lower() == breed_name.lower():
            return breed
    return None

# Хэндлер для команды /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! Введи название породы кошки, чтобы узнать информацию.")

# Хэндлер для обработки текстовых сообщений с названиями пород
@dp.message(F.text)
async def send_cat_info(message: Message):
    breed_name = message.text.strip()
    breed_info = get_breed_info(breed_name)
    if breed_info:
        cat_image_url = get_cat_image_by_breed(breed_info['id'])
        if cat_image_url:
            info = (
                f"Порода - {breed_info['name']}\n"
                f"Описание - {breed_info['description']}\n"
                f"Продолжительность жизни - {breed_info['life_span']} лет"
            )
            await message.answer_photo(photo=cat_image_url, caption=info)
        else:
            await message.answer("Не удалось загрузить изображение породы.")
    else:
        await message.answer("Порода не найдена. Попробуйте еще раз.")

# Главная функция с обработкой ошибок
async def main():
    try:
        logger.info("Бот запущен!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")

if __name__ == "__main__":
    asyncio.run(main())