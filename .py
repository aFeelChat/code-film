import sqlite3
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

API_TOKEN = '6908086522:AAHOGp4FoCH6NFkGG7vq4vL0c1h6kL_I40s'
storage = MemoryStorage()
# Инициализация бота и диспетчера
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

# Укажите ID канала вместо его имени, если канал приватный
CHANNEL_ID = -1002111703195  # замените на реальный ID вашего канала
CHANNEL_URL = "filmnavecherqq"
# Список ID администраторов
ADMIN_IDS = [5424938300]  # замените на нужные ID администраторов

class CodeState(StatesGroup):
    waiting_for_code = State()


# Проверка подписки
async def check_subscription(user_id):
    member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
    return member.is_chat_member()

# Состояния для FSM
class FilmForm(StatesGroup):
    name = State()
    code = State()
    description = State()
    release_date = State()
    director = State()
    year = State()
    rating = State()
    photo = State()

# Команда /start
@dp.message_handler(Command('start'))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        await admin_panel(message)
    elif await check_subscription(user_id):
        await message.answer("Добро пожаловать! Вы подписаны на канал.")
        await send_main_menu(message)
    else:
        keyboard = InlineKeyboardMarkup()
        button = InlineKeyboardButton(text="+Канал", url=f"https://t.me/{CHANNEL_URL}")  # измените на ссылку вашего канала
        keyboard.add(button)
        await message.answer("ПОДПИШИТЕСЬ НА КАНАЛ @your_channel ЧТОБЫ ВОСПОЛЬЗОВАТЬСЯ ФУНКЦИОНАЛОМ БОТА", reply_markup=keyboard)

# Главная меню
async def send_main_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    random_button = InlineKeyboardButton(text="Рандомный фильм", callback_data="random_film")
    code_button = InlineKeyboardButton(text="Код", callback_data="enter_code")
    keyboard.add(random_button, code_button)
    await message.answer("Выберите опцию:", reply_markup=keyboard)

# code
@dp.message_handler(Command('code'))
async def request_code(message: types.Message):
    user_id = message.from_user.id
    if await check_subscription(user_id):
        await message.answer("Введите код фильма...")
        await CodeState.waiting_for_code.set()
    else:
        keyboard = InlineKeyboardMarkup()
        button = InlineKeyboardButton(text="+Канал", url=f"https://t.me/{CHANNEL_URL}")
        keyboard.add(button)
        await message.answer("ПОДПИШИТЕСЬ НА КАНАЛ @your_channel ЧТОБЫ ВОСПОЛЬЗОВАТЬСЯ ФУНКЦИОНАЛОМ БОТА", reply_markup=keyboard)

async def get_film_by_code(message: types.Message):
    code = message.text
    conn = sqlite3.connect('films.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, release_date, director, year, rating, photo_id FROM films WHERE code=?", (code,))
    film = cursor.fetchone()
    if film:
        response = (f"Название: {film[0]}\nОписание: {film[1]}\nДата премьеры: {film[2]}"
                    f"\nРежиссер: {film[3]}\nГод: {film[4]}\nОценка: {film[5]}")
        if film[6]:  # Проверка наличия фото
            await message.answer_photo(film[6], caption=response)
        else:
            await message.answer(response)
    else:
        await message.answer("Фильм с таким кодом не найден.")
    conn.close()





# Обработка инлайн кнопок
@dp.callback_query_handler(lambda c: c.data == 'random_film')
async def process_random_film(callback_query: types.CallbackQuery):
    conn = sqlite3.connect('films.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM films ORDER BY RANDOM() LIMIT 1")
    film = cursor.fetchone()
    if film:
        response = (f"Название: {film[1]}\nОписание: {film[3]}\nДата премьеры: {film[4]}"
                    f"\nРежиссер: {film[5]}\nГод: {film[6]}\nОценка: {film[7]}")
        await bot.send_message(callback_query.from_user.id, response)
    conn.close()

@dp.callback_query_handler(lambda c: c.data == 'enter_code')
async def process_enter_code(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Введите код фильма...")
    await CodeState.waiting_for_code.set()


# Админская часть
async def admin_panel(message: types.Message):
    conn = sqlite3.connect('films.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM films")
    total_films = cursor.fetchone()[0]
    conn.close()
    
    keyboard = InlineKeyboardMarkup()
    add_film_button = InlineKeyboardButton(text="Добавить фильм", callback_data="add_film")
    # edit_film_button = InlineKeyboardButton(text="Редактировать фильм", callback_data="edit_film")
    search_by_code_button = InlineKeyboardButton(text="Поиск по коду", callback_data="enter_code")
    # code_to_id_button = InlineKeyboardButton(text="Код - ID", callback_data="code_to_id")
    keyboard.add(add_film_button, search_by_code_button)
    
    await message.answer(f"Админ панель:\nФильмов всего: {total_films}", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'add_film')
async def process_add_film(callback_query: types.CallbackQuery):
    await FilmForm.name.set()
    await bot.send_message(callback_query.from_user.id, "Введите имя фильма...")

@dp.message_handler(state=FilmForm.name)
async def add_film_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await FilmForm.next()
    await message.answer("Теперь введите код фильма")

@dp.message_handler(state=FilmForm.code)
async def add_film_code(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['code'] = message.text
    await FilmForm.next()
    await message.answer("Теперь введите описание фильма")

@dp.message_handler(state=FilmForm.description)
async def add_film_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await FilmForm.next()
    await message.answer("Теперь введите дату премьеры фильма (в формате ГГГГ-ММ-ДД)")

@dp.message_handler(state=FilmForm.release_date)
async def add_film_release_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['release_date'] = message.text
    await FilmForm.next()
    await message.answer("Теперь введите имя режиссера фильма")

@dp.message_handler(state=FilmForm.director)
async def add_film_director(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['director'] = message.text
    await FilmForm.next()
    await message.answer("Теперь введите год выпуска фильма")

@dp.message_handler(state=FilmForm.year)
async def add_film_year(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['year'] = message.text
    await FilmForm.next()
    await message.answer("Теперь введите оценку фильма")

@dp.message_handler(state=FilmForm.rating)
async def add_film_rating(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['rating'] = message.text
    keyboard = InlineKeyboardMarkup()
    yes_button = InlineKeyboardButton(text="Да", callback_data="add_photo_yes")
    no_button = InlineKeyboardButton(text="Нет", callback_data="add_photo_no")
    keyboard.add(yes_button, no_button)
    await FilmForm.next()
    await message.answer("Хотите добавить фото для фильма?", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data in ["add_photo_yes", "add_photo_no"], state=FilmForm.photo)
async def process_add_photo_choice(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "add_photo_yes":
        await bot.send_message(callback_query.from_user.id, "Загрузите фото для фильма.")
        dp.register_message_handler(lambda msg: save_film_with_photo(msg, state), content_types=['photo'], state=FilmForm.photo)
    else:
        async with state.proxy() as data:
            save_film_to_db(data['name'], data['code'], data['description'], data['release_date'], data['director'], data['year'], data['rating'])
        await bot.send_message(callback_query.from_user.id, "Фильм сохранен без фото.")
        await state.finish()

from aiogram import types

@dp.message_handler(Command('panel'))
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        await admin_panel(message)
    else:
        await message.answer("Неверная команда, напишите /help")

    


import os

async def save_film_with_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        photo_id = message.photo[-1].file_id
        # Сохраняем данные о фильме в базу данных
        save_film_to_db(data['name'], data['code'], data['description'], data['release_date'], data['director'], data['year'], data['rating'], photo_id)
    await message.answer("Фильм сохранен с фото.")
    await state.finish()

def save_film_to_db(name, code, description, release_date, director, year, rating, photo_id=None):
    conn = sqlite3.connect('films.db')
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO films (name, code, description, release_date, director, year, rating, photo_id) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
    (name, code, description, release_date, director, year, rating, photo_id))
    conn.commit()
    conn.close()



def save_film_to_db(name, code, description, release_date, director, year, rating, photo_id=None):
    conn = sqlite3.connect('films.db')
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO films (name, code, description, release_date, director, year, rating, photo_id) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
    (name, code, description, release_date, director, year, rating, photo_id))
    conn.commit()
    conn.close()

@dp.callback_query_handler(lambda c: c.data == 'edit_film')
async def process_edit_film(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Введите ID фильма, который хотите редактировать")
    dp.register_message_handler(get_film_id_for_edit, state=None)

async def get_film_id_for_edit(message: types.Message):
    film_id = message.text
    conn = sqlite3.connect('films.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM films WHERE id=?", (film_id,))
    film = cursor.fetchone()
    if film:
        async with dp.current_state(user=message.from_user.id).proxy() as data:
            data['film_id'] = film_id
        await FilmForm.name.set()
        await message.answer("Введите новое имя фильма или оставьте поле пустым, если не хотите менять")
    else:
        await message.answer("Фильм с таким ID не найден.")
    conn.close()


@dp.message_handler(state=FilmForm.name)
async def edit_film_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text or None
    await FilmForm.next()
    await message.answer("Введите новый код фильма или оставьте поле пустым, если не хотите менять")

@dp.message_handler(state=FilmForm.code)
async def edit_film_code(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['code'] = message.text or None
    await FilmForm.next()
    await message.answer("Введите новое описание фильма или оставьте поле пустым, если не хотите менять")

@dp.message_handler(state=FilmForm.description)
async def edit_film_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text or None
    await FilmForm.next()
    await message.answer("Введите новую дату премьеры фильма (в формате ГГГГ-ММ-ДД) или оставьте поле пустым, если не хотите менять")

@dp.message_handler(state=FilmForm.release_date)
async def edit_film_release_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['release_date'] = message.text or None
    await FilmForm.next()
    await message.answer("Введите новое имя режиссера фильма или оставьте поле пустым, если не хотите менять")

@dp.message_handler(state=FilmForm.director)
async def edit_film_director(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['director'] = message.text or None
    await FilmForm.next()
    await message.answer("Введите новый год выпуска фильма или оставьте поле пустым, если не хотите менять")

@dp.message_handler(state=FilmForm.year)
async def edit_film_year(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['year'] = message.text or None
    await FilmForm.next()
    await message.answer("Введите новую оценку фильма или оставьте поле пустым, если не хотите менять")

@dp.message_handler(state=FilmForm.rating)
async def edit_film_rating(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['rating'] = message.text or None
    keyboard = InlineKeyboardMarkup()
    yes_button = InlineKeyboardButton(text="Да", callback_data="edit_photo_yes")
    no_button = InlineKeyboardButton(text="Нет", callback_data="edit_photo_no")
    keyboard.add(yes_button, no_button)
    await FilmForm.next()
    await message.answer("Хотите изменить фото для фильма?", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data in ["edit_photo_yes", "edit_photo_no"], state=FilmForm.photo)
async def process_edit_photo_choice(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "edit_photo_yes":
        await bot.send_message(callback_query.from_user.id, "Загрузите новое фото для фильма.")
        dp.register_message_handler(lambda msg: update_film_with_photo(msg, state), content_types=['photo'], state=FilmForm.photo)
    else:
        async with state.proxy() as data:
            update_film_in_db(data)
        await bot.send_message(callback_query.from_user.id, "Фильм обновлен.")
        await state.finish()

async def update_film_with_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['photo_id'] = message.photo[-1].file_id
        update_film_in_db(data)
    await message.answer("Фильм обновлен с новым фото.")
    await state.finish()

def update_film_in_db(data):
    conn = sqlite3.connect('films.db')
    cursor = conn.cursor()
    fields_to_update = {k: v for k, v in data.items() if k != 'film_id' and v is not None}
    if fields_to_update:
        set_clause = ", ".join([f"{field} = ?" for field in fields_to_update.keys()])
        values = list(fields_to_update.values()) + [data['film_id']]
        cursor.execute(f"UPDATE films SET {set_clause} WHERE id = ?", values)
        conn.commit()
    conn.close()

# @dp.callback_query_handler(lambda c: c.data == 'search_by_code')
# async def process_search_by_code(callback_query: types.CallbackQuery):
#     await bot.send_message(callback_query.from_user.id, "Введите код фильма для поиска")
#     dp.register_message_handler(get_film_by_code, state=None)

# @dp.callback_query_handler(lambda c: c.data == 'code_to_id')
# async def process_code_to_id(callback_query: types.CallbackQuery):
#     await bot.send_message(callback_query.from_user.id, "Введите код фильма, чтобы получить его ID")
#     dp.register_message_handler(get_film_id_by_code, state=None)

@dp.message_handler(state=CodeState.waiting_for_code)
async def get_film_by_code(message: types.Message, state: FSMContext):
    code = message.text
    conn = sqlite3.connect('films.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, release_date, director, year, rating, photo_id FROM films WHERE code=?", (code,))
    film = cursor.fetchone()
    if film:
        response = (f"Название: {film[0]}\nОписание: {film[1]}\nДата премьеры: {film[2]}"
                    f"\nРежиссер: {film[3]}\nГод: {film[4]}\nОценка: {film[5]}")
        if film[6]:  # Проверка наличия фото
            await message.answer_photo(film[6], caption=response)
        else:
            await message.answer(response)
    else:
        await message.answer("Фильм с таким кодом не найден.")
    conn.close()
    await state.finish()



if __name__ == '__main__':
    conn = sqlite3.connect('films.db')
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS films (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL,
        release_date TEXT NOT NULL,
        director TEXT NOT NULL,
        year TEXT NOT NULL,
        rating TEXT NOT NULL,
        photo_id TEXT
    )
    """)
    conn.commit()
    conn.close()
    executor.start_polling(dp, skip_updates=True)
