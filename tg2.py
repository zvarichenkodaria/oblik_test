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
    confirm = State()
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
    {"q": "Под какой мышцей располагается пространство Ристоу?", "options": ["Поднимающая верхнюю губу и крыло носа", "Поднимающая верхнюю губу", "Поднимающая угол рта"], "answer": "Поднимающая верхнюю губу и крыло носа"},
    {"q": "Какое осложнение возможно при травме подбородочного нерва?", "options": ["Потеря чувств. нижней трети лица", "Атония мимики нижней трети лица", "Паралич подбородочной мышцы"], "answer": "Потеря чувств. нижней трети лица"},
    {"q": "Какая мышца выполняет одновременно леваторную и депрессорную функции?", "options": ["Круговая мышца глаза", "Надчерепная мышца", "Подбородочная мышца"], "answer": "Круговая мышца глаза"},
    {"q": "Какая из перечисленных структур не формирует линию связок?", "options": ["Удерживающая глазничная связка (ORL)", "Височная адгезия", "Скуловая связка"], "answer": "Удерживающая глазничная связка (ORL)"},
    {"q": "Какая мышца не входит в состав SMAS?", "options": ["Височная мыщца", "Лобное брюшко ЗЛМ", "Ушно-височная мышца"], "answer": "Височная мыщца"},
    {"q": "По какому из анастомозов эмбол может попасть в бассейн глазной артерии?", "options": ["Глубокая височная — скуловисочная", "Попереч. артерия лица — подглазничная", "Угловая — подглазничная"], "answer": "Глубокая височная — скуловисочная"},
    {"q": "Какая мышца отвечает за опущение хвоста брови?", "options": ["Круговая мышца глаза", "Мышца гордецов", "Мышца, опускающая бровь"], "answer": "Круговая мышца глаза"},
    {"q": "Наиболее частый мимический паттерн нижней трети лица", "options": ["DAO + platysma", "DAO + platysma + m. mentalis", "Работает только DAO"], "answer": "DAO + platysma"},
    {"q": "Подкожная клетчатка какой области обладает наиболее длинными соединительнотканными септами?", "options": ["Щёчной", "Околоушно-жевательной", "Подглазничной (малярный жировой пакет)"], "answer": "Щёчной"}
]


# ================== JSON ФУНКЦИИ ==================
def save_final_result(user_id: int, data: dict):
    filename = "users_data.json"
    storage = {}
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                storage = json.load(f)
        except:
            pass
    user_key = str(user_id)
    if user_key not in storage:
        storage[user_key] = []
    attempt_info = {
        "attempt": len(storage[user_key]) + 1,
        "score": f"{data.get('score', 0)}/10",
        "name": data.get("name"), "email": data.get("email"),
        "city": data.get("city"), "phone": data.get("phone")
    }
    storage[user_key].append(attempt_info)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(storage, f, ensure_ascii=False, indent=4)


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$'
    return re.match(pattern, email)


def is_valid_phone(phone: str) -> bool:
    # Убираем пробелы, дефисы, скобки
    cleaned = re.sub(r"[ \-\(\)]", "", phone)
    # Разрешаем ведущий +
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    # Должно остаться только от 8 до 15 цифр
    if not cleaned.isdigit():
        return False
    return 8 <= len(cleaned) <= 15


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
        "За прохождение теста можно будет получить бесплатный мастер-класс! ",
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
    try:
        await callback.message.delete()
    except:
        pass
    await cmd_start(callback.message, state)


@dp.message(TestState.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if not is_valid_email(email):
        err = await message.answer("❌ Похоже, e-mail некорректный!\nВведите ещё раз")
        await add_to_delete(state, message, err)
        return
    msg = await message.answer("Как вас зовут? Напишите имя и фамилию")
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
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    msg = await message.answer("И номер телефона для связи 👇", reply_markup=kb)
    await state.update_data(city=message.text.strip())
    await add_to_delete(state, message, msg)
    await state.set_state(TestState.phone)


@dp.message(TestState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text.strip()

    if not message.contact and not is_valid_phone(phone):
        err = await message.answer(
            "❌ Похоже, номер телефона некорректный!\nВведите ещё раз"
        )
        await add_to_delete(state, message, err)
        return

    await add_to_delete(state, message)
    await state.update_data(phone=phone)

    await clear_stored_messages(message.chat.id, state)
    await show_confirm_data(message, state)


async def show_confirm_data(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = (
        "Вот ваши введённые данные:\n\n"
        f"Имя: <b>{data.get('name')}</b>\n"
        f"Город: <b>{data.get('city')}</b>\n"
        f"E-mail: <b>{data.get('email')}</b>\n"
        f"Телефон: <b>{data.get('phone')}</b>\n\n"
        "Если хотите что-то изменить — нажмите на кноки ниже.\n"
        "Если вся информация верная — нажмите <b>«Далее»</b>!"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Изменить имя", callback_data="change_name"),
            InlineKeyboardButton(text="Изменить город", callback_data="change_city"),
        ],
        [
            InlineKeyboardButton(text="Изменить e-mail", callback_data="change_email"),
            InlineKeyboardButton(text="Изменить телефон", callback_data="change_phone"),
        ],
        [InlineKeyboardButton(text="➡️ Далее", callback_data="confirm_next")],
    ])

    msg = await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await add_to_delete(state, msg)
    await state.set_state(TestState.confirm)


@dp.callback_query(F.data.startswith("change_"))
async def change_data(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[1]

    prompts = {
        "name": "Введите новое имя и фамилию:",
        "city": "Введите новый город:",
        "email": "Введите новый e-mail:",
        "phone": "Введите новый номер телефона:",
    }
    prompt_text = prompts.get(field, "Введите новое значение:")

    msg = await callback.message.answer(prompt_text, reply_markup=ReplyKeyboardRemove())
    await state.update_data(edit_field=field)
    await add_to_delete(state, msg)

    await state.set_state(TestState.confirm)
    await callback.answer()


@dp.message(TestState.confirm)
async def update_field_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    edit_field = data.get("edit_field")

    if not edit_field:
        return

    value = message.text.strip()

    if edit_field == "email" and not is_valid_email(value):
        err = await message.answer("❌ Похоже, e-mail некорректный!\nВведите ещё раз")
        await add_to_delete(state, message, err)
        return

    if edit_field == "phone" and not is_valid_phone(value):
        err = await message.answer(
            "❌ Похоже, номер телефона некорректный!\nВведите ещё раз"
        )
        await add_to_delete(state, message, err)
        return

    await state.update_data({edit_field: value, "edit_field": None})

    await add_to_delete(state, message)
    await clear_stored_messages(message.chat.id, state)
    await show_confirm_data(message, state)


@dp.callback_query(F.data == "confirm_next")
async def confirm_next(callback: types.CallbackQuery, state: FSMContext):
    await clear_stored_messages(callback.message.chat.id, state)

    transition_msg = await callback.message.answer(
        "Спасибо, что рассказали о себе!\nПора переходить <b>к тесту</b>!",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

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
        sent_final = await message.answer(
            "✅ Вопросы закончились! Получается, что весь тест пройден. Хотите узнать итоги?",
            reply_markup=kb
        )
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
        [InlineKeyboardButton(text="🗑 Сбросить бота (начать с нуля)", callback_data="full_reset")]
    ])
    await callback.message.answer(txt, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.data == "get_mc")
async def show_mc_info(callback: types.CallbackQuery):
    txt = (
        "За <b>прохождение</b> теста вы получаете <b>мастер-класс</b> от журнала «Облик»!\n\n"
        "В течение суток он будет выслан вам на указанную электронную почту. 🕔 <i>Ждите!</i>\n\n"
        "Спасибо, что остаётесь с нами ❤️"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к результатам", callback_data="results_back")]
    ])
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
    try:
        await callback.message.delete()
    except:
        pass
    await send_question(callback.message, state)
    await callback.answer("Тест начат заново")


@dp.callback_query(F.data == "full_reset")
async def full_reset(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    t_id = data.get("transition_id")

    await clear_stored_messages(callback.message.chat.id, state)

    if t_id:
        try:
            await bot.delete_message(callback.message.chat.id, t_id)
        except:
            pass

    try:
        await callback.message.delete()
    except:
        pass

    await state.clear()
    await cmd_start(callback.message, state)


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
