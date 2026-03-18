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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

# ================== ВОПРОСЫ ==================
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
    # ЗАЩИТА ОТ ID БОТА
    if user_id < 1000000000:  # ID бота обычно большой
        print(f"⚠️ Пропускаем сохранение ID бота: {user_id}")
        return
        
    filename = "users_data.json"
    storage = {}
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                storage = json.load(f)
        except:
            pass
    storage[str(user_id)] = data
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(storage, f, ensure_ascii=False, indent=4)

def log_new_user(user_id: int, username: str | None):
    filename = "all_users.json"
    storage = {}
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                storage = json.load(f)
        except:
            pass
    storage[str(user_id)] = username
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(storage, f, ensure_ascii=False, indent=4)

# Функция проверки email
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email)

# ================== /START ==================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
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
    # НЕ удаляем первое сообщение!
    
    # 1. СНАЧАЛА сообщение про знакомство
    intro_msg = await callback.message.answer(
        "Прежде чем начнём, давайте с вами познакомимся! "
        "Ответьте на пару вопросов - это поможет мне лучше сохранить ваши результаты. "
        "Обещаю, это быстро! ✨"
    )
    await state.update_data(intro_msg_id=intro_msg.message_id)
    
    # 2. ПОТОМ сразу email
    email_msg = await callback.message.answer(
        "Для начала напишите свой e-mail 📩. "
        "Именно на него придёт обещанный мастер-класс по анатомии после прохождения теста!"
    )
    await state.update_data(email_msg_id=email_msg.message_id)
    await state.set_state(TestState.email)
    await callback.answer("📧 Введите e-mail")

@dp.callback_query(F.data == "decline")
async def decline_callback(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Перейти в канал «Облик»", url="https://t.me/oblik_journal")],
        [InlineKeyboardButton(text="🔄 Вернуться к началу", callback_data="restart")]
    ])
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.message.edit_text(
        "Благодарим вас за уделенное время! Узнать больше о журнале «Облик» можно на официальном канале.",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data == "restart")
async def restart_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await cmd_start(callback.message, state)

# ================== СОБИРАЕМ ДАННЫЕ ==================
@dp.message(TestState.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    
    # ОЧИСТКА неуспешных попыток
    data = await state.get_data()
    failed_emails = data.get('failed_email_messages', [])
    for msg_id in failed_emails:
        try:
            await bot.delete_message(message.chat.id, msg_id)
        except:
            pass
    
    if not is_valid_email(email):
        # Сохраняем ID сообщения об ошибке для будущей очистки
        error_msg = await message.answer("❌ По-моему емейл некорректный!\nВведи еще раз")
        await state.update_data(
            failed_email_messages=data.get('failed_email_messages', []) + [error_msg.message_id]
        )
        return
    
    # Email корректный - очищаем ВСЕ сообщения об ошибках
    await state.update_data(failed_email_messages=[])
    
    # НЕ удаляем сообщение с запросом email (персональные данные!)
    await state.update_data(email=email)
    name_msg = await message.answer("Как вас зовут? Напишите Имя и Фамилию - будем знакомы! 😊")
    await state.update_data(name_msg_id=name_msg.message_id)
    await state.set_state(TestState.name)

@dp.message(TestState.name)
async def process_name(message: types.Message, state: FSMContext):
    # НЕ удаляем сообщения персональных данных!
    name = message.text.strip()
    await state.update_data(name=name)
    city_msg = await message.answer("Из какого вы города? 🌍")
    await state.update_data(city_msg_id=city_msg.message_id)
    await state.set_state(TestState.city)

@dp.message(TestState.city)
async def process_city(message: types.Message, state: FSMContext):
    # НЕ удаляем сообщения персональных данных!
    city = message.text.strip()
    await state.update_data(city=city)
    
    contact_msg = await message.answer("И номер телефона для связи 👇")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Отправить контакт", request_contact=True)]
    ])
    phone_msg = await message.answer("👇", reply_markup=kb)
    await state.update_data(phone_msg_id=phone_msg.message_id, contact_msg_id=contact_msg.message_id)
    await state.set_state(TestState.phone)

@dp.message(TestState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    # НЕ удаляем сообщения персональных данных!
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone, score=0, current_q=0, failed_email_messages=[])
    
    await message.answer("🎯 Ну что ж, пора переходить к тесту!")
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
            [InlineKeyboardButton(text=options[0], callback_data=f"q{idx}_0")],
            [InlineKeyboardButton(text=options[1], callback_data=f"q{idx}_1")],
            [InlineKeyboardButton(text=options[2], callback_data=f"q{idx}_2")],
            [InlineKeyboardButton(text=options[3], callback_data=f"q{idx}_3")]
        ])
        
        q_msg = await message.answer(q_data["q"], reply_markup=kb)
        await state.update_data(question_msg_id=q_msg.message_id)
        await state.set_state(TestState.question)
    else:
        await show_results(message, state)

@dp.callback_query(F.data.startswith("q"))
async def check_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = data.get("current_q", 0)
    correct = questions[idx]["answer"]
    
    # Проверяем правильный ли ответ
    option_idx = int(callback.data.split("_")[2])
    selected_option = questions[idx]["options"][option_idx]
    if selected_option == correct:
        data["score"] = data.get("score", 0) + 1
    
    data["current_q"] = idx + 1
    await state.set_data(data)
    
    # Красивое удаление вопроса с задержкой
    await callback.message.delete()
    await callback.answer()
    
    if data["current_q"] < len(questions):
        await asyncio.sleep(0.3)
        await send_question(callback.message, state)
    else:
        await show_results(callback.message, state)

async def show_results(message: types.Message, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)
    user_id = message.from_user.id
    save_user_data(user_id, data)
    
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