import logging
import asyncio
import json
import os
import random
import re

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.client.session.aiohttp import AiohttpSession

# ================== НАСТРОЙКИ ==================
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class TestState(StatesGroup):
    waiting_start = State()
    email = State()
    name = State()
    city = State()
    phone = State()
    question = State()
    results = State()

# Список вопросов (оставил один для краткости примера, верните свои)
questions = [
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", 
     "options": ["Сторожевая вена", "Поверхностная височная артерия", "Ушно-височный нерв", "Щелочная мышца"], 
     "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", 
     "options": ["Сторожевая вена", "Поверхностная височная артерия", "Ушно-височный нерв", "Щелочная мышца"], 
     "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", 
     "options": ["Сторожевая вена", "Поверхностная височная артерия", "Ушно-височный нерв", "Щелочная мышца"], 
     "answer": "Сторожевая вена"},
]

# ================== JSON ФУНКЦИИ ==================
def save_user_data(user_id: int, data: dict):
    if user_id < 100000: return # Грубая проверка на системные ID
    filename = "users_data.json"
    storage = {}
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                storage = json.load(f)
        except: pass
    storage[str(user_id)] = data
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(storage, f, ensure_ascii=False, indent=4)

def log_new_user(user_id: int, username: str | None):
    # Проверка: не является ли user_id айдишником самого бота
    if str(user_id) == API_TOKEN.split(':')[0]:
        return
        
    filename = "all_users.json"
    storage = {}
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                storage = json.load(f)
        except: pass
    storage[str(user_id)] = username
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(storage, f, ensure_ascii=False, indent=4)

def is_valid_email(email):
    # Исправленное регулярное выражение
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email)

# ================== ХЭНДЛЕРЫ ==================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    log_new_user(message.from_user.id, message.from_user.username)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Принять участие", callback_data="accept")],
        [InlineKeyboardButton(text="❌ Не хочу продолжать", callback_data="decline")]
    ])

    await message.answer(
        "Добро пожаловать в бот журнала «Облик. Esthetic Guide»! 🎓\n"
        "Проверьте свои знания по анатомии лица. В тесте 10 вопросов.",
        reply_markup=kb
    )
    await state.set_state(TestState.waiting_start)

@dp.callback_query(F.data == "accept")
async def accept_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Прежде чем начнём, давайте познакомимся! ✨")
    await callback.message.answer("Напишите ваш e-mail 📩\nНа него мы пришлем мастер-класс.")
    await state.set_state(TestState.email)
    await callback.answer()

@dp.message(TestState.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    data = await state.get_data()
    error_msgs = data.get("error_msgs", [])

    if not is_valid_email(email):
        msg = await message.answer("❌ Упс, емейл кажется неверным! Попробуйте еще раз:")
        error_msgs.append(msg.message_id)
        error_msgs.append(message.message_id) # Добавляем и само сообщение юзера
        await state.update_data(error_msgs=error_msgs)
        return

    # Если емейл верный — удаляем весь "мусор"
    for m_id in error_msgs:
        try:
            await bot.delete_message(message.chat.id, m_id)
        except: pass
    
    await state.update_data(email=email, error_msgs=[])
    await message.answer("Приятно познакомиться! Теперь введите ваше Имя и Фамилию 😊")
    await state.set_state(TestState.name)

@dp.message(TestState.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Из какого вы города? 🌍")
    await state.set_state(TestState.city)

@dp.message(TestState.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    
    # Кнопка запроса телефона (только Reply Keyboard)
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Отправить контакт", request_contact=True)]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer("И последний шаг — ваш номер телефона 👇", reply_markup=kb)
    await state.set_state(TestState.phone)

@dp.message(TestState.phone, F.contact | F.text)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone, score=0, current_q=0)
    
    # Убираем Reply-кнопку
    await message.answer("🎯 Отлично! Начинаем тест...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(1)
    await send_question(message, state)

# ================== ТЕСТОВАЯ ЛОГИКА ==================

async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("current_q", 0)

    if idx < len(questions):
        q_item = questions[idx]
        opts = list(q_item["options"])
        random.shuffle(opts)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"ans_{idx}_{i}")] 
            for i, opt in enumerate(opts)
        ])

        await message.answer(f"Вопрос {idx+1}/10:\n\n{q_item['q']}", reply_markup=kb)
    else:
        await show_results(message, state)

@dp.callback_query(F.data.startswith("ans_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = int(callback.data.split("_")[1])
    opt_idx = int(callback.data.split("_")[2])
    
    # Получаем текст выбранной кнопки из разметки сообщения
    selected_text = callback.message.reply_markup.inline_keyboard[opt_idx][0].text
    
    if selected_text == questions[idx]["answer"]:
        await state.update_data(score=data.get("score, 0") + 1)
        # Можно добавить короткое уведомление
        await callback.answer("Верно! ✅")
    else:
        await callback.answer("Не совсем... ❌")

    # Красивое удаление текущего вопроса
    try:
        await callback.message.delete()
    except: pass

    await state.update_data(current_q=idx + 1)
    await asyncio.sleep(0.2) # Небольшая пауза для "гладкости"
    await send_question(callback.message, state)

async def show_results(message: types.Message, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)
    save_user_data(message.chat.id, data)

    res_text = "🏆 Тест завершен!\n\n"
    if score >= 9: res_text += f"🟢 Отлично! Ваш результат: {score}/10"
    elif score >= 7: res_text += f"🟡 Хорошо! Ваш результат: {score}/10"
    else: res_text += f"🔴 Нужно подучить анатомию. Ваш результат: {score}/10"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Пройти еще раз", callback_data="restart")]
    ])
    await message.answer(res_text, reply_markup=kb)

@dp.callback_query(F.data == "restart")
async def restart(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await cmd_start(callback.message, state)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
