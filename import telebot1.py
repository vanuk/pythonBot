import base64
import telebot
import mysql.connector
import requests
from telebot import types
from datetime import datetime
import os
import requests
import zipfile
import shutil  # Додали бібліотеку shutil для роботи з архівами
# Замість 'YOUR_API_TOKEN' вставте ваш API токен бота, який ви отримали від @BotFather.
TOKEN = '6568927019:AAH9cVz8nTewEZ59j0bdnNZMd_LdC77ERL4'

GITHUB_TOKEN = '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'
# Налаштуйте з'єднання з MySQL-сервером
db_config = {
    "host": "127.0.0.1",    # Адреса сервера MySQL
    "user": "root",    # Ваше ім'я користувача MySQL
    "password": "visspan01",    # Ваш пароль MySQL
    "database": "tg_bot_books"    # Назва вашої бази даних MySQL
}

# Підключення до сервера MySQL
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

bot = telebot.TeleBot(TOKEN)

# Створення клавіатури з меню
menu_markup = types.ReplyKeyboardMarkup(row_width=3)
# Додайте кнопки до меню, наприклад:
item1 = types.KeyboardButton('Завантаження книги 📥')
item2 = types.KeyboardButton('Пошук книги по жанру 🔍')
item3 = types.KeyboardButton('Пошук книги за назвою 🔍')
menu_markup.add(item1, item2, item3)

# Додайте список доступних жанрів
available_genres = ['Фантастика', 'Драма', 'Пригоди', 'Кримінал', 'Фентезі']

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Ласкаво просимо! Виберіть опцію з меню:", reply_markup=menu_markup)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    if message.text == 'Завантаження книги 📥':
        bot.reply_to(message, "Виберіть жанр книги:", reply_markup=create_genre_keyboard())
        bot.register_next_step_handler(message, get_genre)
    elif message.text == 'Пошук книги по жанру 🔍':
        bot.reply_to(message, "Виберіть жанр книги:", reply_markup=create_genre_keyboard())
        bot.register_next_step_handler(message, find_books_by_genre)
    elif message.text == 'Пошук книги за назвою 🔍':
       chat_id = message.chat.id  # Отримуємо chat_id з отриманого повідомлення
       bot.send_message(chat_id, 'Введіть назву книги:')
       bot.register_next_step_handler(message, find_books_by_name)
    else:
        bot.reply_to(message, "Я не розумію вашого вибору. Виберіть опцію з меню.")

def create_genre_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    row1 = [types.KeyboardButton(genre) for genre in available_genres[:len(available_genres)//2]]
    row2 = [types.KeyboardButton(genre) for genre in available_genres[len(available_genres)//2:]]
    markup.add(*row1, *row2)
    return markup

def get_genre(message):
    genre = message.text
    user_id = message.from_user.id
    user_name = message.from_user.username
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    bot.reply_to(message, "Введіть назву книги:")
    bot.register_next_step_handler(message, get_book_name, user_id, user_name, current_time, genre)
    
def get_book_name(message, user_id, user_name, current_time, genre):
    book_name = message.text
    
    # Запитайте автора та короткий опис книги
    bot.reply_to(message, "Введіть автора книги в форматі Прізвище та перші букви ініціалів:")
    bot.register_next_step_handler(message, get_book_author, user_id, user_name, current_time, genre, book_name)

def get_book_author(message, user_id, user_name, current_time, genre, book_name):
    book_author = message.text
    
    # Запитайте короткий опис книги
    bot.reply_to(message, "Введіть короткий опис книги:")
    bot.register_next_step_handler(message, get_book_description, user_id, user_name, current_time, genre, book_name, book_author)

def get_book_description(message, user_id, user_name, current_time, genre, book_name, book_author):
    book_description = message.text
    
    bot.reply_to(message, "Завантажте файл книги:")
    bot.register_next_step_handler(message, save_file_to_db, user_id, user_name, current_time, genre, book_name, book_author, book_description)


def upload_to_github(file_path, file_content):
    try:
        url = f"https://api.github.com/repos/vanuk/tgbotbook/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}"
        }
        content_base64 = base64.b64encode(file_content).decode()

        data = {
            "message": f"Add {file_path}",
            "content": content_base64
        }
        
        response = requests.put(url, headers=headers, json=data)

        if response.status_code == 201:
            return response.json()["content"]["download_url"]
        else:
            print(f"GitHub API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"GitHub Upload Error: {e}")
        return None

# Функція для створення архіву, завантаження його на GitHub та збереження посилання в базі даних
def save_file_to_db(message, user_id, user_name, current_time, genre, book_name, book_author, book_description):
    if message.document:
        if message.document.mime_type == 'application/pdf':
            file_id = message.document.file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            # Отримання розширення файлу
            file_extension = message.document.file_name.split('.')[-1]
            
            # Ім'я файлу архіву
            zip_file_name = f"{book_name}.zip"

            # Створення архіву з завантаженим PDF
            with zipfile.ZipFile(zip_file_name, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr(f"{book_name}.pdf", downloaded_file)

            # Виклик функції для завантаження архіву на GitHub
            file_link = upload_to_github(f"save/{zip_file_name}", open(zip_file_name, 'rb').read())

            # Видалення архіву
            os.remove(zip_file_name)

            if file_link:
                # Вставка посилання на файл в базу даних MySQL
                insert_query = "INSERT INTO saved_data (user_id, user_name, genre, name, description, author, file_name, time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                data = (user_id, user_name, genre, book_name, book_description, book_author, file_link, current_time)

                try:
                    cursor.execute(insert_query, data)
                    conn.commit()
                    bot.reply_to(message, f"Книгу '{book_name}' з жанром '{genre}' збережено в базі даних. Посилання на файл: {file_link}")
                except mysql.connector.Error as err:
                    bot.reply_to(message, f"Помилка збереження книги: {err}")
            else:
                bot.reply_to(message, "Помилка завантаження файлу на GitHub.")
        else:
            bot.reply_to(message, "Формат файлу повинен бути PDF.")
    else:
        bot.reply_to(message, "Це не є файлом книги. Завантажте книгу в форматі файлу.")

    # Після завершення завантаження файлу, виводимо головне меню
    bot.send_message(user_id, "Виберіть опцію з меню:", reply_markup=menu_markup)


def find_books_by_genre(message):
    genre = message.text

    # Виконайте запит до бази даних для отримання книг з вибраного жанру
    search_query = "SELECT * FROM saved_data WHERE genre = %s"
    cursor.execute(search_query, (genre,))
    books = cursor.fetchall()

    if books:
        response = "Результати пошуку:\n"
        for book in books:
            response += f"Жанр: {book[3]}\nНазва: {book[4]}\nЗавантажена о {book[6]}\n\n"
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "Книг з цим жанром не знайдено.")

    # Після отримання результатів пошуку виводимо головне меню
    bot.send_message(message.chat.id, "Виберіть опцію з меню:", reply_markup=menu_markup)

def find_books_by_name(message):
    book_name = message.text
    
    search_query = "SELECT * FROM saved_data WHERE name = %s"
    
    cursor.execute(search_query, (book_name,))
    books = cursor.fetchall()
    
    if books:
        response = "Результат пошуку: \n"
        for book in books:
            response += f"Назва книги: {book[4]}\n Жанр: {book[3]}\nАвтор: {book[6]}\nОпис: {book[5]}\nЗавантажена о {book[7]}\n\n"
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "Книги з такою назвою не знайдено.")

    # Після отримання результатів пошуку виводимо головне меню
    bot.send_message(message.chat.id, "Виберіть опцію з меню:", reply_markup=menu_markup)

if __name__ == '__main__':
    bot.polling()