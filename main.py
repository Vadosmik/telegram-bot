import telebot
import os
from telebot import types
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
maks_id = int(os.getenv("maks_id"))
vadim_id = int(os.getenv("vadim_id"))

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

user_state = {}
user_data = {}

contest_status = False
votes_status = False

votes = {}
vote_counts = Counter()

answer_targets = {}

@bot.message_handler(commands=['start'])
def start_handler(message):
  chat_id = message.chat.id

  if chat_id == ADMIN_ID or chat_id == vadim_id:
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('статистика голосования', callback_data='status')
    btn2 = types.InlineKeyboardButton('очистка статистики голосования', callback_data='clear')
    btn3 = types.InlineKeyboardButton('вкл/выкл конкурса', callback_data='contest_status')
    btn4 = types.InlineKeyboardButton('вкл/выкл голосования', callback_data='vote_status')
    btn5 = types.InlineKeyboardButton('🎨 Участвовать в конкурсе', callback_data='add')
    btn6 = types.InlineKeyboardButton('🗳️ Проголосовать за участников', callback_data='vote')
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)
    markup.add(btn5)
    markup.add(btn6)
    bot.send_message(chat_id, "hello admin!!", reply_markup=markup)
  else:
    markup = types.InlineKeyboardMarkup()

    if contest_status:
      btn1 = types.InlineKeyboardButton('🎨 Участвовать в конкурсе', callback_data='add')
      markup.add(btn1)
    if votes_status:
      btn2 = types.InlineKeyboardButton('🗳️ Проголосовать за участников', callback_data='vote')
      markup.add(btn2)
    if contest_status == False & votes_status == False:
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

  top_votes = vote_counts.most_common(5)
  stats_message = "Top 5 голосов:\n"
    
  for option, count in top_votes:
    stats_message += f"заявка №{option}: {count} голосов\n"
    
  bot.send_message(chat_id, stats_message)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
  chat_id = call.message.chat.id
  user_id = call.from_user.id
  global vote_counts, votes, user_state, answer_targets, votes_status, contest_status

  if call.data == 'start':
    start_handler(call.message)

  elif call.data == 'status':
    send_vote_status(call.message)

  elif call.data == 'vote_status':
    votes_status = not votes_status
    if votes_status == True:
      bot.send_message(chat_id, "Голосование началось, максон!!!!!!!!!!")
    else:
      bot.send_message(chat_id, "Голосование закончилось, ок?!!")

  elif call.data == 'contest_status':
    contest_status = not contest_status
    if contest_status == True:
      bot.send_message(chat_id, "Конкурс начался, макс!!")
    else:
      bot.send_message(chat_id, "Конкурс закончился, понял?!!")

  elif call.data == 'hi':  
    bot.send_message(maks_id, "приветик")

  elif call.data == 'xxx':  
    bot.send_message(maks_id, "я тебя трахну!!")

  elif call.data == 'clear':
    votes.clear()
    vote_counts.clear()

  elif call.data == 'change_vote':
    user_id = chat_id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Вернуться в начало", callback_data='start'))

    if user_id in votes:
      user_state[chat_id] = 'awaiting_vote'
      vote_counts[votes[user_id]] -= 1
      del votes[user_id]
      bot.send_message(chat_id, "Вы можете выбрать новый вариант для вашего голоса.")
    else:
      bot.send_message(chat_id, "Вы еще не голосовали.", reply_markup=markup)

  elif call.data == 'remove_vote':
    user_id = chat_id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Вернуться в начало", callback_data='start'))

    if user_id in votes:
      previous_option = votes[user_id]
      vote_counts[previous_option] -= 1
      del votes[user_id]
      bot.send_message(chat_id, "Ваш голос был удален. Вы можете проголосовать снова.", reply_markup=markup)
    else:
      bot.send_message(chat_id, "Вы еще не голосовали.", reply_markup=markup)

  elif call.data == 'add':
    user_state[chat_id] = 'awaiting_agree'
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Согласен", callback_data='agree'))
    bot.send_message(chat_id,
      "Участвуя в конкурсе, ты даёшь согласие на размещение своего проекта на нашем Telegram-канале Ally Books 📚.\n"
      "Это отличная возможность показать свой талант! 🚀\n\n"
      "Что нужно отправить:\n📌 Сам проект (видео или файл)\n📸 Скриншот из монтажной/рабочей программы\n\n"
      "Ждём твою работу — давай удивим всех вместе! ✨\n",
      "⬇️⬇️⬇️⬇️ТЫКНИТЕ НА ВОТ ЭТУ КНОПКУ ⬇️⬇️⬇️⬇️"
      reply_markup=markup)

  elif call.data == 'agree':
    user_state[chat_id] = 'awaiting_project'
    bot.send_message(chat_id, "📌 Пожалуйста, пришли сам проект")

  elif call.data == 'vote':
    user_state[chat_id] = 'awaiting_vote'
    bot.send_message(chat_id,
      "Все работы участников уже размещены на нашем канале Ally Books 📚!\n"
      "Оцени их и выбери свою любимую — нам важно твоё мнение! 💬✨\n\n"
      "Чтобы проголосовать, просто пришли сюда номер работы, которая тебе понравилась больше всего.\n"
      "Лишь один шаг — и твой голос может решить судьбу победителя! 🏆")
    
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
  elif call.data.startswith('text_'):
    user_chat_id = int(call.data.split('_')[1])
    user_state[user_id] = 'awaiting_text_for_answer'
    answer_targets[user_id] = user_chat_id

    bot.send_message(user_id, "Введите текст, который нужно переслать пользователю.")

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def message_handler(message):
  chat_id = message.chat.id
  user_id = 1335534848
  state = user_state.get(chat_id)

  if state == 'awaiting_offer':
    bot.send_message(chat_id, "❗ функция проходит проверку.")
    bot.send_message(user_id, message.text)

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
      bot.send_message(chat_id, "Вы уже проголосовали!\n Но вы можете изменить или удалить ваш голос.", reply_markup=markup)
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

bot.polling(non_stop=True)
