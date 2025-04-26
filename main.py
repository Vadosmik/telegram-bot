import os
import time
import psycopg2
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot import types

# Загрузка переменных окружения
load_dotenv()

# Инициализация Flask и бота
app = Flask(__name__)
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS votes (
    id SERIAL PRIMARY KEY,
    username TEXT,
    user_id BIGINT UNIQUE,
    voted_for TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE,
    value TEXT
);
""")
conn.commit()

# Настройки админов
ADMIN_ID = int(os.getenv("ADMIN_ID"))
maks_id = int(os.getenv("maks_id"))
vadim_id = int(os.getenv("vadim_id"))

# Состояния
user_state = {}
answer_targets = {}
contest_status = False
votes_status = False

# Установка webhook
bot.remove_webhook()
time.sleep(1)
bot.set_webhook(url=WEBHOOK_URL)

# --- Flask роут для вебхука ---
@app.route('/', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '!', 200

# --- Хэндлеры команд ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    chat_id = message.chat.id
    if chat_id in [ADMIN_ID, vadim_id]:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = [
            '📊 Статистика', '🧹 Очистить статистику',
            '🏁 Вкл/выкл конкурс', '🗳️ Вкл/выкл голосование',
            '🔢 Кол-во участников', '🎨 Участвовать', '🗳️ Голосовать'
        ]
        markup.add(*[types.KeyboardButton(btn) for btn in buttons])
        bot.send_message(chat_id, "Привет, админ! 👑", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        if contest_status:
            markup.add(types.InlineKeyboardButton('🎨 Участвовать в конкурсе', callback_data='add'))
        if votes_status:
            markup.add(types.InlineKeyboardButton('🗳️ Проголосовать за участников', callback_data='vote'))
        if not contest_status and not votes_status:
            markup.add(types.InlineKeyboardButton('👋 привет', callback_data='hi'))
        bot.send_message(chat_id, "Приветствуем в боте конкурсов канала Ally Books! 📚✨", reply_markup=markup)

@bot.message_handler(commands=['me'])
def send_my_id(message):
    user = message.from_user
    bot.send_message(
        message.chat.id,
        f"👤 Имя: {user.first_name}\n"
        f"🔹 Username: @{user.username or 'без username'}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"💬 Chat ID: {message.chat.id}"
    )

@bot.message_handler(commands=['call_max'])
def call_max(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👋 привет", callback_data='hi'))
    markup.add(types.InlineKeyboardButton("XXX", callback_data='xxx'))
    bot.send_message(message.chat.id,
        "📢 Эта функция создана для шуток над @una_max. Выбери сообщение:",
        reply_markup=markup
    )

@bot.message_handler(commands=['offer'])
def offer_message(message):
    user_state[message.chat.id] = 'awaiting_offer'
    bot.send_message(message.chat.id, "Введите текст, который хотите добавить.")

@bot.message_handler(commands=['status'])
def vote_status(message):
    cursor.execute("SELECT voted_for, COUNT(*) FROM votes GROUP BY voted_for ORDER BY COUNT(*) DESC LIMIT 5")
    top = cursor.fetchall()
    if not top:
        bot.send_message(message.chat.id, "Пока никто не проголосовал.")
    else:
        stats = "Top 5 голосов:\n" + "\n".join(f"заявка №{vote}: {count} голосов" for vote, count in top)
        bot.send_message(message.chat.id, stats)

# --- Обработка текстовых сообщений от админа ---
@bot.message_handler(func=lambda message: message.chat.id == ADMIN_ID and message.text)
def admin_panel(message):
    global contest_status, votes_status
    text = message.text
    if text == '📊 Статистика':
        vote_status(message)
    elif text == '🧹 Очистить статистику':
        cursor.execute("DELETE FROM votes")
        conn.commit()
        bot.send_message(message.chat.id, "Статистика очищена.")
    elif text == '🏁 Вкл/выкл конкурс':
        contest_status = not contest_status
        bot.send_message(message.chat.id, f"Конкурс {'включён' if contest_status else 'выключен'}.")
    elif text == '🗳️ Вкл/выкл голосование':
        votes_status = not votes_status
        bot.send_message(message.chat.id, f"Голосование {'включено' if votes_status else 'выключено'}.")
    elif text == '🔢 Кол-во участников':
        cursor.execute("SELECT COUNT(DISTINCT voted_for) FROM votes")
        count = cursor.fetchone()[0]
        bot.send_message(message.chat.id, f"Количество участников: {count}")
    elif text == '🎨 Участвовать':
        start_handler(message)
    elif text == '🗳️ Голосовать':
        start_handler(message)

# --- Хэндлеры колбеков ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data

    if data == 'start':
        start_handler(call.message)
    elif data == 'vote':
        user_state[chat_id] = 'awaiting_vote'
        bot.send_message(chat_id, "Отправьте номер понравившейся работы.")
    elif data == 'add':
        user_state[chat_id] = 'awaiting_agree'
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Согласен", callback_data='agree'))
        bot.send_message(chat_id, "Отправьте проект для участия.", reply_markup=markup)
    elif data == 'agree':
        user_state[chat_id] = 'awaiting_project'
        bot.send_message(chat_id, "📌 Пришлите сам проект.")
    elif data == 'hi':
        bot.send_message(maks_id, "Приветик")
    elif data == 'xxx':
        bot.send_message(maks_id, "я тебя трахну!!")
    elif data == 'clear':
        cursor.execute("DELETE FROM votes")
        conn.commit()
        bot.send_message(chat_id, "Все голоса удалены.")
    elif data.startswith('approve_'):
        target_id = int(data.split('_')[1])
        bot.send_message(target_id, "✅ Ваша заявка принята!")
        bot.send_message(ADMIN_ID, "✅ Заявка подтверждена!")
    elif data.startswith('text_'):
        target_id = int(data.split('_')[1])
        answer_targets[user_id] = target_id
        user_state[user_id] = 'awaiting_text_for_answer'
        bot.send_message(user_id, "Введите текст для отправки пользователю.")

# --- Обработка всех сообщений ---
@bot.message_handler(func=lambda message: True)
def all_messages(message):
    chat_id = message.chat.id
    state = user_state.get(chat_id)

    if state == 'awaiting_offer':
        bot.send_message(ADMIN_ID, f"Новое предложение: {message.text}")
        user_state.pop(chat_id)
        bot.send_message(chat_id, "✅ Ваше предложение отправлено.")
    elif state == 'awaiting_project':
        bot.send_message(ADMIN_ID, f"Новый проект от {chat_id}:")
        bot.forward_message(ADMIN_ID, chat_id, message.message_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{chat_id}"))
        bot.send_message(ADMIN_ID, "Выберите действие:", reply_markup=markup)
        user_state.pop(chat_id)
    elif state == 'awaiting_vote':
        try:
            vote = int(message.text)
            cursor.execute("INSERT INTO votes (username, user_id, voted_for) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET voted_for = EXCLUDED.voted_for",
                           (message.from_user.username, message.from_user.id, vote))
            conn.commit()
            bot.send_message(chat_id, "✅ Ваш голос принят!")
            user_state.pop(chat_id)
        except ValueError:
            bot.send_message(chat_id, "❗ Введите только номер заявки.")
    elif state == 'awaiting_text_for_answer':
        target_id = answer_targets.pop(chat_id, None)
        if target_id:
            bot.send_message(target_id, message.text)
            bot.send_message(chat_id, "✅ Текст отправлен пользователю.")
            user_state.pop(chat_id)

## =============================      ============================= ##

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def message_handler(message):
  chat_id = message.chat.id
  user_id = vadim_id
  state = user_state.get(chat_id)

  if state == 'awaiting_offer':
    bot.send_message(chat_id, "❗ функция проходит проверку.")
    bot.send_message(user_id, message.text)

  elif state == 'awaiting_number_of_contestants':
    max_vote = int(message.text)
    set_max_vote(max_vote)
    bot.send_message(chat_id, f"Количество участников: {max_vote}")

  elif state == 'awaiting_project':
    if chat_id not in user_data:
      user_data[chat_id] = {}

    if message.content_type == 'text' and message.text.startswith("http"):
      user_data[chat_id]['project'] = message.text
      user_data[chat_id]['type'] = 'link'
      bot.send_message(chat_id, "✅ Ссылка получена!\n📸 Теперь пришли скриншот или видео из монтажной/рабочей программы")
      user_state[chat_id] = 'awaiting_screenshot'

    elif message.content_type in ['photo', 'video', 'document']:
      if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
      elif message.content_type == 'video':
        file_id = message.video.file_id
      else:
        file_id = message.document.file_id
      user_data[chat_id]['project'] = file_id
      user_data[chat_id]['type'] = message.content_type
      bot.send_message(chat_id, "✅ Проект получен!\n📸 Теперь пришли скриншот или видео из монтажной/рабочей программы")
      user_state[chat_id] = 'awaiting_screenshot'
    else:
      bot.send_message(chat_id, "❗ Пожалуйста, пришли ссылку, файл, фото или видео.")

  elif state == 'awaiting_screenshot':
    if message.content_type in ['photo', 'video', 'document']:
      if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
      elif message.content_type == 'video':
        file_id = message.video.file_id
      else:
        file_id = message.document.file_id

      user_data[chat_id]['screenshot'] = file_id
      user_data[chat_id]['screenshot_type'] = message.content_type

      bot.send_message(chat_id, "📩 Спасибо! Ваша заявка отправлена на проверку. ⏳\n(После отправки нужно подождать подтверждения от администратора)")

      # Отправка админу
      user = message.from_user
      if user.username:
        display_name = f"@{user.username}"
      else:
        display_name = f"{user.first_name} (id: {user.id})"
      

      approve_markup = types.InlineKeyboardMarkup()
      btn1 = types.InlineKeyboardButton("Написать", callback_data=f"text_{chat_id}")
      btn2 = types.InlineKeyboardButton("✅ Затвердить заявку", callback_data=f"approve_{chat_id}")
      approve_markup.add(btn1)
      approve_markup.add(btn2)

      bot.send_message(ADMIN_ID, f"📥 Новая заявка от участника: {display_name}")

      # Проект
      if user_data[chat_id]['type'] == 'link':
        bot.send_message(ADMIN_ID, f"🔗 Проект: {user_data[chat_id]['project']}")
      else:
        bot.send_message(ADMIN_ID, "📌 Проект:")
        p_type = user_data[chat_id]['type']
        p_id = user_data[chat_id]['project']
        if p_type == 'photo':
          bot.send_photo(ADMIN_ID, p_id)
        elif p_type == 'video':
          bot.send_video(ADMIN_ID, p_id)
        elif p_type == 'document':
          bot.send_document(ADMIN_ID, p_id)

      # Скриншот
      bot.send_message(ADMIN_ID, "🖼️ Скриншот:")
      s_type = user_data[chat_id]['screenshot_type']
      s_id = user_data[chat_id]['screenshot']
      if s_type == 'photo':
        bot.send_photo(ADMIN_ID, s_id, reply_markup=approve_markup)
      elif s_type == 'video':
        bot.send_video(ADMIN_ID, s_id, reply_markup=approve_markup)
      elif s_type == 'document':
        bot.send_document(ADMIN_ID, s_id, reply_markup=approve_markup)

      # Очистка
      user_state.pop(chat_id, None)
      user_data.pop(chat_id, None)
    else:
      bot.send_message(chat_id, "❗ Пожалуйста, пришли скриншот или видео в виде фото, видео или документа.")
  
  elif state == 'awaiting_vote':
    user_id = chat_id
    user_vote = message.text.strip()
    username = message.from_user.username or "без username"
    max_vote = get_max_vote()

    if not user_vote.isdigit() or not (1 <= int(user_vote) <= int(max_vote)):
      bot.send_message(chat_id, f"Пожалуйста, выберите одну из опций от 1 до {max_vote}.")
      return

    # sprawdzamy czy użytkownik już głosował
    cursor.execute("SELECT * FROM votes WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if result:
      markup = types.InlineKeyboardMarkup()
      btn1 = types.InlineKeyboardButton("Изменить голос", callback_data='change_vote')
      btn2 = types.InlineKeyboardButton("Удалить голос", callback_data='remove_vote')
      btn3 = types.InlineKeyboardButton("🔙 Вернуться в начало", callback_data='start')
      markup.add(btn1, btn2)
      markup.add(btn3)
      bot.send_message(chat_id, "Вы уже проголосовали!\nНо вы можете изменить или удалить ваш голос.", reply_markup=markup)
      return

    # jeśli nie głosował – zapisujemy do bazy
    cursor.execute(
      "INSERT INTO votes (username, user_id, voted_for) VALUES (%s, %s, %s)",
      (username, user_id, user_vote)
    )
    conn.commit()

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Изменить голос", callback_data='change_vote')
    btn2 = types.InlineKeyboardButton("Удалить голос", callback_data='remove_vote')
    btn3 = types.InlineKeyboardButton("🔙 Вернуться в начало", callback_data='start')
    markup.add(btn1, btn2)
    markup.add(btn3)

    bot.send_message(chat_id, f"✅ Голос за работу №{user_vote} принят! Спасибо за участие! 🗳️", reply_markup=markup)
    user_state.pop(chat_id, None)

  elif state == 'awaiting_text_for_answer':
    admin_id = message.from_user.id
    if message.content_type == 'text':
      user_chat_id = answer_targets.get(admin_id)
      if user_chat_id:
        markup = types.InlineKeyboardMarkup()

        if user_chat_id == ADMIN_ID:
          btn1 = types.InlineKeyboardButton("✉️ Написать", callback_data=f"text_{chat_id}")
          markup.add(btn1)
        else:
          btn1 = types.InlineKeyboardButton("✉️ Написать", callback_data=f"text_{chat_id}")
          btn2 = types.InlineKeyboardButton("🔄 Повторно выслать проект", callback_data='agree')
          markup.add(btn1)
          markup.add(btn2)

        # Получаем имя пользователя, если есть username, иначе имя
        sender = message.from_user.username
        if sender:
          sender_info = f"👤 @{sender}"
        else:
          sender_info = f"👤 {message.from_user.first_name}"

        
        if user_chat_id == ADMIN_ID:
          bot.send_message(user_chat_id, f"{sender_info}:\n{message.text}", reply_markup=markup)
          bot.send_message(admin_id, "Сообщение отправлено ✅")
        else:
          bot.send_message(user_chat_id, message.text, reply_markup=markup)
          bot.send_message(admin_id, "Сообщение отправлено ✅")

      else:
        bot.send_message(admin_id, "Ошибка: пользователь не найден.")
    else:
      bot.send_message(admin_id, "Пожалуйста, отправьте обычный текст.")

    user_state.pop(admin_id, None)
    answer_targets.pop(admin_id, None)

def get_max_vote():
    cursor.execute("SELECT value FROM settings WHERE key = %s", ('max_vote',))
    result = cursor.fetchone()
    return int(result[0]) if result else 2  # Domyślnie 2 głosy, jeśli brak w bazie

def set_max_vote(value):
    cursor.execute("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s", ('max_vote', value, value))
    conn.commit()

@app.route('/', methods=['GET'])
def index():
  return 'Bot is running!', 200

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))