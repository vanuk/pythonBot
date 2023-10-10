import base64
import telebot
import mysql.connector
import requests
from telebot import types
from datetime import datetime
import os
import requests

TOKEN = '6568927019:AAH9cVz8nTewEZ59j0bdnNZMd_LdC77ERL4'

GITHUB_TOKEN = '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'
# Налаштуйте з'єднання з MySQL-сервером
db_config = {
    "host": "127.0.0.1",    
    "user": "root",    
    "password": "visspan01",   
    "database": "tg_bot_books"    
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

bot = telebot.TeleBot(TOKEN)

# Створення клавіатури з меню
menu_markup = types.ReplyKeyboardMarkup(row_width=3)

item1 = types.KeyboardButton('Завантаження книги 📥')
item2 = types.KeyboardButton('Пошук книги по жанру 🔍')
item3 = types.KeyboardButton('Пошук книги за назвою 🔍')
menu_markup.add(item1, item2, item3)

# список доступних жанрів
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

def create_cancel_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item = types.KeyboardButton("Скасувати")
    markup.add(item)
    return markup

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
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item1 = types.KeyboardButton("скасувати")
    markup.add( item1)
    
    bot.reply_to(message, "Введіть назву книги:", reply_markup=markup)
    bot.register_next_step_handler(message, get_book_name, user_id, user_name, current_time, genre)

def get_book_name(message, user_id, user_name, current_time, genre):
    book_name = message.text
    
    if book_name.lower() == "скасувати":
        bot.send_message(message.chat.id, "Виберіть опцію з меню:", reply_markup=menu_markup)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item3 = types.KeyboardButton("скасувати")
    markup.add(item3) 
    
    bot.reply_to(message, "Введіть автора книги в форматі Прізвище та перші букви ініціалів:", reply_markup=markup)
    bot.register_next_step_handler(message, get_book_author, user_id, user_name, current_time, genre, book_name)

def get_book_author(message, user_id, user_name, current_time, genre, book_name):
    book_author = message.text
    
    if book_author.lower() == "скасувати":
        bot.send_message(message.chat.id, "Виберіть опцію з меню:", reply_markup=menu_markup)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item1 = types.KeyboardButton("Ввести опис книги")
    item2 = types.KeyboardButton("Пропустити введення опису")
    item3 = types.KeyboardButton("скасувати")
    
    markup.add(item1, item2, item3)  
    
    bot.send_message(message.chat.id, "Введіть опис книги або пропустіть цей крок:", reply_markup=markup)
    bot.register_next_step_handler(message, get_book_description, user_id, user_name, current_time, genre, book_name, book_author)

def get_book_description(message, user_id, user_name, current_time, genre, book_name, book_author):
    book_description = message.text
    if book_description.lower() == "скасувати":
        bot.send_message(message.chat.id, "Виберіть опцію з меню:", reply_markup=menu_markup)
        return

    if book_description.lower() == "пропустити введення опису":
        description = None
    else:
        description = book_description

    bot.reply_to(message, "Завантажте файл книги:")
    bot.register_next_step_handler(message, save_file_to_db, user_id, user_name, current_time, genre, book_name, book_author, book_description)

def save_file_to_db(message, user_id, user_name, current_time, genre, book_name, book_author, book_description):
    if message.document:
        if message.document.mime_type == 'application/pdf':
            file_id = message.document.file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            # Отримання розширення файлу
            file_extension = message.document.file_name.split('.')[-1]
            
            # Створення шляху для файлу на GitHub
            github_file_path = f"{'save'}/{book_name}.{file_extension}"

            # Виклик функції для завантаження файлу на GitHub
            file_link = upload_to_github(github_file_path, downloaded_file)

            if file_link:
                # Вставка посилання на файл в базу даних MySQL
                insert_query = "INSERT INTO saved_data (user_id, user_name, genre, name, description, author, link, time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
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

    bot.send_message(user_id, "Виберіть опцію з меню:", reply_markup=menu_markup)

def upload_to_github(file_path, downloaded_file):
    try:
        url = f"https://api.github.com/repos/vanuk/tgbotbook/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}"
        }
        content_base64 = base64.b64encode(downloaded_file).decode()

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
    try:
        url = f"https://api.github.com/repos/vanuk/tgbotbook.git/contents/{book_name}/{file_path}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}"
        }
        data = {
            "message": f"Add {book_name}",
            "content": open(file_path, 'rb').read().encode('base64')
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

def find_books_by_genre(message):
    genre = message.text

    search_query = "SELECT * FROM saved_data WHERE genre = %s"
    cursor.execute(search_query, (genre,))
    books = cursor.fetchall()

    if books:
        response = "Результати пошуку:\n"
        for book in books:
            response += f"Жанр книги: {book[3]}\nНазва книги: {book[4]}\nАвтор книги: {book[6]}\nОпис книги: {book[7]}\nПосилання на завантаження книги: {book[9]}\n"
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "Книг з цим жанром не знайдено.")

    bot.send_message(message.chat.id, "Виберіть опцію з меню:", reply_markup=menu_markup)

def find_books_by_name(message):
    book_name = message.text
    
    search_query = "SELECT * FROM saved_data WHERE name = %s"
    
    cursor.execute(search_query, (book_name,))
    books = cursor.fetchall()
    
    if books:
        response = "Результат пошуку: \n"
        for book in books:
             response += f"Жанр книги: {book[3]}\nНазва книги: {book[4]}\nАвтор книги: {book[6]}\nОпис книги: {book[7]}\nПосилання на завантаження книги: {book[9]}\n"
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "Книги з такою назвою не знайдено.")

    bot.send_message(message.chat.id, "Виберіть опцію з меню:", reply_markup=menu_markup)

if __name__ == '__main__':
    bot.polling()  