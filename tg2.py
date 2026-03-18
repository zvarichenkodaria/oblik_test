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
# ВОЗВРАЩЕНО: Сессия с таймаутом
session = AiohttpSession(timeout=60)
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

# ================== СОСТОЯНИЯ ==================
class TestState(StatesGroup):
    email = State()
    name = State()
    city = State()
    phone = State()
    question = State()
    results = State()

# ================== ВСЕ 10 ВОПРОСОВ ==================
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
def save_final_result(user_id: int, data: dict):
    filename = "users_data.json"
    storage = {}
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                storage = json.load(f)
        except: pass
    
    user_key = str(user_id)
    if user_key not in storage:
        storage[user_key] = []
    
    # Сохраняем только итоговые данные попытки
    attempt_info = {
        "attempt_number": len(storage[user_key]) + 1,
        "score": f"{data.get('score', 0)}/10",
        "name": data.get("name"),
        "email": data.get("email"),
        "city": data.get("city"),
        "phone": data.get("phone")
    }
    storage[user_key].append(attempt_info)
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(storage, f, ensure_ascii=False, indent=4)

def log_new_user(user_id: int, username: str | None):
    # Проверка на ID бота (чтобы не логгировать самого себя)
    if str(user_id) == API_TOKEN.split(':')[0]: return
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
    # Исправленная регулярка: домен 2-4 символа (пресекает .ruu)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$'
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
        "Добро пожаловать в официальный Telegram-бот журнала «Облик. Esthetic Guide». "
        "С нашим ботом вы сможете проверить и актуализировать знания по анатомии лица. "
        "Отвечая на вопросы, выбирайте тот, что считаете верным. "
        "После прохождения всех 10 вопросов бот покажет вам количество верных. "
        "При желании вы сможете пройти тест несколько раз, добившись идеального результата!",
        reply_markup=kb
    )

@dp.callback_query(F.data == "accept")
async def accept_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Прежде чем начнём, давайте с вами познакомимся! ✨")
    await asyncio.sleep(0.5)
    await callback.message.answer("Для начала напишите свой e-mail 📩")
    await state.set_state(TestState.email)
    await callback.answer()

@dp.message(TestState.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    data = await state.get_data()
    failed_msgs = data.get('failed_msgs', [])

    if not is_valid_email(email):
        err = await message.answer("❌ По-моему емейл некорректный!\nПроверьте домен и введите еще раз")
        failed_msgs.extend([message.message_id, err.message_id])
        await state.update_data(failed_msgs=failed_msgs)
        return

    # Удаление мусора (ошибок) при успешном вводе
    for m_id in failed_msgs:
        try: await bot.delete_message(message.chat.id, m_id)
        except: pass
    
    await state.update_data(email=email, failed_msgs=[])
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
    # Кнопка запроса контакта
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
    await message.answer("🎯 Ну что ж, пора переходить к тесту!", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.8)
    await send_question(message, state)

# ================== ТЕСТОВАЯ ЛОГИКА ==================

async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("current_q", 0)

    if idx < len(questions):
        q_data = questions[idx]
        options = q_data["options"][:]
        random.shuffle(options)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"ans_{idx}_{i}")] for i, opt in enumerate(options)
        ])
        
        await state.update_data(current_options=options)
        # Визуальная задержка "печатает..."
        await bot.send_chat_action(message.chat.id, "typing")
        await asyncio.sleep(0.5)
        await message.answer(f"Вопрос {idx+1}/10:\n\n{q_data['q']}", reply_markup=kb)
        await state.set_state(TestState.question)
    else:
        # Только одна кнопка
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎯 Подвести итоги", callback_data="results")]])
        await message.answer("✅ Ну что, весь тест пройден! Хочешь узнать итоги?", reply_markup=kb)

@dp.callback_query(F.data.startswith("ans_"))
async def check_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = int(callback.data.split("_")[1])
    opt_idx = int(callback.data.split("_")[2])
    
    options = data.get("current_options")
    if options[opt_idx] == questions[idx]["answer"]:
        await state.update_data(score=data.get("score", 0) + 1)
        await callback.answer("Верно! ✅")
    else:
        await callback.answer("Неверно ❌")

    # Удаление старого вопроса
    try: await callback.message.delete()
    except: pass

    await state.update_data(current_q=idx + 1)
    await send_question(callback.message, state)

@dp.callback_query(F.data == "results")
async def show_final_results(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)
    save_final_result(callback.from_user.id, data)

    # Текст финала по ТЗ
    txt = (f"Ваш результат: {score}/10. За прохождение вы получаете мастер класс, "
           "который будет в скором времени выслан вам на указанную электронную почту "
           "вне зависимости от результатов теста. Спасибо что были с нами!")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Получить мастер-класс", url="https://t.me/oblik_journal")],
        [InlineKeyboardButton(text="🔄 Пройти тест заново", callback_data="retry_test")],
        [InlineKeyboardButton(text="🗑 Запустить бота с нуля", callback_data="restart_full")]
    ])

    try: await callback.message.delete()
    except: pass
    await callback.message.answer(txt, reply_markup=kb)

# ================== КНОПКИ ФИНАЛА ==================

@dp.callback_query(F.data == "retry_test")
async def retry_test(callback: types.CallbackQuery, state: FSMContext):
    # Оставляем данные юзера, сбрасываем только тест
    await state.update_data(current_q=0, score=0)
    try: await callback.message.delete()
    except: pass
    await send_question(callback.message, state)

@dp.callback_query(F.data == "restart_full")
async def restart_full(callback: types.CallbackQuery, state: FSMContext):
    # Полный сброс (удаление из стейта)
    try: await callback.message.delete()
    except: pass
    await cmd_start(callback.message, state)

@dp.callback_query(F.data == "decline")
async def decline_callback(callback: types.CallbackQuery):
    await callback.message.edit_text("Очень жаль! Если передумаете — напишите /start")

# ================== ЗАПУСК ==================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
