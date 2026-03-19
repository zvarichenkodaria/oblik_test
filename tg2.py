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
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ================== НАСТРОЙКИ ==================

logging.basicConfig(level=logging.INFO)
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

# ================== СЛУЖЕБНЫЕ ФУНКЦИИ (ОЧИСТКА) ==================

async def clear_stored_messages(chat_id: int, state: FSMContext):
    """Удаляет всё, что накопилось в списке msgs_to_delete"""
    data = await state.get_data()
    msg_ids = data.get("msgs_to_delete", [])
    for m_id in msg_ids:
        try:
            await bot.delete_message(chat_id, m_id)
        except:
            pass
    await state.update_data(msgs_to_delete=[])

async def add_to_delete(state: FSMContext, *messages: types.Message | int):
    """Добавляет сообщения в список на будущее удаление"""
    data = await state.get_data()
    current_ids = data.get("msgs_to_delete", [])
    for msg in messages:
        if msg:
            m_id = msg.message_id if isinstance(msg, types.Message) else msg
            if m_id not in current_ids:
                current_ids.append(m_id)
    await state.update_data(msgs_to_delete=current_ids)

async def clear_chat_history(chat_id: int):
    """Очистка истории сообщений бота (для команды decline)"""
    try:
        chat_history = await bot.get_chat_history(chat_id, limit=20)
        for msg in chat_history:
            if msg.from_user.is_bot:
                try:
                    await bot.delete_message(chat_id, msg.message_id)
                    await asyncio.sleep(0.1)
                except:
                    pass
    except:
        pass

# ================== ВОПРОСЫ ==================
questions = [
    {"q": "Какую структуру можно повредить в межфасциальном пространстве височной области?", "options": ["Сторожевая вена", "Поверхностная височная артерия", "Ушно-височный нерв"], "answer": "Сторожевая вена"},
    {"q": "Под какой мышцей располагается пространство Ристоу?", "options": ["Мышца, поднимающая верхнюю губу и крыло носа", "Мышца, поднимающая верхнюю губу", "Мышца, поднимающая угол рта"], "answer": "Мышца, поднимающая верхнюю губу и крыло носа"},
    {"q": "Какое осложнение возможно при травме подбородочного нерва?", "options": ["Потеря чувствительности нижней трети лица", "Атония мимической мускулатуры нижней трети лица", "Паралич подбородочной мышцы"], "answer": "Потеря чувствительности нижней трети лица"},
    {"q": "Какая мышца выполняет одновременно леваторную и депрессорную функции?", "options": ["Круговая мышца глаза", "Надчерепная мышца", "Подбородочная мышца"], "answer": "Круговая мышца глаза"},
    {"q": "Какая из перечисленных структур не формирует линию связок?", "options": ["Удерживающая глазничная связка (ORL)", "Височная адгезия", "Скуловая связка"], "answer": "Удерживающая глазничная связка (ORL)"},
    {"q": "Какая мышца не входит в состав SMAS?", "options": ["Височная мыщца", "Лобное брюшко затылочно-лобной мыщцы", "Ушно-височная мышца"], "answer": "Височная мыщца"},
    {"q": "По какому из анастомозов эмбол может попасть в бассейн глазной артерии?", "options": ["Глубокая височная артерия — скуловисочная артерия", "Поперечная артерия лица — подглазничная артерия", "Угловая артерия — подглазничная артерия"], "answer": "Глубокая височная артерия — скуловисочная артерия"},
    {"q": "Какая мышца отвечает за опущение хвоста брови?", "options": ["Круговая мышца глаза", "Мышца гордецов", "Мышца, опускающая бровь"], "answer": "Круговая мышца глаза"},
    {"q": "Наиболее частый мимический паттерн нижней трети лица", "options": ["Содружественный (DAO + platysma)", "Комбинированный (DAO + platysma + m. mentalis)", "Изолированный (работает только DAO)"], "answer": "Содружественный (DAO + platysma)"},
    {"q": "Подкожная клетчатка какой области обладает наиболее длинными соединительнотканными септами?", "options": ["Щёчной", "Околоушно-жевательной", "Подглазничной (малярный жировой пакет)"], "answer": "Щёчной"}
]

# ================== JSON ФУНКЦИИ ==================
def save_final_result(user_id: int, data: dict):
    filename = "users_data.json"
    storage = {}
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f: storage = json.load(f)
        except: pass
    user_key = str(user_id)
    if user_key not in storage: storage[user_key] = []
    attempt_info = {
        "attempt": len(storage[user_key]) + 1,
        "score": f"{data.get('score', 0)}/10",
        "name": data.get("name"), "email": data.get("email"),
        "city": data.get("city"), "phone": data.get("phone")
    }
    storage[user_key].append(attempt_info)
    with open(filename, "w", encoding="utf-8") as f: json.dump(storage, f, ensure_ascii=False, indent=4)

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$'
    return re.match(pattern, email)

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
        "При желании вы сможете пройти тест <b>несколько раз</b>, добившись идеального результата!"
        "</blockquote>\n\n"
        "🎁 За прохождение теста можно будет получить бесплатный мастер-класс! ",
        reply_markup=kb, parse_mode="HTML" 
    )
    await add_to_delete(state, welcome_msg)
    await state.set_state(TestState.waiting_start)

@dp.callback_query(F.data == "accept")
async def accept_callback(callback: types.CallbackQuery, state: FSMContext):
    msg1 = await callback.message.answer("Прежде чем начнём, давайте с вами познакомимся! ✨")
    msg2 = await callback.message.answer("Для начала напишите свой e-mail 📩")
    await add_to_delete(state, msg1, msg2)
    await state.set_state(TestState.email)
    await callback.answer()

@dp.callback_query(F.data == "decline")
async def decline_callback(callback: types.CallbackQuery, state: FSMContext):
    # УДАЛЯЕМ всё, что бот успел отправить до этого момента (приветствие, вопросы анкеты)
    await clear_stored_messages(callback.message.chat.id, state)
    
    # Удаляем само сообщение с кнопками Принять/Отклонить
    try:
        await callback.message.delete()
    except:
        pass
        
    await state.clear()
    
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
    try: await callback.message.delete()
    except: pass
    await cmd_start(callback.message, state)

@dp.message(TestState.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if not is_valid_email(email):
        err = await message.answer("❌ Упс! По-моему, e-mail некорректный!\nВведи еще раз")
        await add_to_delete(state, message, err)
        return
    msg = await message.answer("Как вас зовут? Напишите Имя и Фамилию 😊")
    await state.update_data(email=email)
    await add_to_delete(state, message, msg)
    await state.set_state(TestState.name)

@dp.message(TestState.name)
async def process_name(message: types.Message, state: FSMContext):
    msg = await message.answer("Из какого вы города? 🌍")
    await state.update_data(name=message.text.strip())
    await add_to_delete(state, message, msg)
    await state.set_state(TestState.city)

@dp.message(TestState.city)
async def process_city(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    msg = await message.answer("И номер телефона для связи 👇", reply_markup=kb)
    await state.update_data(city=message.text.strip())
    await add_to_delete(state, message, msg)
    await state.set_state(TestState.phone)

@dp.message(TestState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await add_to_delete(state, message)
    
    # Сразу удаляем анкету
    await clear_stored_messages(message.chat.id, state)

    transition_msg = await message.answer(
        "Спасибо, что рассказали о себе!\n🎯 Ну что ж, пора переходить <b>к тесту</b>!", 
        reply_markup=ReplyKeyboardRemove()
    )
    # Сохраняем transition_id отдельно, чтобы грохнуть при сбросе бота
    await state.update_data(phone=phone, score=0, current_q=0, transition_id=transition_msg.message_id)
    
    await asyncio.sleep(0.5)
    await send_question(message, state)

async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("current_q", 0)
    if idx < len(questions):
        q_data = questions[idx]
        options = q_data["options"][:]
        random.shuffle(options)
        
        # Кнопки с твоим стилем
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=options[0], callback_data=f"ans_{idx}_0")],
            [InlineKeyboardButton(text=options[1], callback_data=f"ans_{idx}_1")],
            [InlineKeyboardButton(text=options[2], callback_data=f"ans_{idx}_2")],
            [InlineKeyboardButton(text="🔄 Начать тест заново", callback_data="retry")]
        ])
        
        await state.update_data(current_options=options)
        sent_q = await message.answer(f"✔️ Вопрос {idx+1}/10:\n\n{q_data['q']}", reply_markup=kb)
        await add_to_delete(state, sent_q)
        await state.set_state(TestState.question)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Подвести итоги", callback_data="results")],
            [InlineKeyboardButton(text="🔄 Начать тест заново", callback_data="retry")]
        ])
        sent_final = await message.answer("✅ Вопросы закончились! Получается, что весь тест пройден. Хотите узнать итоги?", reply_markup=kb)
        await add_to_delete(state, sent_final)

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

    # Чистим старый вопрос перед новым
    await clear_stored_messages(callback.message.chat.id, state)
    await state.update_data(current_q=idx + 1)
    await send_question(callback.message, state)

@dp.callback_query(F.data == "results")
async def show_results(callback: types.CallbackQuery, state: FSMContext):
    await clear_stored_messages(callback.message.chat.id, state)
    data = await state.get_data()
    score = data.get("score", 0)
    save_final_result(callback.from_user.id, data)
    
    status = "🟢 Отличные знания анатомии!" if score >= 9 else "🟡 Есть, что повторить!" if score >= 7 else "🔴 Анатомия забыта!"
    txt = f"Благодарим за прохождение теста! Ваш результат:\n\n<b>{status}</b>\n{score} из 10 правильных ответов."
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Как получить мастер-класс?", callback_data="get_mc")],
        [InlineKeyboardButton(text="🔄 Пройти тест заново", callback_data="retry")],
        [InlineKeyboardButton(text="🗑 Сбросить бота (с нуля)", callback_data="full_reset")]
    ])
    await callback.message.answer(txt, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "get_mc")
async def show_mc_info(callback: types.CallbackQuery):
    txt = (
        "За <b>прохождение</b> теста вы получаете <b>мастер-класс</b> от журнала «Облик»!\n\n"
        "В течение суток он будет выслан вам на указанную электронную почту. 🕔 <i>Ждите!</i>\n\n"
        "Спасибо, что остаётесь с нами ❤️"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад к результатам", callback_data="results_back")]])
    await callback.message.edit_text(txt, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "results_back")
async def show_results_back(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)
    status = "🟢 Отличные знания анатомии!" if score >= 9 else "🟡 Есть, что повторить!" if score >= 7 else "🔴 Анатомия забыта!"
    txt = f"Благодарим за прохождение теста! Ваш результат:\n\n<b>{status}</b>\n{score} из 10 правильных ответов."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Как получить мастер-класс?", callback_data="get_mc")],
        [InlineKeyboardButton(text="🔄 Пройти тест заново", callback_data="retry")],
        [InlineKeyboardButton(text="🗑 Сбросить бота (с нуля)", callback_data="full_reset")]
    ])
    await callback.message.edit_text(txt, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "retry")
async def retry(callback: types.CallbackQuery, state: FSMContext):
    await clear_stored_messages(callback.message.chat.id, state)
    await state.update_data(current_q=0, score=0)
    try: await callback.message.delete()
    except: pass
    await send_question(callback.message, state)
    await callback.answer("Тест начат заново")

@dp.callback_query(F.data == "full_reset")
async def full_reset(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    t_id = data.get("transition_id")
    
    await clear_stored_messages(callback.message.chat.id, state)
    
    if t_id:
        try: await bot.delete_message(callback.message.chat.id, t_id)
        except: pass
        
    try: await callback.message.delete()
    except: pass
    
    await state.clear()
    await cmd_start(callback.message, state)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
