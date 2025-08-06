from config_class import TOKEN
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
import datetime
from deep_translator import GoogleTranslator

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
NUMBERS_API_URL = "http://numbersapi.com/"
translator = GoogleTranslator(source='auto', target='ru')

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Определяем состояния
class Form(StatesGroup):
    waiting_for_number = State()
    waiting_for_date = State()
    waiting_for_year = State()
    waiting_for_math = State()

async def translate_to_russian(text: str) -> str:
    """Переводит текст на русский язык"""
    try:
        return translator.translate(text)
    except Exception as e:
        logger.error(f"Ошибка перевода: {e}")
        return text

async def get_number_fact(number: str, fact_type: str = "trivia") -> str:
    """Получаем факт о числе"""
    url = f"{NUMBERS_API_URL}{number}/{fact_type}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    fact = await response.text()
                    return await translate_to_russian(fact)
                return "Не удалось получить факт о числе. Попробуйте другое число."
    except Exception as e:
        logger.error(f"Ошибка при запросе к NumbersAPI: {e}")
        return "Произошла ошибка при получении данных. Попробуйте позже."

@dp.message(Command("getnumber"))
async def get_number_command(message: types.Message, state: FSMContext):
    """Обработчик команды /getnumber"""
    await message.answer("Введите число, и я расскажу вам интересный факт о нём:")
    await state.set_state(Form.waiting_for_number)

@dp.message(Form.waiting_for_number)
async def process_number(message: types.Message, state: FSMContext):
    """Обработчик ввода числа"""
    number = message.text.strip()
    if number.lstrip('-').isdigit():
        fact = await get_number_fact(number)
        await message.answer(f"🔢 Факт о числе {number}:\n\n{fact}")
    else:
        await message.answer("Пожалуйста, введите корректное целое число.")
    await state.clear()

@dp.message(Command("getdate"))
async def get_date_command(message: types.Message, state: FSMContext):
    """Обработчик команды /getdate"""
    await message.answer("Введите дату в формате ДД.ММ (например, 29.02), и я расскажу интересный факт об этом дне:")
    await state.set_state(Form.waiting_for_date)

@dp.message(Form.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext):
    """Обработчик ввода даты"""
    date_input = message.text.strip()
    try:
        day, month = map(int, date_input.split('.'))
        test_date = datetime.date(2020, month, day)  # Проверка даты
        fact = await get_number_fact(f"{month}/{day}", "date")
        await message.answer(f"📅 Факт о дате {day:02d}.{month:02d}:\n\n{fact}")
    except ValueError:
        await message.answer("Пожалуйста, введите дату в правильном формате (ДД.ММ).")
    except Exception as e:
        logger.error(f"Ошибка обработки даты: {e}")
        await message.answer("Неверный формат даты. Попробуйте снова.")
    await state.clear()

@dp.message(Command("getyear"))
async def get_year_command(message: types.Message, state: FSMContext):
    """Обработчик команды /getyear"""
    await message.answer("Введите год (4 цифры), и я расскажу интересный факт о нём:")
    await state.set_state(Form.waiting_for_year)

@dp.message(Form.waiting_for_year)
async def process_year(message: types.Message, state: FSMContext):
    """Обработчик ввода года"""
    year = message.text.strip()
    if year.isdigit() and len(year) == 4 and 0 < int(year) <= datetime.datetime.now().year + 10:
        fact = await get_number_fact(year, "year")
        await message.answer(f"📅 Факт о {year} годе:\n\n{fact}")
    else:
        await message.answer("Пожалуйста, введите корректный год (4 цифры, не более 10 лет вперед от текущего).")
    await state.clear()

@dp.message(Command("getmath"))
async def get_math_command(message: types.Message, state: FSMContext):
    """Обработчик команды /getmath"""
    await message.answer("Введите число, и я расскажу математический факт о нём:")
    await state.set_state(Form.waiting_for_math)

@dp.message(Form.waiting_for_math)
async def process_math(message: types.Message, state: FSMContext):
    """Обработчик ввода числа для математического факта"""
    number = message.text.strip()
    if number.lstrip('-').isdigit():
        fact = await get_number_fact(number, "math")
        await message.answer(f"➕ Математический факт о {number}:\n\n{fact}")
    else:
        await message.answer("Пожалуйста, введите корректное число.")
    await state.clear()

@dp.message(Command("getrandom"))
async def get_random_command(message: types.Message):
    """Обработчик команды /getrandom"""
    fact = await get_number_fact("random")
    await message.answer(f"🎲 Случайный факт:\n\n{fact}")

@dp.message(Command("start"))
async def start_command(message: types.Message):
    """Обработчик команды /start"""
    help_text = (
        "Привет! Я бот, который рассказывает интересные факты о числах.\n\n"
        "Доступные команды:\n"
        "/getnumber - факт о числе\n"
        "/getdate - факт о дате (введите ДД.ММ)\n"
        "/getyear - факт о годе\n"
        "/getmath - математический факт\n"
        "/getrandom - случайный факт\n\n"
        "Просто выберите команду и следуйте инструкциям!"
    )
    await message.answer(help_text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())