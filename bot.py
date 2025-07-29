import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo, InputMediaPhoto, Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telebot.types import BotCommandScopeChat 
import json
import os
import threading
import time
import logging
import re
from datetime import datetime, timedelta

# --- НАСТРОЙКИ ЛОГИРОВАНИЯ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# --- /НАСТРОЙКИ ЛОГИРОВАНИЯ ---

# Replace 'YOUR_BOT_TOKEN' with your actual bot token
bot = telebot.TeleBot('7580417309:AAHrFOMsIJJpbiZWGXN-xi3VET2hQb0xTxU')

# --- КОНФИГУРАЦИЯ ---
ADMIN_IDS = [7615679936, 748159294] 
CONTENT_FILE = 'bot_content.json'
USER_DATA_FILE = 'user_data.json' 

# --- /КОНФИГУРАЦИЯ ---

# Bot content structure
bot_data = {
    "is_maintenance_mode": True, 
    "steps": [
        {   # Step 1: Video 1 + text + next button
            "text": r"Совершенствование спортивной формы, развитие навыков боевого искусства \- верное решение, а наш тренажёр вам поможет\!",
            "media_id": None, 
            "button_text": "Следующее видео",
            "button_callback": "next_step_1" 
        },
        {   # Step 2: Video 2 + text + next button
            "text": r"Продолжаем наше путешествие\. Смотрите второе видео, чтобы узнать больше\!",
            "media_id": None,
            "button_text": "Следующее видео",
            "button_callback": "next_step_2" 
        },
        {   # Step 3: Video 3 + text + next button
            "text": r"Погрузитесь в детали с третьим видео\.\nОсобо увлекательно на тренажере заниматься под музыку\. Мишени загораются под ритм любимой композиции\.",
            "media_id": None,
            "button_text": "Перейти к завершению",
            "button_callback": "next_step_3" 
        },
        {   # Step 4: Review and Support text with buttons
            "text": r"Спасибо, что посмотрели наши материалы\! Мы стремимся к совершенству и очень ценим ваше мнение\. Пожалуйста, уделите несколько минут, чтобы оставить отзыв или поделиться впечатлениями\. Ваша обратная связь поможет нам стать ещё лучше\!"
                   r"\n\nВозникли вопросы\? Брак\? Нужна помощь\? Обращайтесь в нашу поддержку\.\n\n Мы готовы оказать быструю и эффективную помощь по всем вопросам, связанным с нашими тренажёрами и услугами\. Наша команда всегда к вашим услугам\!",
            "media_id": None, 
            "buttons": [ 
                {"text": "Оставить отзыв", "url": "https://t.me/review_platform"},
                {"text": "Поддержка", "url": "https://t.me/staturas"}
            ]
        }
    ],
    "support_button_text": "Поддержка", 
    "support_button_url": "https://t.me/staturas", 
    "button_name": "Начни тут", 
    "button_url": "https://t.me/staturas"
}

# Function to escape MarkdownV2 special characters
def escape_markdownv2_chars(text):
    if text is None or not isinstance(text, str):
        return text
    
    text = text.replace('\\', '\\\\') 

    escaped_text = re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

    return escaped_text

# --- Data Loading/Saving Functions ---
def save_bot_data():
    logging.info(f"Start saving data to {CONTENT_FILE}")
    try:
        with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
            json.dump(bot_data, f, ensure_ascii=False, indent=4)
        logging.info(f"Data successfully saved to {CONTENT_FILE}")
    except Exception as e:
        logging.error(f"Error saving data to {CONTENT_FILE}: {e}")

def load_bot_data():
    global bot_data
    logging.info(f"Start loading data from {CONTENT_FILE}")
    if os.path.exists(CONTENT_FILE) and os.path.getsize(CONTENT_FILE) > 0:
        try:
            with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                
                if "steps" not in loaded_data or not isinstance(loaded_data["steps"], list) or len(loaded_data["steps"]) != len(bot_data["steps"]):
                    logging.warning(f"Invalid or missing 'steps' structure in loaded data. Reinitializing 'steps' to default.")
                    loaded_data["steps"] = bot_data["steps"]
                else:
                    for i, default_step in enumerate(bot_data["steps"]):
                        for key, default_value in default_step.items():
                            if key not in loaded_data["steps"][i]:
                                loaded_data["steps"][i][key] = default_value
                            if key == "buttons" and isinstance(default_value, list) and not isinstance(loaded_data["steps"][i].get("buttons"), list):
                                loaded_data["steps"][i]["buttons"] = default_value
                
                for key, default_value in bot_data.items():
                    if key not in loaded_data:
                        loaded_data[key] = default_value
                
                bot_data = loaded_data 
                
                for step_idx in range(len(bot_data["steps"]) - 1): 
                    step = bot_data["steps"][step_idx]
                    if "button_callback" not in step or not step["button_callback"].startswith("next_step_"):
                        step["button_callback"] = f"next_step_{step_idx + 1}"
                
            logging.info(f"Data successfully loaded from {CONTENT_FILE}")
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error from {CONTENT_FILE}: {e}. Initial data will be used.")
            save_bot_data()
        except Exception as e:
            logging.error(f"Unknown error loading data from {CONTENT_FILE}: {e}. Initial data will be used.")
            save_bot_data()
    else:
        logging.warning(f"File {CONTENT_FILE} not found or empty. Creating new file with initial data.")
        save_bot_data()


# User Data Management
user_stats = {} # {str(user_id): {first_seen, last_active, first_name, last_name, username, reached_final_step, user_id}}

def save_user_data():
    logging.info(f"Start saving user data to {USER_DATA_FILE}")
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_stats, f, ensure_ascii=False, indent=4)
        logging.info(f"User data successfully saved to {USER_DATA_FILE}")
    except Exception as e:
        logging.error(f"Error saving user data to {USER_DATA_FILE}: {e}")

def load_user_data():
    global user_stats
    logging.info(f"Start loading user data from {USER_DATA_FILE}")
    if os.path.exists(USER_DATA_FILE) and os.path.getsize(USER_DATA_FILE) > 0:
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                user_stats = json.load(f)
            # Ensure user_id keys are strings
            user_stats = {str(k): v for k, v in user_stats.items()} 
            logging.info(f"User data successfully loaded from {USER_DATA_FILE}")
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error from {USER_DATA_FILE}: {e}. User data will be initialized empty.")
            user_stats = {}
            save_user_data()
        except Exception as e:
            logging.error(f"Unknown error loading user data from {USER_DATA_FILE}: {e}. User data will be initialized empty.")
            user_stats = {}
            save_user_data()
    else:
        logging.warning(f"File {USER_DATA_FILE} not found or empty. Initializing empty user data.")
        user_stats = {}
        save_user_data()

def update_user_info(user_telegram_obj, reached_final_step=False):
    user_id_str = str(user_telegram_obj.id)
    current_time = datetime.now().isoformat()

    # Check if user already exists
    if user_id_str not in user_stats:
        user_stats[user_id_str] = {
            "first_seen": current_time,
            "last_active": current_time, 
            "first_name": user_telegram_obj.first_name if user_telegram_obj.first_name else "",
            "last_name": user_telegram_obj.last_name if user_telegram_obj.last_name else "",
            "username": user_telegram_obj.username if user_telegram_obj.username else "",
            "user_id": user_telegram_obj.id, 
            "reached_final_step": False 
        }
        logging.info(f"New user registered: {user_id_str} ({user_telegram_obj.username})")
    
    user_stats[user_id_str]["last_active"] = current_time
    
    if reached_final_step:
        user_stats[user_id_str]["reached_final_step"] = True
        logging.info(f"User {user_id_str} marked as reached final step.")
    
    save_user_data()

# Load data on startup
load_bot_data()
load_user_data()

# --- HANDLERS ---
admin_state = {}  
admin_media_groups = {}
button_setup_cache = {}

user_steps = {}

TECHNICAL_MAINTENANCE_MESSAGE = r"""**Уважаемые пользователи\!**
На данный момент Бот находится на этапе **технического обслуживания** и доработки\. 
Уже скоро мы представим вам **обновленный** и улучшенный функционал\! 

Пожалуйста, проявите терпение\. Мы работаем для вас\!"""


# --- User-facing Commands ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    logging.info(f"Received /start command from user {message.from_user.id} in chat {message.chat.id}")
    
    user_steps[message.chat.id] = 0

    update_user_info(message.from_user) 
    
    if bot_data["is_maintenance_mode"]:
        send_technical_maintenance_message_to_user(message.chat.id)
    else:
        send_sequential_step(chat_id=message.chat.id, step_index=0)

    if message.from_user.id in ADMIN_IDS:
        set_admin_specific_commands_for_user(chat_id=message.chat.id) 


def send_technical_maintenance_message_to_user(chat_id):
    logging.info(f"Sending technical maintenance message to chat {chat_id}.")
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=bot_data["support_button_text"], url=bot_data["support_button_url"]))
    
    try:
        bot.send_message(chat_id=chat_id, text=TECHNICAL_MAINTENANCE_MESSAGE, parse_mode='MarkdownV2', reply_markup=markup)
        logging.info(f"Maintenance message successfully sent to chat {chat_id}.")
    except Exception as e:
        logging.error(f"Error sending maintenance message to chat {chat_id}: {e}")

def send_sequential_step(chat_id, step_index):
    if not (0 <= step_index < len(bot_data["steps"])):
        logging.error(f"Attempted to send step {step_index} which is out of bounds for chat {chat_id}.")
        if chat_id in ADMIN_IDS:
            bot.send_message(chat_id=chat_id, text=r"Ошибка: Запрошен неверный шаг\. Возможно, индекс шага превышает количество существующих шагов\. Проверьте конфигурацию\. Перезапуск сценария\.", parse_mode='MarkdownV2')
            send_sequential_step(chat_id=chat_id, step_index=0) 
        return

    if step_index == len(bot_data["steps"]) - 1:
        if str(chat_id) in user_stats and chat_id not in ADMIN_IDS:
            user_stats[str(chat_id)]["reached_final_step"] = True
            save_user_data()

    current_step = bot_data["steps"][step_index]
    logging.info(f"Sending sequential step {step_index+1} to chat {chat_id}.")

    markup = InlineKeyboardMarkup()
    if step_index < len(bot_data["steps"]) - 1: 
        markup.add(InlineKeyboardButton(text=current_step["button_text"], callback_data=current_step["button_callback"]))
    else: 
        if "buttons" in current_step and isinstance(current_step["buttons"], list):
            for button_info in current_step["buttons"]:
                if "text" in button_info and "url" in button_info:
                    markup.add(InlineKeyboardButton(text=button_info["text"], url=button_info["url"]))
                else:
                    logging.warning(f"Malformed button info in step {step_index}: {button_info}")
        else:
            logging.warning(f"No valid buttons configuration found for the last step {step_index}.")

    text_to_send = escape_markdownv2_chars(current_step.get("text", " ")) 
    media_id = current_step.get("media_id")

    try:
        if media_id:
            logging.debug(f"Sending media_id: {media_id} for step {step_index} with text.")
            try:
                bot.send_video(chat_id=chat_id, video=media_id, caption=text_to_send, parse_mode='MarkdownV2', reply_markup=markup)
            except Exception as e_video:
                logging.debug(f"Failed to send as video ({e_video}). Trying as photo.")
                try:
                    bot.send_photo(chat_id=chat_id, photo=media_id, caption=text_to_send, parse_mode='MarkdownV2', reply_markup=markup)
                except Exception as e_photo:
                    logging.error(f"Failed to send media as photo or video for step {step_index}: {e_photo}")
                    bot.send_message(chat_id=chat_id, text=text_to_send, parse_mode='MarkdownV2', reply_markup=markup)
                    logging.warning(f"Media for step {step_index} failed, sent text and buttons only.")
            logging.info(f"Step {step_index+1} (media with text) sent to {chat_id}.")
        elif text_to_send.strip(): 
            logging.debug(f"Sending text only for step {step_index}.")
            bot.send_message(chat_id=chat_id, text=text_to_send, parse_mode='MarkdownV2', reply_markup=markup)
            logging.info(f"Step {step_index+1} (text only) sent to {chat_id}.")
        else:
            logging.warning(f"Step {step_index+1} has no media or text content. Sending buttons only.")
            if markup.keyboard: 
                 bot.send_message(chat_id=chat_id, text=r"\_", parse_mode='MarkdownV2', reply_markup=markup)
    except Exception as e:
        logging.error(f"Error sending step {step_index+1} to chat {chat_id}: {e}\nContent being sent: {current_step}")
        if chat_id in ADMIN_IDS:
            error_msg = r"Произошла ошибка при отправке сообщения шага " + str(step_index+1) + r": `" + escape_markdownv2_chars(str(e)) + r"`. Проверьте MarkdownV2 или file\_id."
            bot.send_message(chat_id=chat_id, text=error_msg, parse_mode='MarkdownV2')

@bot.callback_query_handler(func=lambda call: call.data.startswith('next_step_'))
def handle_next_step_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    logging.info(f"Received 'next_step' callback from user {user_id} in chat {chat_id}.")

    if user_id not in ADMIN_IDS and bot_data["is_maintenance_mode"]:
        bot.answer_callback_query(call.id, "Бот в режиме технических работ.", show_alert=True)
        return
        
    try: 
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None) 
        logging.debug(f"Removed button from message {call.message.message_id} in chat {chat_id}.")
    except Exception as e:
        logging.warning(f"Could not remove button from message {call.message.message_id} in chat {chat_id}: {e}")
    
    target_step_index = int(call.data.split('_')[2]) 
    user_steps[chat_id] = target_step_index

    if target_step_index < len(bot_data["steps"]):
        send_sequential_step(chat_id=chat_id, step_index=target_step_index)
    else:
        logging.info(f"All sequential steps completed for user {chat_id}. No more steps to send.")

    bot.answer_callback_query(call.id)


# --- Admin-Specific Handlers ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    logging.info(f"Received /admin command from user {message.from_user.id} in chat {message.chat.id}")
    if message.from_user.id not in ADMIN_IDS:
        logging.warning(f"User {message.from_user.id} tried to access admin panel without permission.")
        bot.send_message(chat_id=message.chat.id, text=r"У вас нет прав администратора\. Только для избранных\.", parse_mode='MarkdownV2')
        return
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Редактировать сообщение по шагу", callback_data="edit_step_content"))
    markup.add(InlineKeyboardButton("Показать текущий контент", callback_data="show_current_content"))
    markup.add(InlineKeyboardButton("Пользовательская статистика", callback_data="show_user_stats")) 
    markup.add(InlineKeyboardButton("Изменить кнопку 'Поддержка' (Глобальная)", callback_data="change_support_button_global")) 
    markup.add(InlineKeyboardButton("Изменить кнопку 'Начни тут' (Не используется в потоке)", callback_data="change_start_button_global")) 
    markup.add(InlineKeyboardButton("Перезапустить сценарий (/start для админа)", callback_data="admin_restart_scenario")) 
    
    toggle_text = "Переключить режим тех. работ: " + ("ВКЛ" if bot_data["is_maintenance_mode"] else "ВЫКЛ")
    markup.add(InlineKeyboardButton(toggle_text, callback_data="toggle_maintenance_mode")) 
    
    logging.info(f"Admin panel sent to chat {message.chat.id}.")
    bot.send_message(chat_id=message.chat.id, text="**Панель администратора**\n\nВыберите действие:", reply_markup=markup, parse_mode='MarkdownV2')

@bot.callback_query_handler(func=lambda call: call.data == 'show_user_stats')
def show_user_stats(call):
    if call.from_user.id not in ADMIN_IDS: return

    total_users = len(user_stats)
    
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    last_week = now - timedelta(weeks=1)
    last_month = now - timedelta(days=30) 

    users_last_day = 0
    users_last_week = 0
    users_last_month = 0
    users_reached_final = 0

    for user_id_str, data in user_stats.items():
        if "last_active" in data:
            try: # Use try-except for robust date parsing. If format changes, it won't crash
                 last_active_dt = datetime.fromisoformat(data["last_active"])
                 if last_active_dt > yesterday:
                     users_last_day += 1
                 if last_active_dt > last_week:
                     users_last_week += 1
                 if last_active_dt > last_month:
                     users_last_month += 1
            except ValueError as e:
                logging.error(f"Error parsing date for user {user_id_str}: {data['last_active']} - {e}")
        
        if data.get("reached_final_step", False):
            users_reached_final += 1
    
    stats_text = r"""**Статистика пользователей:**
Всего пользователей: `{total_users}`
Активных за последний день: `{users_last_day}`
Активных за последнюю неделю: `{users_last_week}`
Активных за последний месяц: `{users_last_month}`
Дошли до финального шага: `{users_reached_final}`""".format(
        total_users=total_users,
        users_last_day=users_last_day,
        users_last_week=users_last_week,
        users_last_month=users_last_month,
        users_reached_final=users_reached_final
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Посмотреть пользователей", callback_data="view_all_users"))
    markup.add(InlineKeyboardButton("Вернуться в админ-панель", callback_data="admin_return_to_menu_from_user_stats"))

    bot.send_message(chat_id=call.message.chat.id, text=escape_markdownv2_chars(stats_text), parse_mode='MarkdownV2', reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'view_all_users')
def view_all_users(call):
    if call.from_user.id not in ADMIN_IDS: return

    user_list_text_parts = []
    
    user_list_text_parts.append(r"**Список пользователей:**" + "\n\n")

    for user_id_str, data in user_stats.items():
        name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        username = data.get("username", "")
        current_user_id = data.get("user_id") 

        full_name = f"{name} {last_name}".strip()
        
        if full_name:
            user_link = f"[{escape_markdownv2_chars(full_name)}](tg://user?id={current_user_id})"
        elif username:
            user_link = f"@{escape_markdownv2_chars(username)}"
        else:
            user_link = f"Пользователь с ID {current_user_id}"
        
        user_list_text_parts.append(f"\\- {user_link}\n")

    full_text = "".join(user_list_text_parts)

    current_chunk = ""
    for line in full_text.split('\n'):
        if len(current_chunk) + len(line) + 1 > 4000: 
            bot.send_message(chat_id=call.message.chat.id, text=current_chunk, parse_mode='MarkdownV2')
            current_chunk = line
        else:
            if current_chunk: 
                current_chunk += '\n'
            current_chunk += line
    
    if current_chunk: 
        bot.send_message(chat_id=call.message.chat.id, text=current_chunk, parse_mode='MarkdownV2')

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Вернуться к статистике", callback_data="show_user_stats"))
    bot.send_message(chat_id=call.message.chat.id, text=r"Завершено\.", parse_mode='MarkdownV2', reply_markup=markup)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == 'admin_return_to_menu_from_user_stats')
def admin_return_to_menu_from_user_stats(call):
    if call.from_user.id not in ADMIN_IDS: return
    admin_panel(call.message)
    bot.answer_callback_query(call.id, "Возврат в админ-панель")


@bot.message_handler(commands=['mode_toggle']) 
def toggle_maintenance_mode_command(message):
    if message.from_user.id not in ADMIN_IDS:
        logging.warning(f"User {message.from_user.id} tried to use /mode_toggle without permission.")
        bot.send_message(chat_id=message.chat.id, text=r"У вас нет прав для изменения режима работы бота\.", parse_mode='MarkdownV2')
        return
    
    bot_data["is_maintenance_mode"] = not bot_data["is_maintenance_mode"]
    save_bot_data()
    
    status_text = "ВКЛ" if bot_data["is_maintenance_mode"] else "ВЫКЛ"
    status_msg_content = r"**Режим технических работ переключен на:** `" + status_text + r"`\n\nТеперь пользователи будут видеть "
    status_msg_content += r"сообщение о тех\. работах\." if bot_data["is_maintenance_mode"] else r"пошаговый контент\."
    
    try:
        bot.send_message(chat_id=message.chat.id, text=status_msg_content, parse_mode='MarkdownV2')
        logging.info(f"Admin {message.from_user.id} toggled maintenance mode to {status_text} via command. Confirmation sent.")
    except Exception as e:
        logging.error(f"Error sending maintenance mode toggle confirmation to admin {message.from_user.id}: {e}")


@bot.callback_query_handler(func=lambda call: call.data == 'toggle_maintenance_mode')
def toggle_maintenance_mode_callback(call):
    if call.from_user.id not in ADMIN_IDS: 
        bot.answer_callback_query(call.id, "У вас нет прав.", show_alert=True)
        return
    
    bot_data["is_maintenance_mode"] = not bot_data["is_maintenance_mode"]
    save_bot_data()
    
    status_text = "ВКЛ" if bot_data["is_maintenance_mode"] else "ВЫКЛ"
    bot.answer_callback_query(call.id, f"Режим тех. работ: {status_text}!")
    logging.info(f"Admin {call.from_user.id} toggled maintenance mode to {status_text} via callback.")
    
    admin_panel(call.message) 

@bot.callback_query_handler(func=lambda call: call.data == 'admin_restart_scenario')
def admin_restart_scenario_callback(call):
    if call.from_user.id not in ADMIN_IDS: return
    logging.info(f"Admin {call.from_user.id} requested scenario restart.")
    user_steps[call.message.chat.id] = 0 
    send_sequential_step(chat_id=call.message.chat.id, step_index=0) 
    bot.answer_callback_query(call.id, "Сценарий перезапущен!")

@bot.callback_query_handler(func=lambda call: call.data == 'edit_step_content')
def edit_step_content_callback(call):
    if call.from_user.id not in ADMIN_IDS: return
    markup = InlineKeyboardMarkup(row_width=2)
    for i in range(len(bot_data["steps"])):
        has_content = bot_data["steps"][i].get("text", "").strip() or bot_data["steps"][i].get("media_id")
        button_text = f"Шаг {i+1}"
        if not has_content:
            button_text += " (Пусто)"

        markup.add(InlineKeyboardButton(button_text, callback_data=f"edit_step_select_{i}")) 
    bot.send_message(chat_id=call.message.chat.id, text=r"**Выберите, какое сообщение вы хотите отредактировать:**", reply_markup=markup, parse_mode='MarkdownV2')
    bot.answer_callback_query(call.id)

# Handler for selecting a specific step to edit
CALLBACK_PREFIX_EDIT_STEP_SELECT = 'edit_step_select_'
@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PREFIX_EDIT_STEP_SELECT))
def handle_edit_step_selection(call):
    if call.from_user.id not in ADMIN_IDS: return
    step_index = int(call.data[len(CALLBACK_PREFIX_EDIT_STEP_SELECT):]) 

    admin_state[call.from_user.id] = {"state": "editing_step_options", "step_index": step_index} 

    current_step_info = bot_data["steps"][step_index]
    initial_message = r"**Редактирование шага " + str(step_index+1) + r":**\n\n" \
                      r"**Текущий текст:** `" + escape_markdownv2_chars(current_step_info.get('text', '')) + r"`\n" 
    if current_step_info.get("media_id"):
        initial_message += r"**Текущее медиа ID:** `" + escape_markdownv2_chars(current_step_info['media_id']) + r"`\n"
    else:
        initial_message += r"**Медиа: Нет**\n"

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("Изменить текст", callback_data=f"edit_step_{step_index}_option_text"))
    markup.add(InlineKeyboardButton("Изменить медиафайл", callback_data=f"edit_step_{step_index}_option_media"))
    
    if step_index < len(bot_data["steps"]) - 1: 
        markup.add(InlineKeyboardButton("Изменить текст кнопки 'Следующее'", callback_data=f"edit_step_{step_index}_option_button_text"))
    else: 
        if "buttons" in current_step_info and isinstance(current_step_info["buttons"], list):
            for i, btn in enumerate(current_step_info["buttons"]):
                button_title = btn.get('text', f'Кнопка {i+1}')
                markup.add(InlineKeyboardButton(f"Изменить кнопку '{escape_markdownv2_chars(button_title)}'", callback_data=f"edit_step_{step_index}_option_final_button_{i}"))
    
    markup.add(InlineKeyboardButton("Вернуться в меню редактирования шагов", callback_data="edit_step_content")) 
    markup.add(InlineKeyboardButton("Вернуться в админ-панель", callback_data="admin_return_to_menu_from_step_edit")) 

    bot.send_message(chat_id=call.message.chat.id, text=initial_message, reply_markup=markup, parse_mode='MarkdownV2')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_return_to_menu_from_step_edit")
def admin_return_to_menu_from_step_edit(call):
    if call.from_user.id not in ADMIN_IDS: return
    admin_panel(call.message)
    bot.answer_callback_query(call.id, "Возврат в админ-панель")

# Handlers for editing specific parts of a step CONTENT (TEXT, MEDIA, BUTTON TEXT)
@bot.callback_query_handler(func=lambda call: call.data.endswith('_option_text'))
def edit_step_text_prompt(call):
    if call.from_user.id not in ADMIN_IDS: return
    step_index = int(call.data.split('_')[2]) 
    
    admin_state[call.from_user.id] = {"state": "waiting_for_step_text", "current_editing_step_index": step_index}
    
    bot.send_message(chat_id=call.message.chat.id, text=r"**Отправьте новый текст для шага " + str(step_index+1) + r"**\.\n\n_Используйте MarkdownV2_:\n\nТекущий текст: `" + escape_markdownv2_chars(bot_data['steps'][step_index].get('text', '')) + "`", parse_mode='MarkdownV2')
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['text'], func=lambda message: admin_state.get(message.from_user.id) and admin_state[message.from_user.id].get("state") == "waiting_for_step_text")
def set_step_text(message):
    if message.from_user.id not in ADMIN_IDS: return
    step_index = admin_state[message.from_user.id].get("current_editing_step_index")
    if step_index is None: 
        bot.send_message(chat_id=message.chat.id, text=r"**Ошибка:** Не удалось определить шаг для редактирования текста\. Пожалуйста, повторите операцию через меню админа\.", parse_mode='MarkdownV2')
        del admin_state[message.from_user.id]
        return
    
    bot_data["steps"][step_index]["text"] = message.text
    save_bot_data()
    bot.send_message(chat_id=message.chat.id, text=r"**Текст шага " + str(step_index+1) + r" обновлен\!**\nПроверьте:\n`" + escape_markdownv2_chars(bot_data['steps'][step_index]['text']) + "`", parse_mode='MarkdownV2')
    del admin_state[message.from_user.id]
    send_sequential_step(chat_id=message.chat.id, step_index=step_index) 

@bot.callback_query_handler(func=lambda call: call.data.endswith('_option_media'))
def edit_step_media_prompt(call):
    if call.from_user.id not in ADMIN_IDS: return
    step_index = int(call.data.split('_')[2])
    admin_state[call.from_user.id]["state"] = "waiting_for_step_media"
    admin_state[call.from_user.id]["current_editing_step_index"] = step_index
    bot.send_message(chat_id=call.message.chat.id, text=r"**Отправьте одиночное видео или фото для шага " + str(step_index+1) + r"**\.\n\n_Старое медиа будет перезаписано\. Отправьте текстовое сообщение 'нет' если не хотите медиа\._", parse_mode='MarkdownV2')
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['text', 'video', 'photo'], func=lambda message: admin_state.get(message.from_user.id) and admin_state[message.from_user.id].get("state") == "waiting_for_step_media")
def set_step_media(message):
    if message.from_user.id not in ADMIN_IDS: return
    step_index = admin_state[message.from_user.id].get("current_editing_step_index")
    if step_index is None: 
        bot.send_message(chat_id=message.chat.id, text=r"**Ошибка:** Не удалось определить шаг для редактирования медиа\. Пожалуйста, повторите операцию через меню админа\.", parse_mode='MarkdownV2')
        del admin_state[message.from_user.id]
        return

    new_media_id = None
    if message.content_type == 'video':
        new_media_id = message.video.file_id
    elif message.content_type == 'photo':
        new_media_id = message.photo[-1].file_id 
    elif message.text and message.text.lower() == 'нет':
        new_media_id = None 
    else:
        bot.send_message(chat_id=message.chat.id, text=r"**Ошибка:** Ожидалось видео, фото или текст 'нет'\. Пожалуйста, попробуйте снова\.", parse_mode='MarkdownV2')
        return

    bot_data["steps"][step_index]["media_id"] = new_media_id
    save_bot_data()
    # Corrected f-string usage for backslashes
    bot.send_message(chat_id=message.chat.id, text=fr"**Медиафайл для шага {step_index+1} обновлен\!**\nID:`{escape_markdownv2_chars(new_media_id) if new_media_id else 'Нет'}`", parse_mode='MarkdownV2')
    del admin_state[message.from_user.id]
    user_steps[message.chat.id] = step_index 
    send_sequential_step(chat_id=message.chat.id, step_index=step_index) 

@bot.callback_query_handler(func=lambda call: call.data.endswith('_option_button_text'))
def edit_step_button_text_prompt(call):
    if call.from_user.id not in ADMIN_IDS: return
    step_index = int(call.data.split('_')[2])
    admin_state[call.from_user.id]["state"] = "waiting_for_step_button_text"
    admin_state[call.from_user.id]["current_editing_step_index"] = step_index
    current_button_text = bot_data['steps'][step_index].get('button_text', '')
    bot.send_message(chat_id=call.message.chat.id, text=r"**Отправьте новый текст для кнопки шага " + str(step_index+1) + r"**\.\n\n_Например: Следующее видео, Продолжить_:\n\nТекущий текст: `" + escape_markdownv2_chars(current_button_text) + "`", parse_mode='MarkdownV2')
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['text'], func=lambda message: admin_state.get(message.from_user.id) and admin_state[message.from_user.id].get("state") == "waiting_for_step_button_text")
def set_step_button_text(message):
    if message.from_user.id not in ADMIN_IDS: return
    step_index = admin_state[message.from_user.id].get("current_editing_step_index")
    if step_index is None: 
        bot.send_message(chat_id=message.chat.id, text=r"**Ошибка:** Не удалось определить шаг для редактирования текста кнопки\. Пожалуйста, повторите операцию через меню админа\.", parse_mode='MarkdownV2')
        del admin_state[message.from_user.id]
        return
    
    bot_data["steps"][step_index]["button_text"] = message.text
    save_bot_data()
    bot.send_message(chat_id=message.chat.id, text=r"**Текст кнопки шага " + str(step_index+1) + r" обновлен\!**\nПроверьте:\n`" + escape_markdownv2_chars(bot_data['steps'][step_index]['button_text']) + "`", parse_mode='MarkdownV2')
    del admin_state[message.from_user.id]
    user_steps[message.chat.id] = step_index 
    send_sequential_step(chat_id=message.chat.id, step_index=step_index)

@bot.callback_query_handler(func=lambda call: call.data.endswith('_option_final_button_0')) 
def edit_step_final_button_review_prompt(call):
    if call.from_user.id not in ADMIN_IDS: return
    step_index = int(call.data.split('_')[2]) 
    
    current_button = bot_data["steps"][step_index]["buttons"][0] 
    
    admin_state[call.from_user.id] = {"state": "waiting_for_final_button_edit_text", "current_editing_step_index": step_index, "current_editing_button_index": 0} 

    bot.send_message(chat_id=call.message.chat.id, 
                     text=r"**Изменение кнопки '" + escape_markdownv2_chars(current_button.get('text', '')) + r"' (Шаг " + str(step_index+1) + r"):**\n\n"
                     r"**Отправьте новый ТЕКСТ для кнопки:**\n`" + escape_markdownv2_chars(current_button.get('text', '')) + "`", parse_mode='MarkdownV2')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.endswith('_option_final_button_1')) 
def edit_step_final_button_support_prompt(call):
    if call.from_user.id not in ADMIN_IDS: return
    step_index = int(call.data.split('_')[2]) 
    
    current_button = bot_data["steps"][step_index]["buttons"][1] 
    
    admin_state[call.from_user.id] = {"state": "waiting_for_final_button_edit_text", "current_editing_step_index": step_index, "current_editing_button_index": 1}

    bot.send_message(chat_id=call.message.chat.id, 
                     text=r"**Изменение кнопки '" + escape_markdownv2_chars(current_button.get('text', '')) + r"' (Шаг " + str(step_index+1) + r"):**\n\n"
                     r"**Отправьте новый ТЕКСТ для кнопки:**\n`" + escape_markdownv2_chars(current_button.get('text', '')) + "`", parse_mode='MarkdownV2')
    bot.answer_callback_query(call.id)


@bot.message_handler(content_types=['text'], func=lambda message: admin_state.get(message.from_user.id) and admin_state[message.from_user.id].get("state") == "waiting_for_final_button_edit_text")
def set_final_button_text(message):
    if message.from_user.id not in ADMIN_IDS: return
    user_id = message.from_user.id
    
    step_index = admin_state[user_id].get("current_editing_step_index")
    button_idx = admin_state[user_id].get("current_editing_button_index")
    if step_index is None or button_idx is None: 
        bot.send_message(chat_id=message.chat.id, text=r"**Ошибка:** Не удалось определить шаг или кнопку для редактирования текста\. Повторите операцию\.", parse_mode='MarkdownV2')
        del admin_state[user_id]
        return

    button_setup_cache[user_id] = {"text": message.text, "step_index": step_index, "button_idx": button_idx}
    admin_state[user_id]["state"] = "waiting_for_final_button_edit_url" 
    
    current_button_url = bot_data["steps"][step_index]["buttons"][button_idx].get("url", "")
    bot.send_message(chat_id=user_id, text=r"**Отправьте новый URL для кнопки '" + escape_markdownv2_chars(message.text) + r"':**\n`" + escape_markdownv2_chars(current_button_url) + "`", parse_mode='MarkdownV2')

@bot.message_handler(content_types=['text'], func=lambda message: admin_state.get(message.from_user.id) and admin_state[message.from_user.id].get("state") == "waiting_for_final_button_edit_url")
def set_final_button_url(message):
    if message.from_user.id not in ADMIN_IDS: return
    user_id = message.from_user.id
    
    if user_id not in button_setup_cache: 
        bot.send_message(chat_id=message.chat.id, text=r"**Ошибка:** Не удалось найти кэш для настройки кнопки\. Пожалуйста, повторите операцию через меню админа\.", parse_mode='MarkdownV2')
        del admin_state[user_id]
        return

    step_index = button_setup_cache[user_id]["step_index"]
    button_idx = button_setup_cache[user_id]["button_idx"]

    bot_data["steps"][step_index]["buttons"][button_idx]["text"] = button_setup_cache[user_id]["text"]
    bot_data["steps"][step_index]["buttons"][button_idx]["url"] = message.text
    
    save_bot_data()

    bot.send_message(chat_id=user_id, text=r"**Кнопка '" + escape_markdownv2_chars(bot_data['steps'][step_index]['buttons'][button_idx]['text']) + r"' обновлена\!**", parse_mode='MarkdownV2')
    del admin_state[user_id]
    del button_setup_cache[user_id]
    user_steps[user_id] = step_index 
    send_sequential_step(chat_id=user_id, step_index=step_index)


# Handlers for general purpose buttons (Support and Start button that are not part of basic flow)
@bot.callback_query_handler(func=lambda call: call.data == 'change_support_button_global')
def handle_change_support_button_global_callback(call):
    if call.from_user.id not in ADMIN_IDS: return
    admin_state[call.from_user.id] = {"state": "waiting_for_support_button_text_global"} 
    button_setup_cache[call.from_user.id] = {"type": "support_global"}
    bot.send_message(chat_id=call.message.chat.id, text=r"**Отлично\!** Отправьте мне новый **текст** для глобальной кнопки 'Поддержка' \(например, `Связь с нами`\)\.", parse_mode='MarkdownV2')
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['text'], func=lambda message: admin_state.get(message.from_user.id) and admin_state[message.from_user.id].get("state") == "waiting_for_support_button_text_global")
def set_support_button_text_global(message):
    if message.from_user.id not in ADMIN_IDS: return
    user_id = message.from_user.id
    button_setup_cache[user_id]["text"] = message.text
    admin_state[user_id]["state"] = "waiting_for_support_button_url_global"
    bot.send_message(chat_id=user_id, text=r"**Теперь отправьте новый URL** для глобальной кнопки 'Поддержка' \(например, `https://t.me/your_support_chat`\)\.", parse_mode='MarkdownV2')

@bot.message_handler(content_types=['text'], func=lambda message: admin_state.get(message.from_user.id) and admin_state[message.from_user.id].get("state") == "waiting_for_support_button_url_global")
def set_support_button_url_global(message):
    if message.from_user.id not in ADMIN_IDS: return
    user_id = message.from_user.id
    if user_id not in button_setup_cache or button_setup_cache[user_id].get("type") != "support_global": return

    bot_data["support_button_text"] = button_setup_cache[user_id]["text"]
    bot_data["support_button_url"] = message.text
    save_bot_data()
    bot.send_message(chat_id=user_id, text=f"**Глобальная кнопка 'Поддержка' обновлена:**\nТекст: `{escape_markdownv2_chars(bot_data['support_button_text'])}`\nURL: `{escape_markdownv2_chars(bot_data['support_button_url'])}`", parse_mode='MarkdownV2')
    del admin_state[user_id]
    del button_setup_cache[user_id]


@bot.callback_query_handler(func=lambda call: call.data == 'change_start_button_global')
def handle_change_start_button_global_callback(call):
    if call.from_user.id not in ADMIN_IDS: return
    admin_state[call.from_user.id] = {"state": "waiting_for_start_button_text_global_misc"} 
    button_setup_cache[call.from_user.id] = {"type": "start_global_misc"}
    bot.send_message(chat_id=call.message.chat.id, text=r"**Отлично\!** Отправьте мне новый **текст** для кнопки 'Начни тут' \(эта кнопка не используется в основном потоке сообщений для пользователя, но может быть полезной в других сценариях\)\.", parse_mode='MarkdownV2')
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['text'], func=lambda message: admin_state.get(message.from_user.id) and admin_state[message.from_user.id].get("state") == "waiting_for_start_button_text_global_misc")
def set_start_button_text_global_misc(message):
    if message.from_user.id not in ADMIN_IDS: return
    user_id = message.from_user.id
    button_setup_cache[user_id]["text"] = message.text
    admin_state[user_id]["state"] = "waiting_for_start_button_url_global_misc"
    bot.send_message(chat_id=user_id, text=r"**Теперь отправьте новый URL** для кнопки 'Начни тут'\.", parse_mode='MarkdownV2')

@bot.message_handler(content_types=['text'], func=lambda message: admin_state.get(message.from_user.id) and admin_state[message.from_user.id].get("state") == "waiting_for_start_button_url_global_misc")
def set_start_button_url_global_misc(message):
    if message.from_user.id not in ADMIN_IDS: return
    user_id = message.from_user.id
    if user_id not in button_setup_cache or button_setup_cache[user_id].get("type") != "start_global_misc": return

    bot_data["button_name"] = button_setup_cache[user_id]["text"]
    bot_data["button_url"] = message.text
    save_bot_data()
    bot.send_message(chat_id=user_id, text=f"**Кнопка 'Начни тут' обновлена:**\nТекст: `{escape_markdownv2_chars(bot_data['button_name'])}`\nURL: `{escape_markdownv2_chars(bot_data['button_url'])}`", parse_mode='MarkdownV2')
    del admin_state[user_id]
    del button_setup_cache[user_id]


@bot.callback_query_handler(func=lambda call: call.data.startswith('show_current_content'))
def handle_show_current_content_callback(call):
    logging.info(f"Received callback show_current_content from user {call.from_user.id}")
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, r"У вас нет прав администратора\.", show_alert=True)
        return

    content_info = "**Текущий контент бота (по шагам):**\n\n"
    for i, step in enumerate(bot_data["steps"]):
        content_info += f"--- **Шаг {i+1}** ---\n"
        content_info += f"**Текст:** `{escape_markdownv2_chars(step.get('text', 'Нет текста'))}`\n"
        if step.get("media_id"):
            content_info += f"**Медиа ID:** `{escape_markdownv2_chars(step['media_id'])}`\n"
        else:
            content_info += "**Медиа: Нет**\n"
        
        if i < len(bot_data["steps"]) - 1: # All steps except the last
            if "button_text" in step:
                content_info += r"**Текст кнопки 'Далее':** `" + escape_markdownv2_chars(step['button_text']) + r"`\n"
                content_info += r"**Callback кнопки:** `" + escape_markdownv2_chars(step['button_callback']) + r"`\n"
        elif "buttons" in step: # For the final step's buttons
            content_info += "**Кнопки (финальный шаг):**\n"
            for btn_info in step["buttons"]:
                content_info += r"  `- " + escape_markdownv2_chars(btn_info.get('text', '')) + r"` \(URL:`" + escape_markdownv2_chars(btn_info.get('url', '')) + r"`\)\n"
        content_info += r"\n" 
    
    content_info += "--- **Глобальные настройки** ---\n"
    content_info += f"**Режим технических работ:** `{'ВКЛ' if bot_data['is_maintenance_mode'] else 'ВЫКЛ'}`\n"
    content_info += f"**Текст глобальной кнопки 'Поддержка':** `{escape_markdownv2_chars(bot_data['support_button_text'])}`\n"
    content_info += f"**URL глобальной кнопки 'Поддержка':** `{escape_markdownv2_chars(bot_data['support_button_url'])}`\n"
    content_info += f"**Текст глобальной кнопки 'Начни тут':** `{escape_markdownv2_chars(bot_data['button_name'])}`\n"
    content_info += f"**URL глобальной кнопки 'Начни тут':** `{escape_markdownv2_chars(bot_data['button_url'])}`\n"

    try:
        bot.send_message(chat_id=call.message.chat.id, text=content_info, parse_mode='MarkdownV2')
    except Exception as e:
        logging.error(f"Error sending current content to admin {call.from_user.id}: {e}")
        error_msg = r"Произошла ошибка при отправке текущего контента: `" + escape_markdownv2_chars(str(e)) + r"`. Возможно, в контенте много необработанных символов MarkdownV2."
        bot.send_message(chat_id=call.message.chat.id, text=error_msg, parse_mode='MarkdownV2')

    bot.answer_callback_query(call.id)
    logging.info(f"Current content sent to admin {call.from_user.id}.")

# Set up bot commands for admin menu (BotCommander menu)
# This function sets commands specific to an admin user's chat_id.
# These commands appear in the menu pop-up when typing '/' or clicking the menu button.
def set_admin_specific_commands_for_user(chat_id): 
    commands = [
        telebot.types.BotCommand("/start", "Начать / Перезапустить сценарий"),
        telebot.types.BotCommand("/admin", "Меню администрирования"),
        telebot.types.BotCommand("/mode_toggle", "Переключить режим тех. работ"),
        telebot.types.BotCommand("/update_menu", "Обновить меню команд (для отладки)") 
    ]
    try:
        # bot.set_my_commands takes a list of BotCommand and registers them for a specific scope.
        bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=chat_id)) 
        logging.info(f"Admin commands set for chat {chat_id} using BotCommandScopeChat.")
    except Exception as e:
        logging.error(f"Error setting admin commands for {chat_id}: {e}")

# This function sets default commands for ALL users. 
# This should contain only commands visible to everyone.
def set_global_user_commands():
    commands = [
        telebot.types.BotCommand("/start", "Начать / Перезапустить сценарий"),
    ]
    try:
        # bot.set_my_commands with default scope (no scope parameter) applied to all users
        bot.set_my_commands(commands) 
        logging.info("Global user commands set.")
    except Exception as e:
        logging.error(f"Error setting global user commands: {e}")


@bot.message_handler(commands=['update_menu'])
def update_menu_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(chat_id=message.chat.id, text=r"У вас нет прав для обновления меню команд\.", parse_mode='MarkdownV2')
        return
    
    set_admin_specific_commands_for_user(chat_id=message.chat.id) # Re-call admin command setter for this user
    bot.send_message(chat_id=message.chat.id, text=r"Меню команд обновлено\. Возможно, потребуется перезапустить официальный клиент Telegram для отображения изменений\.", parse_mode='MarkdownV2')


# Start polling for messages
if __name__ == '__main__':
    logging.info("Bot starting...")
    # Set default commands for all users (e.g., just /start)
    set_global_user_commands()
    
    # Also set admin commands for all ADMIN_IDS upon bot startup
    # This ensures admins have their special commands if the bot restarts.
    for admin_id in ADMIN_IDS:
        set_admin_specific_commands_for_user(chat_id=admin_id)
        
    bot.infinity_polling(timeout=30, long_polling_timeout=30) 
    logging.info("Bot stopped.")
