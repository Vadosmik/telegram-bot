import telebot
import sqlite3
from telebot import types

# Tworzenie bota z tokenem
bot = telebot.TeleBot('7670789690:AAGpJUW459GtpsTj7aEeWrhooE-_ggLUn-k')

# Słownik do przechowywania danych tymczasowych dla użytkowników
user_data = {}

# Obsługa komendy '/start'
@bot.message_handler(commands=['start'])
def start_handler(message):
    conn = sqlite3.connect('dateBD.db')
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            user_id INTEGER
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

    user_data[message.chat.id] = {"name": "❌none❌", "description": "❌none❌", "date": "❌none❌"}
    send_start_message(message.chat.id)

# Funkcja do wyświetlania startowej wiadomości
def send_start_message(chat_id, message_id=None):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Dodanie wydarzenia', callback_data='add')
    btn2 = types.InlineKeyboardButton('Wyświetlenie wszystkich wydarzeń', callback_data='list')
    btn3 = types.InlineKeyboardButton('Usunięcie wydarzenia', callback_data='delete')
    
    markup.add(btn1, btn2)
    markup.add(btn3)
    
    if message_id:
        bot.edit_message_text('Witaj! Wybierz jedną z opcji:', chat_id=chat_id, message_id=message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, 'Witaj! Wybierz jedną z opcji:', reply_markup=markup)

# Obsługa zdarzeń klawiatury Inline
@bot.callback_query_handler(func=lambda callback: True)
def callback_handler(callback):
    chat_id = callback.message.chat.id

    if callback.data == 'add':
        # Inicjalizacja danych użytkownika
        user_data[chat_id] = {"name": "❌none❌", "description": "❌none❌", "date": "❌none❌"}
        show_add_menu(chat_id, callback.message.message_id)
    elif callback.data == 'change_name':
        msg = bot.send_message(chat_id, "Wpisz nazwę wydarzenia:")
        bot.register_next_step_handler(msg, set_name)
    elif callback.data == 'change_description':
        msg = bot.send_message(chat_id, "Wpisz opis wydarzenia:")
        bot.register_next_step_handler(msg, set_description)
    elif callback.data == 'change_date':
        msg = bot.send_message(chat_id, "Wpisz datę wydarzenia (format YYYY-MM-DD):")
        bot.register_next_step_handler(msg, set_date)
    elif callback.data == 'add_event_to_date':
        add_event_to_db(chat_id, callback.message.message_id)
    elif callback.data == 'list':
        list_events(chat_id, callback.message.message_id)
    elif callback.data == 'delete':
        delete_events(chat_id, callback.message.message_id)
    elif callback.data == 'back':
        send_start_message(chat_id, callback.message.message_id)

# Funkcja wyświetlająca menu dodawania wydarzenia
def show_add_menu(chat_id, previous_message_id=None):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('<< wróć', callback_data='back')
    btn2 = types.InlineKeyboardButton('Zmień nazwę', callback_data='change_name')
    btn3 = types.InlineKeyboardButton('Zmień opis', callback_data='change_description')
    btn4 = types.InlineKeyboardButton('Zmień datę', callback_data='change_date')
    btn5 = types.InlineKeyboardButton('Dodaj wydarzenie', callback_data='add_event_to_date')
    markup.add(btn2, btn3, btn4)
    markup.add(btn5)
    markup.add(btn1)

    # Tworzenie nowej wiadomości
    new_message = bot.send_message(
        chat_id,
        f"Nazwa: {user_data[chat_id]['name']}\nOpis: {user_data[chat_id]['description']}\nData ukończenia: {user_data[chat_id]['date']}",
        reply_markup=markup
    )

    # Usuwanie poprzedniej wiadomości, jeśli istnieje
    if previous_message_id:
        bot.delete_message(chat_id, previous_message_id)

    # Przechowywanie ID nowej wiadomości w aplikacji
    user_data[chat_id]['main_message_id'] = new_message.message_id

# Funkcje ustawiania danych wydarzenia
def set_name(message):
    chat_id = message.chat.id
    user_data[chat_id]['name'] = message.text
    
    # Usuwanie poprzednich dwóch wiadomości
    bot.delete_message(chat_id, message.message_id)
    bot.delete_message(chat_id, message.message_id - 1)
    
    # Wyświetlanie zaktualizowanego menu
    show_add_menu(chat_id, message.message_id - 2)

def set_description(message):
    chat_id = message.chat.id
    user_data[chat_id]['description'] = message.text
    
    # Usuwanie poprzednich dwóch wiadomości
    bot.delete_message(chat_id, message.message_id)
    bot.delete_message(chat_id, message.message_id - 1)
    
    # Wyświetlanie zaktualizowanego menu
    show_add_menu(chat_id, message.message_id - 2)

def set_date(message):
    chat_id = message.chat.id
    user_data[chat_id]['date'] = message.text
    
    # Usuwanie poprzednich dwóch wiadomości
    bot.delete_message(chat_id, message.message_id)
    bot.delete_message(chat_id, message.message_id - 1)
    
    # Wyświetlanie zaktualizowanego menu
    show_add_menu(chat_id, message.message_id - 2)

# Funkcja dodająca wydarzenie do bazy danych
def add_event_to_db(chat_id, message_id):
    data = user_data[chat_id]

    if "❌none❌" in data.values():
        bot.send_message(chat_id, "Nie wszystkie pola zostały uzupełnione!")
        return

    conn = sqlite3.connect('dateBD.db')
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO task (name, description, due_date, completed, user_id) VALUES (?, ?, ?, ?, ?)",
        (data['name'], data['description'], data['date'], 0, chat_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('<< wróć', callback_data='back')
    markup.add(btn1)

    bot.edit_message_text("Wydarzenie zostało dodane!", chat_id=chat_id, message_id=message_id, reply_markup=markup)

# Funkcja wyświetlająca listę wydarzeń
def list_events(chat_id, message_id):
    conn = sqlite3.connect('dateBD.db')
    cur = conn.cursor()
    cur.execute("SELECT name, description, due_date, completed FROM task WHERE user_id = ?", (chat_id,))
    tasks = cur.fetchall()
    cur.close()
    conn.close()

    if tasks:
        task_list = "Lista wydarzeń:\n"
        for i, (name, description, due_date, completed) in enumerate(tasks, start=1):
            status = "✔️" if completed else "❌"
            task_list += f"{i}. {name} - {description or 'Brak opisu'} - {due_date or 'Brak daty'} - {status}\n"
    else:
        task_list = "Nie masz jeszcze żadnych wydarzeń."

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('zmień status', callback_data='change_status')
    btn2 = types.InlineKeyboardButton('<< wróć', callback_data='back')
    markup.add(btn1, btn2)

    bot.edit_message_text(task_list, chat_id=chat_id, message_id=message_id, reply_markup=markup)

def delete_events(chat_id, message_id):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('<< wróć', callback_data='back')
    markup.add(btn1)

    bot.edit_message_text('hello', chat_id=chat_id, message_id=message_id, reply_markup=markup)

# Start bota
bot.polling(non_stop=True)