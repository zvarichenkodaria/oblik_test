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
session = AiohttpSession(timeout=60)
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ================== СОСТОЯНИЯ ==================
class TestState(StatesGroup):
    waiting_start = State()
    email = State()
    name = State()
    city = State()
    phone = State()
    question = State()
    results = State()

# ================== ВОПРОСЫ (ТВОИ ОРИГИНАЛЬНЫЕ) ==================
questions = [
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Сторожевая вена", "Поверхностная височная артерия", "Ушно-височный нерв", "Щелочная мышца"], "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Поверхностная височная артерия", "Сторожевая вена", "Ушно-височный нерв", "Лобная кость"], "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Ушно-височный нерв", "Поверхностная височная артерия", "Сторожевая вена", "Верхнечелюстная кость"], "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Сторожевая вена", "Ушно-височный нерв", "Поверхностная височная артерия", "Затылочная мышца"], "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Поверхностная височная артерия", "Сторожевая вена", "Ушно-височный нерв", "Глазничная артерия"], "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Сторожевая вена", "Ушно-височный нерв", "Поверхностная височная артерия", "Нижнечелюстная мышца"], "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Ушно-височный нерв", "Сторожевая вена", "Поверхностная височная артерия", "Сосцевидная кость"], "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Сторожевая вена", "Поверхностная височная артерия", "Ушно-височный нерв", "Круговая мышца рта"], "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Поверхностная височная артерия", "Ушно-височный нерв", "Сторожевая вена", "Подклювочная мышца"], "answer": "Сторожевая вена"},
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Сторожевая вена", "Ушно-височный нерв", "Поверхностная височная артерия", "Верхнегубная мышца"], "answer": "Сторожевая вена"}
]

# ================== JSON ФУНКЦИИ ==================
def save_user_data(user_id: int, data: dict):
    if user_id < 10000000: return # Защита

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
    # ПУНКТ 1: Проверка, чтобы ID бота не попадал в лог
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
    # ПУНКТ 2: Исправленное регулярное выражение
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email)

# ================== /START ==================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear() # Полная очистка при рестарте
    log_new_user(message.from_user.id, message.from_user.username)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Принять участие", callback_data="accept")],
        [InlineKeyboardButton(text="❌ Не хочу продолжать", callback_data="decline")]
    ])

    await message.answer(
        "Добро пожаловать в официальный Telegram-бот журнала «Облик. Esthetic Guide». "
        "С нашим ботом вы сможете проверить и актуализировать знания по анатомии лица. "
        "Отвечая на вопросы, выбирайте тот, что считаете верным. "
        "После прохождения всех 10 вопросов бот покажет вам количество верных. "
        "При желании вы сможете пройти тест несколько раз, добившись идеального результата!",
        reply_markup=kb
    )
    await state.set_state(TestState.waiting_start)

# ================== CALLBACK ХЭНДЛЕРЫ ==================
@dp.callback_query(F.data == "accept")
async def accept_callback(callback: types.CallbackQuery, state: FSMContext):
    intro_msg = await callback.message.answer(
        "Прежде чем начнём, давайте с вами познакомимся! "
        "Ответьте на пару вопросов - это поможет мне лучше сохранить ваши результаты. "
        "Обещаю, это быстро! ✨"
    )
    email_msg = await callback.message.answer(
        "Для начала напишите свой e-mail 📩. "
        "Именно на него придёт обещанный мастер-класс по анатомии после прохождения теста!"
    )
    await state.update_data(intro_msg_id=intro_msg.message_id, email_msg_id=email_msg.message_id)
    await state.set_state(TestState.email)
    await callback.answer()

@dp.callback_query(F.data == "decline")
async def decline_callback(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Перейти в канал «Облик»", url="https://t.me/oblik_journal")],
        [InlineKeyboardButton(text="🔄 Вернуться к началу", callback_data="restart")]
    ])
    await callback.message.edit_text(
        "Благодарим вас за уделенное время! Узнать больше о журнале «Облик» можно на официальном канале.",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data == "restart")
async def restart_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except: pass
    await cmd_start(callback.message, state)

# ================== СОБИРАЕМ ДАННЫЕ ==================
@dp.message(TestState.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    data = await state.get_data()
    failed_emails = data.get('failed_email_messages', [])

    if not is_valid_email(email):
        # ПУНКТ 2: Сохраняем ID сообщения юзера и ответа бота для удаления
        error_msg = await message.answer("❌ По-моему емейл некорректный!\nВведи еще раз")
        failed_emails.extend([message.message_id, error_msg.message_id])
        await state.update_data(failed_email_messages=failed_emails)
        return

    # Если емейл верный — удаляем все неудачные попытки
    for msg_id in failed_emails:
        try:
            await bot.delete_message(message.chat.id, msg_id)
        except: pass
    
    await state.update_data(email=email, failed_email_messages=[])
    await message.answer("Как вас зовут? Напишите Имя и Фамилию - будем знакомы! 😊")
    await state.set_state(TestState.name)

@dp.message(TestState.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Из какого вы города? 🌍")
    await state.set_state(TestState.city)

@dp.message(TestState.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    
    # ПУНКТ 3: Правильная кнопка "Отправить контакт" (ReplyKeyboardMarkup)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("И номер телефона для связи 👇", reply_markup=kb)
    await state.set_state(TestState.phone)

@dp.message(TestState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone, score=0, current_q=0)

    # Удаляем Reply-кнопку и переходим к тесту
    await message.answer("🎯 Ну что ж, пора переходить к тесту!", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(1)
    await send_question(message, state)

# ================== ТЕСТ ==================
async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("current_q", 0)

    if idx < len(questions):
        q_data = questions[idx].copy()
        options = q_data["options"][:]
        random.shuffle(options)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"ans_{idx}_{i}")] 
            for i, opt in enumerate(options)
        ])
        
        # Сохраняем варианты в стейт, чтобы проверить правильность по тексту
        await state.update_data(current_options=options)
        await message.answer(f"Вопрос {idx+1}/10:\n\n{q_data['q']}", reply_markup=kb)
        await state.set_state(TestState.question)
    else:
        await show_results(message, state)

@dp.callback_query(F.data.startswith("ans_"))
async def check_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = int(callback.data.split("_")[1])
    opt_idx = int(callback.data.split("_")[2])
    
    options = data.get("current_options")
    selected_text = options[opt_idx]
    
    if selected_text == questions[idx]["answer"]:
        await state.update_data(score=data.get("score", 0) + 1)
        await callback.answer("Верно! ✅")
    else:
        await callback.answer("Неверно ❌")

    # ПУНКТ 4: Красивое удаление вопроса
    try:
        await callback.message.delete()
    except: pass

    await state.update_data(current_q=idx + 1)
    # Плавный переход к следующему вопросу
    await asyncio.sleep(0.3)
    await send_question(callback.message, state)

async def show_results(message: types.Message, state: FSMContext):
    data = await state.get_data()
    save_user_data(message.chat.id, data)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Подвести итоги", callback_data="results")],
        [InlineKeyboardButton(text="🔄 Вернуться к началу", callback_data="restart")]
    ])

    await message.answer("✅ Ну что, весь тест пройден! Хочешь узнать итоги?", reply_markup=kb)
    await state.set_state(TestState.results)

@dp.callback_query(F.data == "results")
async def show_final_results(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)

    if score >= 9:
        result = f"🟢 Отличные знания!\nВаш результат: {score}/10"
    elif score >= 7:
        result = f"🟡 Есть, что повторить!\nВаш результат: {score}/10"
    else:
        result = f"🔴 Анатомия забыта!\nВаш результат: {score}/10"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Вернуться к началу", callback_data="restart")]
    ])

    await callback.message.edit_text(result, reply_markup=kb)
    await callback.answer()

# ================== ЗАПУСК ==================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
