import logging
import asyncio
import json
import os
import random
import re
import aiosqlite  # Не забудь: pip install aiosqlite

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ================== КЛАСС ДЛЯ ЗАПОМИНАНИЯ (SQLite) ==================

class SQLiteStorage(BaseStorage):
    def __init__(self, db_path="bot_database.db"):
        self.db_path = db_path

    async def _init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS fsm_data "
                "(key TEXT PRIMARY KEY, state TEXT, data TEXT)"
            )
            await db.execute(
                "CREATE TABLE IF NOT EXISTS test_results "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, info TEXT)"
            )
            await db.commit()

    async def set_state(self, key: StorageKey, state: State = None):
        k = f"{key.chat_id}:{key.user_id}"
        s = state.state if state else None
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO fsm_data (key, state, data) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET state = excluded.state",
                (k, s, "{}")
            )
            await db.commit()

    async def get_state(self, key: StorageKey):
        k = f"{key.chat_id}:{key.user_id}"
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT state FROM fsm_data WHERE key = ?", (k,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_data(self, key: StorageKey, data: dict):
        k = f"{key.chat_id}:{key.user_id}"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO fsm_data (key, state, data) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET data = excluded.data",
                (k, None, json.dumps(data, ensure_ascii=False))
            )
            await db.execute(
                "UPDATE fsm_data SET data = ? WHERE key = ?",
                (json.dumps(data, ensure_ascii=False), k)
            )
            await db.commit()

    async def get_data(self, key: StorageKey):
        k = f"{key.chat_id}:{key.user_id}"
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT data FROM fsm_data WHERE key = ?", (k,)) as cursor:
                row = await cursor.fetchone()
                return json.loads(row[0]) if row else {}

    async def close(self): pass

# ================== ФУНКЦИЯ СОХРАНЕНИЯ РЕЗУЛЬТАТОВ ==================

async def save_final_result_sql(user_id: int, data: dict):
    attempt_info = {
        "score": f"{data.get('score', 0)}/10",
        "name": data.get("name"), 
        "email": data.get("email"),
        "city": data.get("city"), 
        "phone": data.get("phone")
    }
    async with aiosqlite.connect("bot_database.db") as db:
        await db.execute(
            "INSERT INTO test_results (user_id, info) VALUES (?, ?)",
            (user_id, json.dumps(attempt_info, ensure_ascii=False))
        )
        await db.commit()

# ================== НАСТРОЙКИ ==================

logging.basicConfig(level=logging.INFO)
session = AiohttpSession(timeout=60)
API_TOKEN = os.getenv("BOT_TOKEN")

storage = SQLiteStorage()
bot = Bot(
    token=API_TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=storage)

# ================== СОСТОЯНИЯ ==================
class TestState(StatesGroup):
    waiting_start = State()
    email = State()
    name = State()
    city = State()
    phone = State()
    confirm = State()
    question = State()
    results = State()

# ================== СЛУЖЕБНЫЕ ФУНКЦИИ (ОЧИСТКА) ==================

async def clear_stored_messages(chat_id: int, state: FSMContext):
    data = await state.get_data()
    msg_ids = data.get("msgs_to_delete", [])
    for m_id in msg_ids:
        try:
            await bot.delete_message(chat_id, m_id)
        except:
            pass
    await state.update_data(msgs_to_delete=[])

async def add_to_delete(state: FSMContext, *messages: types.Message | int):
    data = await state.get_data()
    current_ids = data.get("msgs_to_delete", [])
    for msg in messages:
        if msg:
            m_id = msg.message_id if isinstance(msg, types.Message) else msg
            if m_id not in current_ids:
                current_ids.append(m_id)
    await state.update_data(msgs_to_delete=current_ids)

# ================== ВОПРОСЫ ==================
questions = [
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Сторожевая вена", "Поверхностная височная артерия", "Ушно-височный нерв"], "answer": "Сторожевая вена"},
#    {"q": "Под какой мышцей располагается пространство Ристоу?", "options": ["Поднимающая верхнюю губу и крыло носа", "Поднимающая верхнюю губу", "Поднимающая угол рта"], "answer": "Поднимающая верхнюю губу и крыло носа"},
#    {"q": "Какое осложнение возможно при травме подбородочного нерва?", "options": ["Потеря чувств. нижней трети лица", "Атония мимики нижней трети лица", "Паралич подбородочной мышцы"], "answer": "Потеря чувств. нижней трети лица"},
    {"q": "Какая мышца выполняет одновременно леваторную и депрессорную функции?", "options": ["Круговая мышца глаза", "Надчерепная мышца", "Подбородочная мышца"], "answer": "Круговая мышца глаза"},
    {"q": "Какая из перечисленных структур не формирует линию связок?", "options": ["Удерживающая глазничная связка", "Височная адгезия", "Скуловая связка"], "answer": "Удерживающая глазничная связка"},
    {"q": "Какая мышца не входит в состав SMAS?", "options": ["Височная мыщца", "Лобное брюшко ЗЛМ", "Ушно-височная мышца"], "answer": "Височная мыщца"},
#    {"q": "По какому из анастомозов эмбол может попасть в бассейн глазной артерии?", "options": ["Глубокая височная — скуловисочная", "Попереч. артерия лица — подглазничная", "Угловая — подглазничная"], "answer": "Глубокая височная — скуловисочная"},
    {"q": "Какая мышца отвечает за опущение хвоста брови?", "options": ["Круговая мышца глаза", "Мышца гордецов", "Мышца, опускающая бровь"], "answer": "Круговая мышца глаза"},
    {"q": "Наиболее частый мимический паттерн нижней трети лица", "options": ["DAO + platysma", "DAO + platysma + m. mentalis", "Работает только DAO"], "answer": "DAO + platysma"},
    {"q": "Подкожная клетчатка какой области обладает наиболее длинными соединительнотканными септами?", "options": ["Щёчной", "Околоушно-жевательной", "Подглазничной"], "answer": "Щёчной"},
    {"q": "Кто обладает наименьшей емкостью среди слоев височной области?", "options": ["Подкожная клетчатка", "Межфасциальное пространство", "Межапоневротическое пространство"], "answer": "Подкожная клетчатка"},
    {"q": "Пульсация какой артерии обнаруживается на 1-1,5 см спереди от козелка ушной раковины?", "options": ["Поперечной артерии лица", "Скуловисочной", "Поверхностной височной"], "answer": "Поверхностной височной"},
    {"q": "Как чаще всего располагается лицевая артерия по отношению к носогубной борозде?", "options": ["Непосредственно в ее проекции", "Медиальнее", "Латеральнее"], "answer": "Медиальнее"}
]

# ================== ПРОВЕРКИ ==================
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$'
    return re.match(pattern, email)

def is_valid_phone(phone: str) -> bool:
    cleaned = re.sub(r"[ \-\(\)]", "", phone)
    if cleaned.startswith("+"): cleaned = cleaned[1:]
    return cleaned.isdigit() and 8 <= len(cleaned) <= 15

# ================== ХЕНДЛЕРЫ ==================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Принять участие", callback_data="accept")],
        [InlineKeyboardButton(text="❌ Не хочу продолжать", callback_data="decline")]
    ])
    welcome_msg = await message.answer(
        "Добро пожаловать в официальный Telegram-бот <b>журнала «Облик. Esthetic Guide»</b>.\n"
        "С нашим ботом вы сможете проверить и актуализировать знания по анатомии лица.\n\n"
        "<blockquote>"
        "Отвечая на вопросы, выбирайте тот ответ, который считаете <b>правильным</b>. "
        "Всего в тесте 10 вопросов. После их прохождения бот посчитает количество верных ответов. "
        "</blockquote>\n\n"
        "Каждому прошедшему тест видео-мастер-класс по анатомии в подарок!",
        reply_markup=kb, parse_mode="HTML"
    )
    await add_to_delete(state, welcome_msg)
    await state.set_state(TestState.waiting_start)

@dp.callback_query(F.data == "accept")
async def accept_callback(callback: types.CallbackQuery, state: FSMContext):
    msg1 = await callback.message.answer("Прежде чем начнём, давайте с вами познакомимся!")
    msg2 = await callback.message.answer("Для начала напишите свой e-mail 📩")
    await add_to_delete(state, msg1, msg2)
    await state.set_state(TestState.email)
    await callback.answer()

@dp.callback_query(F.data == "decline")
async def decline_callback(callback: types.CallbackQuery, state: FSMContext):
    await clear_stored_messages(callback.message.chat.id, state)
    try: await callback.message.delete()
    except: pass
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔘 Перейти в канал «Облик»", url="https://t.me/oblikmagazine")],
        [InlineKeyboardButton(text="🔄 Вернуться к началу", callback_data="restart")]
    ])
    await callback.message.answer("Благодарим за уделенное время!", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "restart")
async def restart_test(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try: await callback.message.delete()
    except: pass
    await cmd_start(callback.message, state)

@dp.message(TestState.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if not is_valid_email(email):
        err = await message.answer("❌ Некорректный e-mail! Введите ещё раз")
        await add_to_delete(state, message, err)
        return
    await state.update_data(email=email)
    msg = await message.answer("Как вас зовут? Напишите имя и фамилию")
    await add_to_delete(state, message, msg)
    await state.set_state(TestState.name)

@dp.message(TestState.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    msg = await message.answer("Из какого вы города? 🌍")
    await add_to_delete(state, message, msg)
    await state.set_state(TestState.city)

@dp.message(TestState.city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]], resize_keyboard=True)
    msg = await message.answer("И номер телефона для связи 👇", reply_markup=kb)
    await add_to_delete(state, message, msg)
    await state.set_state(TestState.phone)

@dp.message(TestState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text.strip()
    if not message.contact and not is_valid_phone(phone):
        err = await message.answer("❌ Некорректный номер! Введите ещё раз")
        await add_to_delete(state, message, err)
        return
    await state.update_data(phone=phone)
    await add_to_delete(state, message)
    await clear_stored_messages(message.chat.id, state)
    await show_confirm_data(message, state)

async def show_confirm_data(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = (f"Ваши данные:\nИмя: <b>{data.get('name')}</b>\nГород: <b>{data.get('city')}</b>\n"
            f"E-mail: <b>{data.get('email')}</b>\nТелефон: <b>{data.get('phone')}</b>")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить имя", callback_data="change_name"), InlineKeyboardButton(text="Изменить город", callback_data="change_city")],
        [InlineKeyboardButton(text="Изменить e-mail", callback_data="change_email"), InlineKeyboardButton(text="Изменить телефон", callback_data="change_phone")],
        [InlineKeyboardButton(text="➡️ Далее", callback_data="confirm_next")]
    ])
    msg = await message.answer(text, reply_markup=kb)
    await add_to_delete(state, msg)
    await state.set_state(TestState.confirm)

@dp.callback_query(F.data.startswith("change_"))
async def change_data(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[1]
    msg = await callback.message.answer(f"Введите новое значение для {field}:", reply_markup=ReplyKeyboardRemove())
    await state.update_data(edit_field=field)
    await add_to_delete(state, msg)
    await callback.answer()

@dp.message(TestState.confirm)
async def update_field_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_field = data.get("edit_field")
    if edit_field:
        await state.update_data({edit_field: message.text.strip(), "edit_field": None})
    await add_to_delete(state, message)
    await clear_stored_messages(message.chat.id, state)
    await show_confirm_data(message, state)

@dp.callback_query(F.data == "confirm_next")
async def confirm_next(callback: types.CallbackQuery, state: FSMContext):
    await clear_stored_messages(callback.message.chat.id, state)
    transition_msg = await callback.message.answer("Пора переходить к тесту!", reply_markup=ReplyKeyboardRemove())
    await state.update_data(score=0, current_q=0, transition_id=transition_msg.message_id)
    await asyncio.sleep(0.5)
    await send_question(callback.message, state)
    await callback.answer()

async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("current_q", 0)
    if idx < len(questions):
        q_data = questions[idx]
        options = q_data["options"][:]
        random.shuffle(options)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=options[0], callback_data=f"ans_{idx}_0")],
            [InlineKeyboardButton(text=options[1], callback_data=f"ans_{idx}_1")],
            [InlineKeyboardButton(text=options[2], callback_data=f"ans_{idx}_2")],
            [InlineKeyboardButton(text="🔄 Начать заново", callback_data="retry")]
        ])
        await state.update_data(current_options=options)
        sent_q = await message.answer(f"✔️ Вопрос {idx+1}/10:\n\n{q_data['q']}", reply_markup=kb)
        await add_to_delete(state, sent_q)
        await state.set_state(TestState.question)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎯 Итоги", callback_data="results")]])
        sent_final = await message.answer("✅ Тест пройден!", reply_markup=kb)
        await add_to_delete(state, sent_final)

@dp.callback_query(F.data.startswith("ans_"))
async def check_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx, opt_idx = int(callback.data.split("_")[1]), int(callback.data.split("_")[2])
    options = data.get("current_options")
    if options[opt_idx] == questions[idx]["answer"]:
        await state.update_data(score=data.get("score", 0) + 1)
        await callback.answer("Верно! ✅")
    else: await callback.answer("Неверно ❌")
    await clear_stored_messages(callback.message.chat.id, state)
    await state.update_data(current_q=idx + 1)
    await send_question(callback.message, state)

@dp.callback_query(F.data == "results")
async def show_results(callback: types.CallbackQuery, state: FSMContext):
    await clear_stored_messages(callback.message.chat.id, state)
    data = await state.get_data()
    score = data.get("score", 0)
    await save_final_result_sql(callback.from_user.id, data)
    status = "🟢 Отлично!" if score >= 9 else "🟡 Хорошо!" if score >= 7 else "🔴 Повторите анатомию!"
    txt = f"Ваш результат: <b>{score} из 10</b>\n{status}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Мастер-класс", callback_data="get_mc")],
        [InlineKeyboardButton(text="🔄 Заново", callback_data="retry")],
        [InlineKeyboardButton(text="🗑 Сброс", callback_data="full_reset")]
    ])
    await callback.message.answer(txt, reply_markup=kb)

@dp.callback_query(F.data == "get_mc")
async def show_mc_info(callback: types.CallbackQuery):
    await callback.message.edit_text("Видео-мастер-класс будет выслан на почту в течение суток!", 
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="results")]]))

@dp.callback_query(F.data == "retry")
async def retry(callback: types.CallbackQuery, state: FSMContext):
    await clear_stored_messages(callback.message.chat.id, state)
    await state.update_data(current_q=0, score=0)
    await send_question(callback.message, state)
    await callback.answer()

@dp.callback_query(F.data == "full_reset")
async def full_reset(callback: types.CallbackQuery, state: FSMContext):
    await clear_stored_messages(callback.message.chat.id, state)
    await state.clear()
    await cmd_start(callback.message, state)

async def main():
    await storage._init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
