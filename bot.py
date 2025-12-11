import telebot
from telebot import types
import requests
from lxml import etree
import re

# === НАСТРОЙКИ ===
TOKEN = '8557822109:AAFXwqMvMNnwCh3baDoBP2DvDgK20-ui-dE'  # ⚠️ Замени!
ADMIN_CHAT_ID = 339123540      # Твой ID

YML_URL = "https://groupes.ru/yml.xml"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

bot = telebot.TeleBot(TOKEN)

# === ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
products = []
categories = {}
user_state = {}
user_data = {}

# === ИНФОРМАЦИЯ ПО УСЛУГАМ ===
SERVICES = {
    "Контакты": (
        "📍 *Адрес*:\n"
        "г. Нижний Новгород, ул. Щербакова, д. 15, офис 302\n\n"
        "📞 *Телефон*:\n+7 (831) 266 01 23\n\n"
        "📧 *Email*:\ninfo@groupes.ru\n\n"
        "🕒 *График работы*:\nПн–Пт: с 09:00 до 18:00"
    ),
    "Доставка": (
        "🚚 *Транспортировка станков*\n\n"
        "При транспортировке станка мы обеспечиваем надежное крепление. "
        "Дополнительно фиксируем отдельные части станка, чтобы избежать надломов. "
        "Подбираем нужный транспорт и производим погрузку станка с учетом его «слабых мест».\n\n"
        "Перевозка станков осуществляется по разным городам РФ и странам СНГ."
    ),
    "Сервис": (
        "🔧 *Сервисный центр*\n\n"
        "Группа Энергосервис оказывает полный комплекс услуг по сервисному обслуживанию "
        "металлообрабатывающего оборудования на территории России и стран СНГ."
    ),
    "Инжиниринг": "⚙️ *Инжиниринговый центр*\n\nПроекты любой сложности с фиксированным бюджетом и сроками.",
    "Рассрочка": "💳 *Рассрочка от поставщика*\n\nФиксируйте цену сейчас и получите станок без отсрочки.",
    "Trade-in": "🔄 *Trade-in*\n\nПримем ваш старый станок в зачёт нового.",
    "Лизинг": "📊 *Лизинг*\n\nАренда с выкупом. Удобнее кредита. График под ваш бюджет."
}

# === ЗАГРУЗКА YML ===
def load_catalog():
    global products, categories
    try:
        resp = requests.get(YML_URL, headers=HEADERS, timeout=20)
        root = etree.fromstring(resp.content)

        # Убираем namespace
        for elem in root.getiterator():
            if elem.tag.startswith('{'):
                elem.tag = elem.tag.split('}', 1)[1]

        shop = root.find('shop')
        categories = {
            cat.get('id'): cat.text.strip()
            for cat in shop.find('categories').findall('category')
        }

        products = []
        for offer in shop.find('offers').findall('offer'):
            # Извлекаем данные только если они есть
            name = "Без названия"
            desc = "Описание отсутствует"
            url = "https://groupes.ru"
            price = "Цена по запросу"
            cat_id = None
            available = offer.get('available', 'true')

            # Безопасное извлечение
            name_elem = offer.find('name')
            if name_elem is not None and name_elem.text:
                name = name_elem.text.strip()

            desc_elem = offer.find('description')
            if desc_elem is not None and desc_elem.text:
                desc = desc_elem.text.strip()

            url_elem = offer.find('url')
            if url_elem is not None and url_elem.text:
                url = url_elem.text.strip()

            price_elem = offer.find('price')
            if price_elem is not None and price_elem.text:
                price = price_elem.text + " ₽"

            cat_elem = offer.find('categoryId')
            if cat_elem is not None and cat_elem.text:
                cat_id = cat_elem.text

            # Параметры
            params = {}
            for param in offer.findall('param'):
                pname = param.get('name')
                if pname:
                    pval = (param.text or "").strip()
                    unit = param.get('unit', '')
                    if unit:
                        pval += f" {unit}"
                    params[pname] = pval

            products.append({
                "name": name,
                "description": desc,
                "link": url,
                "price": price,
                "cat_id": cat_id,
                "available": available,
                "params": params
            })

        print(f"✅ Загружено {len(products)} станков, {len(categories)} категорий")
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return False

# === ПОИСК ПО ЗАПРОСУ ===
def search_products(query):
    query = query.lower()
    results = []
    for p in products:
        if query in p['name'].lower() or query in p['description'].lower():
            results.append(p)
            if len(results) >= 3:
                break
    return results

# === ФИЛЬТРАЦИЯ ПО ПАРАМЕТРАМ ===
def filter_by_params(cat_id, numbers, cat_name):
    def to_num(s):
        try:
            return float(re.sub(r'[^\d.]', '', str(s)))
        except:
            return 0

    results = []
    for p in products:
        if p['cat_id'] != cat_id:
            continue

        params = p['params']
        match = True

        if "фрезер" in cat_name.lower():
            if len(numbers) >= 3:
                if to_num(params.get("Ширина стола", "0")) < numbers[0]: match = False
                if to_num(params.get("Длина стола", "0")) < numbers[1]: match = False
                if to_num(params.get("Нагрузка на стол", "0")) < numbers[2]: match = False
        elif "токар" in cat_name.lower():
            if len(numbers) >= 2:
                if to_num(params.get("Макс. диаметр обработки", "0")) < numbers[0]: match = False
                if to_num(params.get("Макс. длина обработки", "0")) < numbers[1]: match = False
        elif "шлиф" in cat_name.lower():
            if len(numbers) >= 3:
                if to_num(params.get("Ширина стола", "0")) < numbers[1]: match = False
                if to_num(params.get("Длина стола", "0")) < numbers[0]: match = False
                if to_num(params.get("Нагрузка на стол", "0")) < numbers[2]: match = False

        if match:
            results.append(p)
            if len(results) >= 5:
                break
    return results

# === МЕНЮ ===
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📋 Категории")
    markup.add("🔍 Поиск по названию")
    markup.add("⚙️ Подбор оборудования")
    markup.add("ℹ️ Услуги компании")
    markup.add("📞 Связь с менеджером")
    return markup

def services_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for name in SERVICES.keys():
        markup.add(types.KeyboardButton(name))
    markup.add("⬅️ Назад")
    return markup

def category_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for name in categories.values():
        markup.add(types.KeyboardButton(name))
    markup.add("⬅️ Назад")
    return markup

# === КОМАНДЫ ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        f"🔧 *Здравствуйте, {message.from_user.first_name}!*\n\n"
        "Я — технический ассистент компании *Groupes.ru*.\n"
        "Готов помочь с подбором станков для металлообработки.",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

# === УСЛУГИ ===
@bot.message_handler(func=lambda m: m.text == "ℹ️ Услуги компании")
def show_services(message):
    bot.send_message(message.chat.id, "Выберите раздел:", reply_markup=services_menu())

@bot.message_handler(func=lambda m: m.text in SERVICES)
def handle_service(message):
    bot.send_message(message.chat.id, SERVICES[message.text], parse_mode='Markdown')
    bot.send_message(message.chat.id, "Чем ещё могу помочь?", reply_markup=main_menu())

# === КАТЕГОРИИ ===
@bot.message_handler(func=lambda m: m.text == "📋 Категории")
def show_categories(message):
    if not categories:
        bot.send_message(message.chat.id, "Категории ещё не загружены.")
        return
    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=category_menu())

@bot.message_handler(func=lambda m: m.text in categories.values())
def handle_category(message):
    cat_name = message.text
    cat_id = next((cid for cid, name in categories.items() if name == cat_name), None)
    if not cat_id:
        return

    user_data[message.chat.id] = {"cat_id": cat_id, "cat_name": cat_name}
    user_state[message.chat.id] = "awaiting_params"

    if "фрезер" in cat_name.lower():
        bot.send_message(message.chat.id, "Укажите:\n• Ширина стола (мм)\n• Длина стола (мм)\n• Нагрузка на стол (кг)\n\nПример: *800, 600, 1000*")
    elif "токар" in cat_name.lower():
        bot.send_message(message.chat.id, "Укажите:\n• Макс. диаметр (мм)\n• Макс. длина (мм)\n\nПример: *500, 1500*")
    elif "шлиф" in cat_name.lower():
        bot.send_message(message.chat.id, "Укажите:\n• Длина стола (мм)\n• Ширина стола (мм)\n• Нагрузка (кг)\n\nПример: *600, 300, 270*")
    else:
        # Если нет параметров — показываем все
        items = [p for p in products if p['cat_id'] == cat_id]
        if items:
            for p in items[:10]:
                status = "🟢 В наличии" if p['available'] == 'true' else "⏳ Под заказ"
                bot.send_message(
                    message.chat.id,
                    f"✅ [{p['name']}]({p['link']})\n💰 {p['price']}\n📌 {status}",
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
        else:
            bot.send_message(message.chat.id, f"В категории *{cat_name}* пока нет станков.", parse_mode='Markdown')
        user_state[message.chat.id] = None
        bot.send_message(message.chat.id, "Чем ещё могу помочь?", reply_markup=main_menu())

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "awaiting_params")
def handle_params(message):
    numbers = list(map(float, re.findall(r'\d+', message.text)))
    if not numbers:
        bot.send_message(message.chat.id, "Не удалось извлечь числа. Пример: *800, 600, 1000*")
        return

    cat_id = user_data[message.chat.id]["cat_id"]
    cat_name = user_data[message.chat.id]["cat_name"]
    results = filter_by_params(cat_id, numbers, cat_name)

    if results:
        for p in results:
            status = "🟢 В наличии" if p['available'] == 'true' else "⏳ Под заказ"
            reply = (
                f"🔧 *{p['name']}*\n\n"
                f"{p['description']}\n\n"
                f"💰 {p['price']}\n"
                f"📌 {status}\n"
                f"🔗 [Подробнее на сайте]({p['link']})"
            )
            bot.send_message(message.chat.id, reply, parse_mode='Markdown', disable_web_page_preview=True)
    else:
        bot.send_message(message.chat.id, "Подходящих станков нет. Менеджер предложит решение.")
        bot.send_message(ADMIN_CHAT_ID, f"🔍 Подбор в категории: {cat_name}\nКлиент: {message.from_user.full_name} (ID: {message.chat.id})\nПараметры: {message.text}")

    user_state[message.chat.id] = None
    bot.send_message(message.chat.id, "Чем ещё могу помочь?", reply_markup=main_menu())

# === ПОИСК ПО НАЗВАНИЮ ===
@bot.message_handler(func=lambda m: m.text == "🔍 Поиск по названию")
def ask_name(message):
    user_state[message.chat.id] = "search"
    bot.send_message(message.chat.id, "Введите название или модель (например: *VMC 855*, *Lynx 225*):")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "search")
def handle_search(message):
    results = search_products(message.text)
    if results:
        for p in results:
            status = "🟢 В наличии" if p['available'] == 'true' else "⏳ Под заказ"
            reply = (
                f"🔧 *{p['name']}*\n\n"
                f"{p['description']}\n\n"
                f"💰 {p['price']}\n"
                f"📌 {status}\n"
                f"🔗 [Подробнее на сайте]({p['link']})"
            )
            bot.send_message(message.chat.id, reply, parse_mode='Markdown', disable_web_page_preview=True)
    else:
        bot.send_message(message.chat.id, "Не найдено. Могу связать вас с менеджером.")
        user_state[message.chat.id] = "collect_name"
        bot.send_message(message.chat.id, "Для связи укажите:\n1. Ваше имя")
        return
    user_state[message.chat.id] = None
    bot.send_message(message.chat.id, "Чем ещё могу помочь?", reply_markup=main_menu())

# === ПОДБОР ОБОРУДОВАНИЯ ===
@bot.message_handler(func=lambda m: m.text == "⚙️ Подбор оборудования")
def start_selection(message):
    user_state[message.chat.id] = "choose_type"
    bot.send_message(
        message.chat.id,
        "Какой тип оборудования вас интересует?\n\n"
        "Например: *фрезерный, токарный, шлифовальный*",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "choose_type")
def choose_type(message):
    text = message.text.lower()
    if "фрезер" in text:
        user_data[message.chat.id] = {"type": "фрезер"}
        user_state[message.chat.id] = "params_fres"
        bot.send_message(message.chat.id, "Укажите через запятую:\n• Ширина стола (мм)\n• Длина стола (мм)\n• Нагрузка на стол (кг)\n\nПример: *800, 600, 1000*")
    elif "токар" in text:
        user_data[message.chat.id] = {"type": "токар"}
        user_state[message.chat.id] = "params_tokar"
        bot.send_message(message.chat.id, "Укажите:\n• Макс. диаметр (мм)\n• Макс. длина (мм)\n\nПример: *500, 1500*")
    elif "шлиф" in text:
        user_data[message.chat.id] = {"type": "шлиф"}
        user_state[message.chat.id] = "params_shlif"
        bot.send_message(message.chat.id, "Укажите:\n• Длина стола (мм)\n• Ширина стола (мм)\n• Нагрузка (кг)\n\nПример: *600, 300, 270*")
    else:
        bot.send_message(message.chat.id, "Не распознал тип. Попробуйте: *фрезерный, токарный или шлифовальный*?")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) in ["params_fres", "params_tokar", "params_shlif"])
def handle_params_generic(message):
    numbers = list(map(float, re.findall(r'\d+', message.text)))
    if not numbers:
        bot.send_message(message.chat.id, "Не удалось извлечь числа. Пример: *800, 600, 1000*")
        return

    eq_type = user_data[message.chat.id]["type"]
    def to_num(s):
        try:
            return float(re.sub(r'[^\d.]', '', str(s)))
        except:
            return 0

    results = []
    for p in products:
        params = p['params']
        match = True
        if eq_type == "фрезер":
            if len(numbers) >= 3:
                if to_num(params.get("Ширина стола", "0")) < numbers[0]: match = False
                if to_num(params.get("Длина стола", "0")) < numbers[1]: match = False
                if to_num(params.get("Нагрузка на стол", "0")) < numbers[2]: match = False
        elif eq_type == "токар":
            if len(numbers) >= 2:
                if to_num(params.get("Макс. диаметр обработки", "0")) < numbers[0]: match = False
                if to_num(params.get("Макс. длина обработки", "0")) < numbers[1]: match = False
        elif eq_type == "шлиф":
            if len(numbers) >= 3:
                if to_num(params.get("Ширина стола", "0")) < numbers[1]: match = False
                if to_num(params.get("Длина стола", "0")) < numbers[0]: match = False
                if to_num(params.get("Нагрузка на стол", "0")) < numbers[2]: match = False

        if match:
            results.append(p)
            if len(results) >= 5:
                break

    if results:
        for p in results:
            status = "🟢 В наличии" if p['available'] == 'true' else "⏳ Под заказ"
            reply = (
                f"🔧 *{p['name']}*\n\n"
                f"{p['description']}\n\n"
                f"💰 {p['price']}\n"
                f"📌 {status}\n"
                f"🔗 [Подробнее на сайте]({p['link']})"
            )
            bot.send_message(message.chat.id, reply, parse_mode='Markdown', disable_web_page_preview=True)
    else:
        bot.send_message(message.chat.id, "Подходящих станков нет. Менеджер предложит решение.")
        bot.send_message(ADMIN_CHAT_ID, f"🔍 Подбор по параметрам:\nКлиент: {message.from_user.full_name} (ID: {message.chat.id})\nПараметры: {message.text}")

    user_state[message.chat.id] = None
    bot.send_message(message.chat.id, "Чем ещё могу помочь?", reply_markup=main_menu())

# === СБОР КОНТАКТОВ ===
@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "collect_name")
def collect_name(message):
    user_data[message.chat.id] = {"name": message.text}
    user_state[message.chat.id] = "collect_phone"
    bot.send_message(message.chat.id, "2. Ваш номер телефона")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "collect_phone")
def collect_phone(message):
    user_data[message.chat.id]["phone"] = message.text
    user_state[message.chat.id] = "collect_email"
    bot.send_message(message.chat.id, "3. Email (необязательно)")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "collect_email")
def collect_email(message):
    user_data[message.chat.id]["email"] = message.text or "не указан"
    data = user_data[message.chat.id]
    msg_to_admin = (
        f"📩 Новый запрос от клиента:\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Email: {data['email']}\n"
        f"Вопрос: {message.text}"
    )
    bot.send_message(ADMIN_CHAT_ID, msg_to_admin)
    bot.send_message(message.chat.id, "Спасибо! Менеджер *Максим (@maxim_varganov)* свяжется с вами в течение часа.")
    user_state[message.chat.id] = None
    bot.send_message(message.chat.id, "Чем ещё могу помочь?", reply_markup=main_menu())

# === СВЯЗЬ С МЕНЕДЖЕРОМ ===
@bot.message_handler(func=lambda m: m.text == "📞 Связь с менеджером")
def contact_manager(message):
    user_state[message.chat.id] = "collect_name"
    bot.send_message(message.chat.id, "Для связи укажите:\n1. Ваше имя")

# === НАЗАД ===
@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back_to_main(message):
    bot.send_message(message.chat.id, "Главное меню", reply_markup=main_menu())

# === ЗАПУСК ===
if __name__ == '__main__':
    success = load_catalog()
    if success:
        print("✅ Бот запущен и работает с YML.")
    else:
        print("⚠️ Бот запущен без каталога.")
    bot.polling(none_stop=True)