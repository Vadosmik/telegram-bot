import time
import telebot
import os
import psycopg2
from telebot import types
from telebot.types import ReplyKeyboardMarkup
from collections import Counter
from dotenv import load_dotenv
from flask import Flask, request

load_dotenv()
app = Flask(__name__)

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
maks_id = int(os.getenv("maks_id"))
vadim_id = int(os.getenv("vadim_id"))

bot = telebot.TeleBot(TOKEN)

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

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
bot.remove_webhook()
time.sleep(1)
bot.set_webhook(url=WEBHOOK_URL)

user_state = {}
user_data = {}

contest_status = False
votes_status = False

answer_targets = {}
max_vote = 2

@app.route('/', methods=['POST'])
def webhook():
  json_str = request.get_data().decode('UTF-8')
  update = telebot.types.Update.de_json(json_str)
  bot.process_new_updates([update])
  return '!', 200

@bot.message_handler(commands=['start'])
def start_handler(message):
  chat_id = message.chat.id

  if chat_id == ADMIN_ID or chat_id == vadim_id:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False, row_width=2)

    admin_buttons = [
      types.KeyboardButton('📊 Статистика'),
      types.KeyboardButton('🧹 Очистить статистику'),
      types.KeyboardButton('🏁 Вкл/выкл конкурс'),
      types.KeyboardButton('🗳️ Вкл/выкл голосование'),
      types.KeyboardButton('🔢 Кол-во участников'),
      types.KeyboardButton('🎨 Участвовать'),
      types.KeyboardButton('🗳️ Голосовать')
    ]
    
    # Grupowanie przycisków
    markup.add(*admin_buttons[:2])
    markup.add(*admin_buttons[2:4])
    markup.add(admin_buttons[4])
    markup.add(admin_buttons[5], admin_buttons[6])

    bot.send_message(chat_id, "Привет, админ! 👑", reply_markup=markup)
  else:
    markup = types.InlineKeyboardMarkup()

    if contest_status:
      btn1 = types.InlineKeyboardButton('🎨 Участвовать в конкурсе', callback_data='add')
      markup.add(btn1)
    if votes_status:
      btn2 = types.InlineKeyboardButton('🗳️ Проголосовать за участников', callback_data='vote')
      markup.add(btn2)
    if contest_status == False and votes_status == False:
      btn3 = types.InlineKeyboardButton("👋 привет", callback_data='hi')
      markup.add(btn3)

    bot.send_message(chat_id, "Приветствуем в боте конкурсов канала Ally Books! 📚✨", reply_markup=markup)


@bot.message_handler(commands=['me'])
def send_my_id(message):
  user_id = message.from_user.id
  chat_id = message.chat.id
  username = message.from_user.username or "без username"
  name = message.from_user.first_name

  bot.send_message(chat_id,
    f"👤 Имя: {name}\n"
    f"🔹 Username: @{username}\n"
    f"🆔 Telegram ID: {user_id}\n"
    f"💬 Chat ID: {chat_id}")
  
@bot.message_handler(commands=['call_max'])
def send_to_max_mess(message):
  chat_id = message.chat.id

  markup = types.InlineKeyboardMarkup()
  markup.add(types.InlineKeyboardButton("👋 привет", callback_data='hi'))
  markup.add(types.InlineKeyboardButton("XXX", callback_data='xxx'))

  bot.send_message(
    chat_id,
    "📢 Эта функция создана для тех, кто хочет немного пошалить и позлить @una_max. "
    "При нажатии на кнопку ему будет отправлено короткое сообщение.\n\n"
    "🔸 Сейчас доступно только два варианта, но со временем список может расшириться.\n"
    "🔸 В будущем эта функция исчезнет из меню — пользоваться ей придётся вручную.\n"
    "🔸 Предложить своё сообщение можно командой /offer.\n"
    "🔸 Всё абсолютно анонимно — никто не узнает, кто нажал.\n\n"
    "👇 Выбери, что хочешь отправить:",
    reply_markup=markup
  )
  
@bot.message_handler(commands=['offer'])
def send_offer(message):
  chat_id = message.chat.id
  user_state[chat_id] = 'awaiting_offer'
  
  bot.send_message(chat_id, "Введите текст, который хотите добавить.")

@bot.message_handler(commands=['status'])
def send_vote_status(message):
  chat_id = message.chat.id

  cursor.execute("SELECT voted_for, COUNT(*) FROM votes GROUP BY voted_for ORDER BY COUNT(*) DESC LIMIT 5")
  top_votes = cursor.fetchall()

  if not top_votes:
    bot.send_message(chat_id, "Пока никто не проголосовал.")
    return
    
  stats_message = "Top 5 голосов:\n"
  for option, count in top_votes:
    stats_message += f"заявка №{option}: {count} голосов\n"

  bot.send_message(chat_id, stats_message)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
  chat_id = call.message.chat.id
  user_id = call.from_user.id
  global contest_status, votes_status

  actions = {
    'start': lambda: handle_start(call.message),
    'hi': lambda: bot.send_message(MAKS_ID, "приветик"),
    'xxx': lambda: bot.send_message(MAKS_ID, "я тебя трахну!!"),
    'vote_status': lambda: toggle_vote_status(chat_id),
    'contest_status': lambda: toggle_contest_status(chat_id),
    'add': lambda: prompt_agreement(chat_id),
    'agree': lambda: prompt_project_submission(chat_id),
    'vote': lambda: prompt_vote(chat_id),
    'clear': lambda: clear_votes(chat_id),
  }

  for prefix, func in actions.items():
    if call.data.startswith(prefix):
      func()
      return
  
  if call.data.startswith('approve_'):
    user_chat_id = int(call.data.split('_')[1])
    bot.send_message(user_chat_id, "✅ Ваша заявка принята!", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🔙 Вернуться', callback_data='start')))
    bot.send_message(ADMIN_ID, "✅ Заявка подтверждена!")

def toggle_vote_status(chat_id):
  global votes_status
  votes_status = not votes_status
  text = "Голосование началось!" if votes_status else "Голосование закончилось!"
  bot.send_message(chat_id, text)

def toggle_contest_status(chat_id):
  global contest_status
  contest_status = not contest_status
  text = "Конкурс начался!" if contest_status else "Конкурс закончился!"
  bot.send_message(chat_id, text)

def prompt_agreement(chat_id):
  user_state[chat_id] = 'awaiting_agree'
  markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Согласен", callback_data='agree'))
  bot.send_message(chat_id, "Жми 'Согласен' для участия в конкурсе!", reply_markup=markup)

def prompt_project_submission(chat_id):
  user_state[chat_id] = 'awaiting_project'
  bot.send_message(chat_id, "📩 Пришли свой проект!")

def prompt_vote(chat_id):
  user_state[chat_id] = 'awaiting_vote'
  bot.send_message(chat_id, "📊 Отправь номер понравившейся работы!")

def clear_votes(chat_id):
  db_execute("DELETE FROM votes")
  bot.send_message(chat_id, "Все голоса удалены.")

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