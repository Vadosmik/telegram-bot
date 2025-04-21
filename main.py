import telebot
from telebot import types
from collections import Counter

TOKEN = '8070878657:AAHSqNPN6i_scj63kMkIi7Y-M4WC-XIRui0'
bot = telebot.TeleBot(TOKEN)

user_state = {}
user_data = {}
votes = {}
vote_counts = Counter()
ADMIN_ID = 1335534848     # vadim: 1335534848   maks_2: 5639741014

@bot.message_handler(commands=['start'])
def start_handler(message):
  chat_id = message.chat.id

  if chat_id == ADMIN_ID:
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('статистика голосования', callback_data='status')
    btn2 = types.InlineKeyboardButton('очистка статистики голосования', callback_data='clear')
    btn3 = types.InlineKeyboardButton('🗳️ Проголосовать за участников', callback_data='vote')
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    bot.send_message(chat_id, "hello admin!!", reply_markup=markup)
  else:
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('🎨 Участвовать в конкурсе', callback_data='add')
    btn2 = types.InlineKeyboardButton('🗳️ Проголосовать за участников', callback_data='vote')
    markup.add(btn1)
    markup.add(btn2)
    bot.send_message(chat_id, "Приветствуем в боте конкурсов канала Ally books! 📚✨", reply_markup=markup)


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
  
@bot.message_handler(commands=['status'])
def send_vote_status(message):
  chat_id = message.chat.id

  top_votes = vote_counts.most_common(5)
  stats_message = "Top 5 голосов:\n"
    
  for option, count in top_votes:
    stats_message += f"заявка №{option}: {count} голосов\n"
    
  bot.send_message(chat_id, stats_message)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
  chat_id = call.message.chat.id

  if call.data == 'start':
    start_handler(call.message)

  elif call.data == 'status':
    send_vote_status(call.message)
  
  elif call.data == 'clear':
    votes = {}
    vote_counts = Counter()

  elif call.data == 'change_vote':
    chat_id = call.message.chat.id
    bot.send_message(chat_id, "Вы можете выбрать новый вариант для вашего голоса.")

  elif call.data == 'remove_vote':
    chat_id = call.message.chat.id
    user_id = call.message.chat.id
    
    if user_id in votes:
      del votes[user_id]
      bot.send_message(chat_id, "Ваш голос был удален. Вы можете проголосовать снова.")
      vote_counts[votes] -= 1
    else:
      bot.send_message(chat_id, "Вы еще не голосовали.")

  elif call.data == 'add':
    user_state[chat_id] = 'awaiting_agree'
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Согласен", callback_data='agree'))
    bot.send_message(chat_id,
      "Участвуя в конкурсе, ты даёшь согласие на размещение своего проекта в нашем Telegram-канале Ally books📚.\n"
      "Это отличная возможность показать свой талант! 🚀\n\n"
      "Что нужно отправить:\n📌 Сам проект \n📸 Скриншот из монтажной/рабочей программы\n\n"
      "Ждём твою работу — давай удивим всех вместе! ✨",
      reply_markup=markup)

  elif call.data == 'agree':
    user_state[chat_id] = 'awaiting_project'
    bot.send_message(chat_id, "📌 Пожалуйста, пришли сам проект")

  elif call.data == 'vote':
    user_state[chat_id] = 'awaiting_vote'
    bot.send_message(chat_id,
      "Все работы участников уже размещены в нашем канале Ally books📚!\n"
      "Оцени их и выбери свою любимую — нам важно твоё мнение! 💬✨\n\n"
      "Чтобы проголосовать, просто пришли сюда номер работы, которая тебе понравилась больше всего.\n"
      "Всего один шаг — и твой голос может решить судьбу победителя! 🏆")
    
  elif call.data.startswith('approve_'):
    user_chat_id = int(call.data.split('_')[1])
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Вернуться в начало", callback_data='start'))
    bot.send_message(
      user_chat_id,
      "✅ Спасибо! Ваша заявка принята. Удачи в конкурсе! ✨",
      reply_markup=markup
    )
    bot.send_message(
      ADMIN_ID,
      "✅ Заявка подтверждена!"
    )

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def message_handler(message):
  chat_id = message.chat.id
  state = user_state.get(chat_id)

  if state == 'awaiting_project':
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
      approve_markup.add(types.InlineKeyboardButton("✅ Затвердить заявку", callback_data=f"approve_{chat_id}"))

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

    max_vote = 10

    if not user_vote.isdigit() or not (1 <= int(user_vote) <= max_vote):
      bot.send_message(chat_id, f"Пожалуйста, выберите одну из опций от 1 до {max_vote}.")
      return

    if user_id in votes:
      markup = types.InlineKeyboardMarkup()
      btn1 = types.InlineKeyboardButton("Изменить голос", callback_data='change_vote')
      btn2 = types.InlineKeyboardButton("Удалить голос", callback_data='remove_vote')
      btn3 = types.InlineKeyboardButton("🔙 Вернуться в начало", callback_data='start')
      markup.add(btn1, btn2)
      markup.add(btn3)
      bot.send_message(chat_id, "Вы уже проголосовали! Вы можете изменить или удалить ваш голос. Спасибо за участника.", reply_markup=markup)
      return

    votes[user_id] = user_vote
    vote_counts[user_vote] += 1


    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("Изменить голос", callback_data='change_vote')
    btn2 = types.InlineKeyboardButton("Удалить голос", callback_data='remove_vote')
    btn3 = types.InlineKeyboardButton("🔙 Вернуться в начало", callback_data='start')
    markup.add(btn1, btn2)
    markup.add(btn3)
    bot.send_message(chat_id, f"✅ Голос за работу №{message.text} принят! Спасибо за участие! 🗳️", reply_markup=markup)
    user_state.pop(chat_id, None)
    

bot.polling(non_stop=True)