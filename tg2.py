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
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ================== НАСТРОЙКИ ==================

session = AiohttpSession(timeout=60)
API_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(
    token=API_TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
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

# ================== НОВАЯ ФУНКЦИЯ ОЧИСТКИ ==================
async def clear_chat_history(chat_id: int):
    """Удаляет последние 20 сообщений бота из чата"""
    try:
        for i in range(1, 21):  # Пробуем удалить последние 20 сообщений
            try:
                await bot.delete_message(chat_id, i)
            except:
                pass
        await asyncio.sleep(0.5)  # Пауза чтобы API не забанил
    except:
        pass

# ================== ВОПРОСЫ (ВСЕ 10 ШТУК) ==================
questions = [
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?",
    "options": ["Сторожевая вена", "Поверхностная височная артерия", "Ушно-височный нерв"],
    "answer": "Сторожевая вена"},
    {"q": "Под какой мышцей располагается пространство Ристоу?",
    "options": ["Мышца, поднимающая верхнюю губу и крыло носа", "Мышца, поднимающая верхнюю губу", "Мышца, поднимающая угол рта"],
    "answer": "Мышца, поднимающая верхнюю губу и крыло носа"},
    {"q": "Какое осложнение возможно при травме подбородочного нерва?",
    "options": ["Потеря чувствительности нижней трети лица", "Атония мимической мускулатуры нижней трети лица", "Паралич подбородочной мышцы"],
    "answer": "Потеря чувствительности нижней трети лица"},
    {"q": "Какая мышца выполняет одновременно леваторную и депрессорную функции?",
    "options": ["Круговая мышца глаза", "Надчерепная мышца", "Подбородочная мышца"],
    "answer": "Круговая мышца глаза"},
    {"q": "Какая из перечисленных структур не формирует линию связок?",
    "options": ["Удерживающая глазничная связка (ORL)", "Височная адгезия", "Скуловая связка"],
    "answer": "Удерживающая глазничная связка (ORL)"},
    {"q": "Какая мышца не входит в состав SMAS?",
    "options": ["Височная мыщца", "Лобное брюшко затылочно-лобной мыщцы", "Ушно-височная мышца"],
    "answer": "Височная мыщца"},
    {"q": "По какому из анастомозов эмбол может попасть в бассейн глазной артерии?",
    "options": ["Глубокая височная артерия — скуловисочная артерия", "Поперечная артерия лица — подглазничная артерия", "Угловая артерия — подглазничная артерия"],
    "answer": "Глубокая височная артерия — скуловисочная артерия"},
    {"q": "Какая мышца отвечает за опущение хвоста брови?",
    "options": ["Круговая мышца глаза", "Мышца гордецов", "Мышца, опускающая бровь"],
    "answer": "Круговая мышца глаза"},
    {"q": "Наиболее частый мимический паттерн нижней трети лица",
    "options": ["Содружественный (DAO + platysma)", "Комбинированный (DAO + platysma + m. mentalis)", "Изолированный (работает только DAO)"],
    "answer": "Содружественный (DAO + platysma)"},
    {"q": "Подкожная клетчатка какой области обладает наиболее длинными соединительнотканными септами?",
    "options": ["Щёчной", "Околоушно-жевательной", "Подглазничной (малярный жировой пакет)"],
    "answer": "Щёчной"}
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
    
    # ПУНКТ: Записываем попытку с баллами и данными, без истории вопросов
    attempt_info = {
        "attempt": len(storage[user_key]) + 1,
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
    # ПУНКТ: ID бота не должен попадать в список пользователей
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
    # ПУНКТ: Проверка на 2-4 символа домена (.ru, .com и т.д.)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$'
    return re.match(pattern, email)

# ================== /START ==================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    log_new_user(message.from_user.id, message.from_user.username)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Принять участие", callback_data="accept")],
        [InlineKeyboardButton(text="❌ Не хочу продолжать", callback_data="decline")]
    ])

    await message.answer(
        "Добро пожаловать в официальный Telegram-бот <b>журнала «Облик. Esthetic Guide»</b>.\n"
        "С нашим ботом вы сможете проверить и актуализировать знания по анатомии лица.\n\n"
        "<blockquote>"
        "Отвечая на вопросы, выбирайте тот ответ, который считаете <b>правильным</b>. "
        "Всего в тесте 10 вопросов. После их прохождения бот посчитает количество верных ответов. "
        "При желании вы сможете пройти тест <b>несколько раз</b>, добившись идеального результата!"
        "</blockquote>\n\n"
        "🎁 За прохождение теста можно будет получить бесплатный мастер-класс! ",
        reply_markup=kb,
        parse_mode="HTML" 
    )
    await state.set_state(TestState.waiting_start)

# ================== СБОР ДАННЫХ ==================
@dp.callback_query(F.data == "accept")
async def accept_callback(callback: types.CallbackQuery, state: FSMContext):
    msg1 = await callback.message.answer("Прежде чем начнём, давайте с вами познакомимся! ✨")
    msg2 = await callback.message.answer("Для начала напишите свой e-mail 📩")
    
    # Список для удаления персональных сообщений в будущем
    await state.update_data(personal_msgs=[msg1.message_id, msg2.message_id])
    await state.set_state(TestState.email)
    await callback.answer()

@dp.callback_query(F.data == "decline", state="*")
async def decline_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    
    # ✅ ОЧИСТКА ВСЕХ СООБЩЕНИЙ ПРИ "НЕ ХОЧУ"
    await clear_chat_history(callback.message.chat.id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔘 Перейти в канал «Облик»", url="https://t.me/oblikmagazine")],
        [InlineKeyboardButton(text="🔄 Вернуться к началу", callback_data="restart")]
    ])
    await callback.message.answer(
        "Благодарим вас за уделенное время! Узнать больше о журнале «Облик» можно на официальном канале.",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data == "restart")
async def restart_test(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await cmd_start(callback.message, state)

@dp.message(TestState.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    data = await state.get_data()
    f_msgs = data.get('failed_msgs', [])
    p_msgs = data.get('personal_msgs', [])

    if not is_valid_email(email):
        err = await message.answer("❌ Упс! По-моему, e-mail некорректный!\nВведи еще раз")
        await state.update_data(failed_msgs=f_msgs + [message.message_id, err.message_id])
        return

    # Чистим ошибки
    for m_id in f_msgs:
        try: await bot.delete_message(message.chat.id, m_id)
        except: pass
    
    msg = await message.answer("Как вас зовут? Напишите Имя и Фамилию 😊")
    await state.update_data(
        email=email, 
        failed_msgs=[], 
        personal_msgs=p_msgs + [message.message_id, msg.message_id]
    )
    await state.set_state(TestState.name)

@dp.message(TestState.name)
async def process_name(message: types.Message, state: FSMContext):
    msg = await message.answer("Из какого вы города? 🌍")
    data = await state.get_data()
    await state.update_data(
        name=message.text.strip(), 
        personal_msgs=data.get('personal_msgs', []) + [message.message_id, msg.message_id]
    )
    await state.set_state(TestState.city)

@dp.message(TestState.city)
async def process_city(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    msg = await message.answer("И номер телефона для связи 👇", reply_markup=kb)
    data = await state.get_data()
    await state.update_data(
        city=message.text.strip(), 
        personal_msgs=data.get('personal_msgs', []) + [message.message_id, msg.message_id]
    )
    await state.set_state(TestState.phone)

@dp.message(TestState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    data = await state.get_data()
    p_msgs = data.get('personal_msgs', []) + [message.message_id]
    
    # ПУНКТ: Удаляем все сообщения с персональными данными перед тестом
    for m_id in p_msgs:
        try: await bot.delete_message(message.chat.id, m_id)
        except: pass

    await state.update_data(phone=phone, score=0, current_q=0, personal_msgs=[])
    await message.answer("Спасибо, что рассказали о себе!\n" "🎯 Ну что ж, пора переходить <b>к тесту</b>!", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5)
    await send_question(message, state)

# ================== ТЕСТ ==================
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
            [InlineKeyboardButton(text=options[2], callback_data=f"ans_{idx}_2")]
        ])
        
        await state.update_data(current_options=options)
        await bot.send_chat_action(message.chat.id, "typing")
        await message.answer(f"✔️ Вопрос {idx+1}/10:\n\n{q_data['q']}", reply_markup=kb)
        await state.set_state(TestState.question)
    else:
        # ПУНКТ: Только одна кнопка
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎯 Подвести итоги", callback_data="results")]])
        await message.answer("✅ Вопросы закончились! Получается, что весь тест пройден. Хотите узнать итоги?", reply_markup=kb)

@dp.callback_query(F.data.startswith("ans_"))
async def check_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx, opt_idx = int(callback.data.split("_")[1]), int(callback.data.split("_")[2])
    
    options = data.get("current_options")
    if options[opt_idx] == questions[idx]["answer"]:
        await state.update_data(score=data.get("score", 0) + 1)
        await callback.answer("Верно! ✅")
    else:
        await callback.answer("Неверно ❌")

    # ПУНКТ: Красивое удаление вопроса
    try: await callback.message.delete()
    except: pass

    await state.update_data(current_q=idx + 1)
    await send_question(callback.message, state)

# ================== ИТОГИ И МАСТЕР-КЛАСС ==================
@dp.callback_query(F.data == "results")
async def show_results(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)
    save_final_result(callback.from_user.id, data)
    
    if score >= 9: 
        status = "🟢 Отличные знания анатомии!"
    elif score >= 7: 
        status = "🟡 Есть, что повторить!"
    else: 
        status = "🔴 Анатомия забыта!"
    
    # ПУНКТ: НОВЫЙ ТЕКСТ
    txt = f"Благодарим за прохождение теста! Ваш результат:\n\n<b>{status}</b>\n{score} из 10 правильных ответов."
    
    # ПУНКТ: ТРИ КНОПКИ У СООБЩЕНИЯ С РЕЗУЛЬТАТОМ
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Как получить мастер-класс?", callback_data="get_mc")],
        [InlineKeyboardButton(text="🔄 Пройти тест заново", callback_data="retry")],
        [InlineKeyboardButton(text="🗑 Сбросить бота (с нуля)", callback_data="full_reset")]
    ])
    await callback.message.edit_text(txt, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "get_mc")
async def show_mc_info(callback: types.CallbackQuery):
    # ПУНКТ: ВЫЛЕЗАЕТ СООБЩЕНИЕ ПРО МАСТЕР-КЛАСС ПРИ НАЖАТИИ
    txt = (
        "За <b>прохождение</b> теста вы получаете <b>мастер-класс</b> от журнала «Облик»!\n\n"
        "В течение суток он будет выслан вам на указанную электронную почту. 🕔 <i>Ждите!</i>\n\n"
        "Спасибо, что остаётесь с нами ❤️"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад к результатам", callback_data="results")]])
    await callback.message.edit_text(txt, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "retry")
async def retry(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(current_q=0, score=0)
    try: await callback.message.delete()
    except: pass
    await send_question(callback.message, state)

@dp.callback_query(F.data == "full_reset")
async def full_reset(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    
    # ✅ ОЧИСТКА ВСЕХ СООБЩЕНИЙ ПРИ "СБРОСИТЬ БОТА"
    await clear_chat_history(callback.message.chat.id)
    
    await cmd_start(callback.message, state)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
