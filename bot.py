import asyncio
import logging
import aiocron
import gspread
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, Poll, PollAnswer
from aiogram.filters import Command
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# Замените 'YOUR_BOT_TOKEN' на токен из BotFather
BOT_TOKEN = "7574629305:AAGyXwXdqp55H-r6qqyFgUGqdYknQ9iLZLc"

# Создаём объект бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def connect_to_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name("tg-bot-454109-5f09ec8f1c5b.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open("Фильмы").sheet1  # Открываем первую страницу
    return sheet

# Обрабатываем команду /start
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer("Привет! Я бот для голосования по фильмам. Используйте /фильм НазваниеФильма, чтобы предложить фильм.")


# Список для хранения предложенных фильмов
film_suggestions = set()
poll_results = {}  # Словарь для хранения голосов
poll_id = None  # Переменная для хранения ID голосования
chat_id = -4642887339

# Обрабатываем команду /фильм НазваниеФильма
@dp.message(Command("фильм"))
async def suggest_film(message: Message):
    args = message.text.split(maxsplit=1)  # Разбиваем текст команды
    if len(args) < 2:
        await message.answer("Пожалуйста, укажите название фильма. Пример:\n/фильм Матрица")
        return

    film_name = args[1].strip()

    #special for liza
    if len(film_name) == len("титаник"):
        film = film_name.lower()    
        if (film[0] == "т" or film[0] == "t") and (film[2] == "т" or film[2] == "t") and 
            (film[3] == "а" or film[3] == "a") and (film[4] == "н" or film[4] == "h") and 
            (film[-1] == "к" or film[-1] == "k"):
            await  message.answer(f"Никакого блять Титаника!!!")

    # Проверяем, нет ли уже такого фильма в списке
    if film_name.lower() in (name.lower() for name in film_suggestions):
        await message.answer(f"Фильм '{film_name}' уже был предложен!")
    else:
        film_suggestions.add(film_name)
        await message.answer(f"Фильм '{film_name}' добавлен в список предложений!")

@dp.message(Command("фото"))
async def take_all_photos(message: Message):
    if !check_command(message):
        return
    sunday = get_prev_sunday()    #ищем ближайшее время до воскресения
                                  #начиная с воскресения до пн (окончание пн еще думаю) 
                                  #нужно собрать все медиафайлы и загрузить их на гугл диск
    return

#special for CBOdron or Apollon
@dp.message(Command("анекдот"))
async def tell_anekdot(message : Message):
    if !check_command(message):
        return

    #Нужно, чтобы бот заходил и искал анекдоты и отправлял их
    await message.answer()


# Функция для автоматического запуска голосования
def check_command(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пожалуйсте, введите правильную команду")
        return False
    return True
    
async def scheduled_poll():
    global poll_id, poll_results

    if not film_suggestions:
        await bot.send_message(chat_id, "На этой неделе никто не предложил фильмы 😕")
        return
    elif len(film_suggestions) == 1:
        only_film = next(iter(film_suggestions))
        await bot.send_message(chat_id, f"На этой неделе предложен только один фильм: {only_film} 🎬")
        film_suggestions.clear()
        return

    films_list = list(film_suggestions)
    film_suggestions.clear()

    poll_message = await bot.send_poll(
        chat_id=chat_id,
        question="Какой фильм будем смотреть?",
        options=films_list,
        is_anonymous=False,
        allows_multiple_answers=True
    )

    sunday    # Сохраняем id голосования для дальнейшего использования
    poll_id = poll_message.poll.id
    print(f"Poll ID: {poll_id}")

    poll_results = {option: 0 for option in films_list}

    # Ожидаем 24 часа (до субботы в 5 вечера) перед закрытием голосования
    await asyncio.sleep(86400)  #86400 24 часа в секундах

    max_votes = max(poll_results.values())
    winners = [film for film, votes in poll_results.items() if votes == max_votes]

    if len(winners) == 1:
        await bot.send_message(chat_id, f"Победитель голосования: {winners[0]} с {max_votes} голосами!")
        await save_winner_to_google_sheets(winners[0])
    else:
        await bot.send_message(chat_id, "Обнаружена ничья! Запускаем дополнительное голосование.")

        second_poll_message = await bot.send_poll(
            chat_id= chat_id,
            question= "Какой фильм будем смотреть?",
            options= winners,
            is_anonymous= False,
            allows_multiple_answers=True
        )

        poll_id = second_poll_message.poll.id
        poll_results = {option: 0 for option in winners}

        await asyncio.sleep(86400/2)

        second_max_votes = max(poll_results.values())
        final_winners = [film for film, votes in poll_results.items() if votes == second_max_votes]

        if len(final_winners) == 1:
            await bot.send_message(chat_id, f"Окончательный победитель: {final_winners[0]}!")
            await save_winner_to_google_sheets(final_winners[0])
        else:
            await bot.send_message(chat_id, "Снова ничья! Все фильмы попадают в таблицу.")
            for film in final_winners:
                await save_winner_to_google_sheets(film)


@dp.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer):
    global poll_results, poll_id

    if poll_id and poll_answer.poll_id == poll_id:
        for option_id in poll_answer.option_ids:
            option_text = list(poll_results.keys())[option_id]  # Получаем текст варианта
            poll_results[option_text] += 1  # Увеличиваем счётчик голосов


#aiocron.crontab("*/1 * * * *", func=scheduled_poll)
def get_prev_sunday():
    today = datetime.today()
    days_hps_sunday = (6 - today.weekday()) % 7
    if days_hps_sunday == 0:
        days_hps_sunday = -7
    prev_sunday = today - timedelta(days=days_hps_sunday)
    return prev_sunday.strftime("%d.%m.%y")
    
def get_next_sunday():
    today = datetime.today()
    days_until_sunday = (6 - today.weekday()) % 7  # 6 - воскресенье, weekday() начинается с 0 (понедельник)
    if days_until_sunday == 0:
        days_until_sunday = 7  # Если сегодня воскресенье, берем следующее
    next_sunday = today + timedelta(days=days_until_sunday)
    return next_sunday.strftime("%d.%m.%y")

async def start_rating_poll(winner: str):
    poll_message = await bot.send_poll(
        chat_id=chat_id,
        question=f'Оцените фильм "{winner}" от 1 до 10!',
        options=[str(i) for i in range(1, 11)],
        is_anonymous=False,
        allows_multiple_answers=False
    )

    global poll_id, poll_results
    poll_id = poll_message.poll.id
    poll_results = {str(i): 0 for i in range(1,11)}

    await asyncio.sleep(43200)

    await calculate_rating()

async def calculate_rating():
    total_votes = sum(poll_results.values())
    if total_votes == 0:
        await bot.send_message(chat_id, "Никто не проголосовал за оценку фильма 😕")
        return

    total_score = sum(int(score) * votes for score, votes in poll_results.items())
    avg_rating = round(total_score / total_votes, 1)

    await bot.send_message(chat_id, f'Средняя оценка фильма: {avg_rating} ⭐')

    sheet = connect_to_google_sheets()
    last_row = len(sheet.get_all_values())
    sheet.update_cell(last_row, 4, avg_rating)

async def save_winner_to_google_sheets(winner: str):
    sheet = connect_to_google_sheets()
    sunday_date = get_next_sunday()
    time = "22:00"

    sheet.append_row([winner, sunday_date, time])
    print(f'Добавлен победитель в таблицу: {winner} ({sunday_date} в {time})')

    now = datetime.now()
    monday_1am = now.replace(hour=1, minute=0, second=0, microsecond=0) + timedelta(days=1)
    wait_time = (monday_1am - now).total_seconds()
    print(f'Запуск голосования оценок фильма через {wait_time/ 3600:.2f} часов')
    await asyncio.sleep(wait_time)

    await start_rating_poll(winner)

@dp.message(Command("голосование"))
async def start_poll(message: Message):
    if not film_suggestions:
        await message.answer("Список фильмов пуст! Добавьте хотя бы один фильм командой /фильм.")
        return

    # Создаём список фильмов для голосования
    films_list = list(film_suggestions)
    film_suggestions.clear()  # Очищаем список после начала голосования

    # Отправляем голосование (poll)
    await bot.send_poll(
        chat_id=message.chat.id,
        question="Какой фильм будем смотреть?",
        options=films_list,
        is_anonymous=False,  # Делаем голосование открытым
        allows_multiple_answers=True
    )

    await message.answer("Голосование запущено! 🎬")

@dp.message(Command("оценка"))
async def rating_poll(message: Message):
    poll_message = await bot.send_poll(
        chat_id=chat_id,
        question='Оцените фильм от 1 до 10!',
        options=[str(i) for i in range(1, 11)],
        is_anonymous=False,
        allows_multiple_answers=False
    )

    global poll_id, poll_results
    poll_id = poll_message.poll.id
    poll_results = {str(i): 0 for i in range(1, 11)}

    await asyncio.sleep(3600)

    await calculate_rating()

aiocron.crontab("0 19 * * 5", func=scheduled_poll)

# Запуск бота
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())  # Запускаем бота
    loop.run_forever()
    #asyncio.run(main())
