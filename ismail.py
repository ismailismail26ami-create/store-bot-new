import telebot.async_telebot
import asyncio
import json
import os
import threading
from flask import Flask
import libsql_client
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo

# الإعدادات الرئيسية للمتجر (تم وضع التوكن الجديد الخاص بك هنا)
TOKEN = '8955980096:AAHaBDBpQGL59xvAToOSDQeM4Qxz4jtBwI8'
ADMIN_ID = 7339897843
CONTACT_LINK = 'https://t.me/Ismail_Bouarar'                     # حساب تيليجرام الشخصي
CHANNEL_LINK = 'https://t.me/Ismail_Bouarar02'                   # قناة تيليجرام
FEEDBACK_LINK = 'https://t.me/Ismail_Bouarar02'                  # قناة الثقة والآراء
WHATSAPP_LINK = 'https://wa.me/213562161047'                     # رابط واتساب مباشر
FACEBOOK_LINK = 'https://www.facebook.com/profile.php?id=61594681395326' # رابط الفيسبوك

# 🌐 بيانات قاعدة البيانات السحابية (Turso)
TURSO_URL = "libsql://store-db-YOUR_USERNAME.turso.io"
TURSO_TOKEN = "ey...YOUR_TURSO_AUTH_TOKEN"

bot = telebot.async_telebot.AsyncTeleBot(TOKEN)
user_states = {}

# 🌐 إنشاء سيرفر Flask مصغر لإبقاء البوت مستيقظاً على الاستضافات المجانية
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7 successfully!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

async def get_db():
    return libsql_client.create_client_async(url=TURSO_URL, auth_token=TURSO_TOKEN)

async def init_db():
    try:
        async with await get_db() as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS accounts 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, desc TEXT, price TEXT, 
                 media_ids TEXT, media_types TEXT, is_sold INTEGER DEFAULT 0)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS pending_orders 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, desc TEXT, price TEXT, 
                 media_ids TEXT, media_types TEXT)''')
        print("✅ [قاعدة البيانات]: تم الاتصال وتحديث الجداول بنجاح.")
    except Exception as e:
        print(f"❌ [خطأ في قاعدة البيانات]: {e}")

asyncio.run(init_db())

async def notify_all_users(acc_type, price, desc):
    type_names = {
        'ff': '🎮 فري فاير',
        'tt_beta': '🎵 تيك توك بيطا',
        'tt_normal': '🎵 تيك توك عادي',
        'fb_group': '📘 فيسبوك (مجموعة)',
        'fb_page': '📘 فيسبوك (صفحة)'
    }
    category_name = type_names.get(acc_type, "سلعة جديدة")
    
    async with await get_db() as db:
        res = await db.execute("SELECT user_id FROM users")
        users = res.rows
        
    notification_text = (
        f"📢 **تم إضافة سلعة جديدة في المتجر!**\n\n"
        f"📁 **القسم:** {category_name}\n"
        f"💵 **السعر:** {price}\n"
        f"📝 **الوصف:** {desc[:100]}...\n\n"
        f"💡 *ادخل إلى البوت الآن لتصفح التفاصيل والصور!*"
    )
    
    async with await get_db() as db:
        for u in users:
            try:
                await bot.send_message(u[0], notification_text, parse_mode="Markdown")
            except Exception:
                await db.execute("DELETE FROM users WHERE user_id = ?", [u[0]])

def get_acc_markup(acc_id, acc_type, index, total, img_index=0, img_total=1):
    markup = InlineKeyboardMarkup()
    
    if img_total > 1:
        img_nav = []
        prev_img = img_index - 1 if img_index > 0 else img_total - 1
        img_nav.append(InlineKeyboardButton("▶️ الصورة السابقة", callback_data=f"media_{acc_type}_{index}_{prev_img}"))
        img_nav.append(InlineKeyboardButton(f"📷 {img_index+1}/{img_total}", callback_data="ignore"))
        next_img = img_index + 1 if img_index < img_total - 1 else 0
        img_nav.append(InlineKeyboardButton("الصورة التالية ◀️", callback_data=f"media_{acc_type}_{index}_{next_img}"))
        markup.row(*img_nav)

    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{acc_type}_{index-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📦 {index+1}/{total}", callback_data="ignore"))
    if index < total - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"page_{acc_type}_{index+1}"))
    markup.row(*nav_buttons)
    
    markup.row(InlineKeyboardButton("🛒 شراء هذا الحساب", callback_data=f"buy_{acc_id}"))
    markup.row(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu_back"))
    return markup

def main_menu(user_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🎮 فري فاير", callback_data="page_ff_0"))
    markup.row(InlineKeyboardButton("🎵 تيك توك", callback_data="menu_tt"), InlineKeyboardButton("📘 فيسبوك", callback_data="menu_fb"))
    markup.row(InlineKeyboardButton("📋 الحسابات المتوفرة حالياً", callback_data="show_all_available"))
    markup.row(InlineKeyboardButton("🔍 البحث عن حساب برقم ID", callback_data="search_by_id"))
    markup.row(InlineKeyboardButton("➕ إرسال سلعة للبيع", callback_data="user_add_acc"))
    markup.row(InlineKeyboardButton("📦 المبيعات السابقة", callback_data="sold_accs"))
    markup.row(InlineKeyboardButton("⭐ آراء العملاء وثقة المتجر", url=FEEDBACK_LINK))
    markup.row(InlineKeyboardButton("📢 طلبات تم إنجازها (القناة)", url=CHANNEL_LINK))
    markup.row(InlineKeyboardButton("💬 تواصل معي (تليجرام)", url=CONTACT_LINK))
    markup.row(InlineKeyboardButton("🟢 واتساب", url=WHATSAPP_LINK), InlineKeyboardButton("🔵 فيسبوك", url=FACEBOOK_LINK))
    if user_id == ADMIN_ID:
        markup.row(InlineKeyboardButton("🛠 لوحة التحكم", callback_data="admin_panel"))
    return markup

@bot.message_handler(commands=['start'])
async def start_cmd(message):
    async with await get_db() as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", [message.chat.id])
    await bot.send_message(message.chat.id, "👋 أهلاً بك في متجر الحسابات الرقمية! \n\nاختر القسم الذي تريد تصفحه من الأسفل ملاحظة‼️ يرجى التعامل بوسيط لضمان كفاءة البيع والثقة 💰:", reply_markup=main_menu(message.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data == "menu_tt")
async def sub_menu_tt(call):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("⚡ تيك توك بيطا", callback_data="page_tt_beta_0"))
    markup.row(InlineKeyboardButton("🎵 تيك توك عادي", callback_data="page_tt_normal_0"))
    markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu_back"))
    await bot.edit_message_text("🎵 اختر نوع حساب التيك توك:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "menu_fb")
async def sub_menu_fb(call):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("👥 مجموعات فيسبوك", callback_data="page_fb_group_0"))
    markup.row(InlineKeyboardButton("📄 صفحات فيسبوك", callback_data="page_fb_page_0"))
    markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu_back"))
    await bot.edit_message_text("📘 اختر نوع خدمات الفيسبوك:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_all_available")
async def show_all_available_accs(call):
    async with await get_db() as db:
        res = await db.execute("SELECT id, type, price FROM accounts WHERE is_sold=0")
        rows = res.rows
            
    if not rows:
        await bot.answer_callback_query(call.id, "🛒 المتجر فارغ حالياً، لا توجد حسابات معروضة للبيع!", show_alert=True)
        return
        
    type_names = {
        'ff': '🎮 فري فاير',
        'tt_beta': '🎵 تيك توك بيطا',
        'tt_normal': '🎵 تيك توك عادي',
        'fb_group': '📘 مجموعة فيسبوك',
        'fb_page': '📘 صفحة فيسبوك'
    }
    
    text = "📋 قائمة الحسابات المتوفرة حالياً للبيع:\n\n"
    for r in rows:
        name = type_names.get(r[1], 'سلعة')
        text += f"🔹 {name} | الرقم المعرف: {r[0]} | السعر: {r[2]}\n"
    
    text += "\n💡 *لتصفح تفاصيل أي حساب ورؤية صوره، استخدم خيار البحث أو تصفح الأقسام.*"
    await bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "search_by_id")
async def search_by_id_start(call):
    user_states[call.from_user.id] = {'step': 'search_acc_id'}
    await bot.edit_message_text("🔍 أرسل الآن رقم المعرف (ID) الخاص بالحساب للبحث عنه مباشرة:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'search_acc_id')
async def process_search_id(message):
    acc_id = message.text.strip()
    if not acc_id.isdigit():
        await bot.send_message(message.chat.id, "⚠️ يرجى إرسال رقم الـ ID صحيح (أرقام فقط):")
        return

    async with await get_db() as db:
        res = await db.execute("SELECT * FROM accounts WHERE id=? AND is_sold=0", [acc_id])
        rows = res.rows

    if not rows:
        await bot.send_message(message.chat.id, "❌ عذراً، لم يتم العثور على حساب بهذا الرقم أو أنه قد تم بيعه مسبقاً.", reply_markup=main_menu(message.from_user.id))
        user_states.pop(message.from_user.id, None)
        return

    acc = rows[0]
    try:
        media_ids = json.loads(acc[4])
        media_types = json.loads(acc[5])
    except Exception:
        media_ids = [acc[4]]
        media_types = [acc[5]]

    caption = f"📦 تفاصيل الحساب المطلوبة:\n\n🆔 رقم الحساب (ID): {acc[0]}\n📝 الوصف:\n{acc[2]}\n\n💵 السعر: {acc[3]}"
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🛒 شراء هذا الحساب", callback_data=f"buy_{acc[0]}"))
    markup.row(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu_back"))

    if media_types[0] == 'photo':
        await bot.send_photo(message.chat.id, photo=media_ids[0], caption=caption, parse_mode="Markdown", reply_markup=markup)
    else:
        await bot.send_video(message.chat.id, video=media_ids[0], caption=caption, parse_mode="Markdown", reply_markup=markup)
    
    user_states.pop(message.from_user.id, None)

@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
async def admin_panel(call):
    if call.from_user.id != ADMIN_ID: return
    
    async with await get_db() as db:
        res = await db.execute("SELECT COUNT(*) FROM pending_orders")
        count = res.rows[0][0] if res.rows else 0
            
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("➕ إضافة حساب جديد", callback_data="add_acc"))
    markup.row(InlineKeyboardButton(f"📥 مراجعة طلبات السلع ({count})", callback_data="review_pending_0"))
    markup.row(InlineKeyboardButton("✅ تحويل حساب إلى (مباع)", callback_data="set_sold"))
    markup.row(InlineKeyboardButton("❌ حذف حساب نهائياً", callback_data="del_acc"))
    markup.row(InlineKeyboardButton("📢 إرسال إعلان للجميع", callback_data="broadcast"))
    markup.row(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu_back"))
    await bot.edit_message_text(f"🛠 لوحة التحكم الخاصة بالأدمن:\nاختر العملية التي تريد القيام بها:\n\n📥 يوجد حالياً {count} منشورات معلقة بانتظار المراجعة.", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu_back")
async def back_to_menu(call):
    try: 
        await bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception: 
        pass
    await bot.send_message(call.message.chat.id, "اختر القسم الذي تريد تصفحه من الأسفل:", reply_markup=main_menu(call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data in ["add_acc", "user_add_acc"])
async def add_account_start(call):
    if call.data == "add_acc" and call.from_user.id != ADMIN_ID: return
    is_admin = "1" if call.from_user.id == ADMIN_ID and call.data == "add_acc" else "0"
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🎮 فري فاير", callback_data=f"settype_ff_{is_admin}"))
    markup.row(InlineKeyboardButton("🎵 تيك توك بيطا", callback_data=f"settype_tt_beta_{is_admin}"), InlineKeyboardButton("🎵 تيك توك عادي", callback_data=f"settype_tt_normal_{is_admin}"))
    markup.row(InlineKeyboardButton("👥 مجموعة فيسبوك", callback_data=f"settype_fb_group_{is_admin}"), InlineKeyboardButton("📄 صفحة فيسبوك", callback_data=f"settype_fb_page_{is_admin}"))
    await bot.edit_message_text("📁 اختر القسم الذي تريد إضافة السلعة أو المنشور إليه:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("settype_"))
async def process_type(call):
    parts = call.data.split("_")
    is_admin = parts[-1]
    acc_type = "_".join(parts[1:-1])
    
    user_states[call.from_user.id] = {'type': acc_type, 'is_admin': is_admin, 'step': 'desc', 'media_ids': [], 'media_types': []}
    await bot.edit_message_text("📝 الآن أرسل (تفاصيل المنشور أو وصف السلعة) بالتفصيل:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'desc')
async def process_desc(message):
    user_states[message.from_user.id]['desc'] = message.text
    user_states[message.from_user.id]['step'] = 'price'
    await bot.send_message(message.chat.id, "💵 كم السعر المطلوب؟ (مثال: 1500 DA):")

@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'price')
async def process_price(message):
    user_states[message.from_user.id]['price'] = message.text
    user_states[message.from_user.id]['step'] = 'media'
    await bot.send_message(message.chat.id, "🖼️ الآن أرسل (الصورة الأولى أو الفيديو الأول) الخاصة بالسلعة:")

@bot.message_handler(content_types=['photo', 'video'], func=lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'media')
async def process_media(message):
    state_data = user_states.get(message.from_user.id)
    if not state_data: return
    
    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = 'photo'
    else:
        media_id = message.video.file_id
        media_type = 'video'
        
    state_data['media_ids'].append(media_id)
    state_data['media_types'].append(media_type)
    
    if len(state_data['media_ids']) >= 10:
        await finish_adding_media(message.chat.id, message.from_user.id)
        return

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("➕ إضافة صورة/فيديو آخر", callback_data="add_more_media"))
    markup.row(InlineKeyboardButton("✅ إنهاء وحفظ المنشور رسمياً", callback_data="finish_media"))
    await bot.send_message(message.chat.id, f"📸 تم استلام الوسيط رقم ({len(state_data['media_ids'])}). هل تريد إضافة المزيد من الصور التوضيحية لهذا الحساب أم تكتفي بهذا؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "add_more_media")
async def ask_more_media(call):
    await bot.edit_message_text("🖼️ أرسل الآن الصورة التالية أو الفيديو التالي مباشرة:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "finish_media")
async def finish_media_callback(call):
    try:
        await bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    await finish_adding_media(call.message.chat.id, call.from_user.id)

async def finish_adding_media(chat_id, user_id):
    state_data = user_states.get(user_id)
    if not state_data: return
    
    media_ids_json = json.dumps(state_data['media_ids'])
    media_types_json = json.dumps(state_data['media_types'])
    
    if state_data['is_admin'] == "1":
        try:
            async with await get_db() as db:
                await db.execute(
                    "INSERT INTO accounts (type, desc, price, media_ids, media_types) VALUES (?, ?, ?, ?, ?)",
                    [state_data['type'], state_data['desc'], state_data['price'], media_ids_json, media_types_json]
                )
            await bot.send_message(chat_id, "✅ تم حفظ المنشور مع كامل ألبومه وإضافته للمتجر بنجاح!")
            await notify_all_users(state_data['type'], state_data['price'], state_data['desc'])
        except Exception:
            await bot.send_message(chat_id, "❌ حدث خطأ أثناء الحفظ في قاعدة البيانات.")
    else:
        try:
            async with await get_db() as db:
                await db.execute(
                    "INSERT INTO pending_orders (user_id, type, desc, price, media_ids, media_types) VALUES (?, ?, ?, ?, ?, ?)",
                    [user_id, state_data['type'], state_data['desc'], state_data['price'], media_ids_json, media_types_json]
                )
            await bot.send_message(chat_id, "📥 تم إرسال منشورك مع ألبومه بنجاح للأدمن للمراجعة!\nسيتم فحصه ونشره في البوت فوراً إذا كان موافقاً للشروط.")
            await bot.send_message(ADMIN_ID, "🔔 إشعار: زبون جديد قام بتقديم سلعة للبيع، ادخل للوحة التحكم لمراجعتها.")
        except Exception:
            await bot.send_message(chat_id, "❌ فشل إرسال الطلب، يرجى إعادة المحاولة.")
            
    user_states.pop(user_id, None)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_") or call.data.startswith("media_"))
async def show_accounts(call):
    is_media_click = call.data.startswith("media_")
    parts = call.data.split("_")
    
    if is_media_click:
        img_index = int(parts[-1])
        index = int(parts[-2])
        acc_type = "_".join(parts[1:-2])
    else:
        img_index = 0
        index = int(parts[-1])
        acc_type = "_".join(parts[1:-1])
    
    async with await get_db() as db:
        res = await db.execute("SELECT * FROM accounts WHERE type=? AND is_sold=0", [acc_type])
        accs = res.rows
            
    if not accs:
        await bot.answer_callback_query(call.id, "🚫 لا توجد منشورات متوفرة حالياً في هذا القسم!", show_alert=True)
        return
        
    acc = accs[index]
    try:
        media_ids = json.loads(acc[4])
        media_types = json.loads(acc[5])
    except Exception:
        media_ids = [acc[4]]
        media_types = [acc[5]]
        
    if img_index >= len(media_ids): img_index = 0
    
    current_media_id = media_ids[img_index]
    current_media_type = media_types[img_index]
    
    type_names = {
        'ff': 'فري فاير',
        'tt_beta': 'تيك توك بيطا',
        'tt_normal': 'تيك توك عادي',
        'fb_group': 'مجموعة فيسبوك',
        'fb_page': 'صفحة فيسبوك'
    }
    name_ar = type_names.get(acc_type, "السلعة")
    caption = f"📦 حساب {name_ar} متوفر حالياً:\n\n🆔 رقم الحساب (ID): {acc[0]}\n📝 الوصف:\n{acc[2]}\n\n💵 السعر: {acc[3]}"
    
    markup = get_acc_markup(acc[0], acc_type, index, len(accs), img_index, len(media_ids))
    
    try:
        if current_media_type == 'photo':
            await bot.edit_message_media(InputMediaPhoto(current_media_id, caption=caption, parse_mode="Markdown"), call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            await bot.edit_message_media(InputMediaVideo(current_media_id, caption=caption, parse_mode="Markdown"), call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        try: 
            await bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: 
            pass
        if current_media_type == 'photo':
            await bot.send_photo(call.message.chat.id, photo=current_media_id, caption=caption, parse_mode="Markdown", reply_markup=markup)
        else:
            await bot.send_video(call.message.chat.id, video=current_media_id, caption=caption, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("review_pending_") or call.data.startswith("revmed_"))
async def review_pending(call):
    if call.from_user.id != ADMIN_ID: return
    
    is_media_click = call.data.startswith("revmed_")
    parts = call.data.split("_")
    index = int(parts[1]) if not is_media_click else int(parts[2])
    img_index = int(parts[3]) if is_media_click else 0
    
    async with await get_db() as db:
        res = await db.execute("SELECT * FROM pending_orders")
        rows = res.rows
            
    if not rows:
        try: 
            await bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: 
            pass
        await bot.send_message(call.message.chat.id, "📥 لا توجد أي سلع أو منشورات معلقة حالياً لمراجعتها!", reply_markup=main_menu(ADMIN_ID))
        return
        
    if index >= len(rows): index = 0
    row = rows[index]
    order_id, user_id, acc_type, desc, price, media_ids_raw, media_types_raw = row
    
    try:
        media_ids = json.loads(media_ids_raw)
        media_types = json.loads(media_types_raw)
    except Exception:
        media_ids = [media_ids_raw]
        media_types = [media_types_raw]
        
    if img_index >= len(media_ids): img_index = 0
    current_media_id = media_ids[img_index]
    current_media_type = media_types[img_index]
    
    type_names = {
        'ff': 'فري فاير',
        'tt_beta': 'تيك توك بيطا',
        'tt_normal': 'تيك توك عادي',
        'fb_group': 'مجموعة فيسبوك',
        'fb_page': 'صفحة فيسبوك'
    }
    name_ar = type_names.get(acc_type, "السلعة")
    caption = f"📥 مراجعة منشور معلق من زبون:\n\n👤 المرسل ID: {user_id}\n📁 القسم: {name_ar}\n📝 الوصف:\n{desc}\n\n💵 السعر المقترح: {price}\n\n⚙️ اختر قبول المنشور لإضافته رسمياً أو رفضه لحذفه:"
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ قبول ونشر", callback_data=f"accept_{order_id}"),
        InlineKeyboardButton("❌ رفض وحذف", callback_data=f"reject_{order_id}")
    )
    
    if len(media_ids) > 1:
        img_nav = []
        prev_img = img_index - 1 if img_index > 0 else len(media_ids) - 1
        img_nav.append(InlineKeyboardButton("▶️ صورة الطلب السابقة", callback_data=f"revmed_pending_{index}_{prev_img}"))
        img_nav.append(InlineKeyboardButton(f"📷 {img_index+1}/{len(media_ids)}", callback_data="ignore"))
        next_img = img_index + 1 if img_index < len(media_ids) - 1 else 0
        img_nav.append(InlineKeyboardButton("صورة الطلب التالية ◀️", callback_data=f"revmed_pending_{index}_{next_img}"))
        markup.row(*img_nav)

    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"review_pending_{index-1}"))
    nav_buttons.append(InlineKeyboardButton(f"الطلبات: {index+1}/{len(rows)}", callback_data="ignore"))
    if index < len(rows) - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"review_pending_{index+1}"))
    markup.row(*nav_buttons)
    markup.row(InlineKeyboardButton("🛠 العودة للوحة التحكم", callback_data="admin_panel"))
    
    try:
        if current_media_type == 'photo':
            await bot.edit_message_media(InputMediaPhoto(current_media_id, caption=caption), call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            await bot.edit_message_media(InputMediaVideo(current_media_id, caption=caption), call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        try: 
            await bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: 
            pass
        if current_media_type == 'photo':
            await bot.send_photo(call.message.chat.id, photo=current_media_id, caption=caption, reply_markup=markup)
        else:
            await bot.send_video(call.message.chat.id, video=current_media_id, caption=caption, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_"))
async def accept_order(call):
    if call.from_user.id != ADMIN_ID: return
    order_id = int(call.data.split("_")[1])
    
    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM pending_orders WHERE id=?", [order_id])
        rows = cursor.rows
        if rows:
            row = rows[0]
            await db.execute(
                "INSERT INTO accounts (type, desc, price, media_ids, media_types) VALUES (?, ?, ?, ?, ?)",
                [row[2], row[3], row[4], row[5], row[6]]
            )
            await db.execute("DELETE FROM pending_orders WHERE id=?", [order_id])
            row_data = row
        else:
            row_data = None

    if row_data:
        await bot.answer_callback_query(call.id, "✅ تم قبول السلعة ونشرها في المتجر بنجاح!", show_alert=True)
        try: 
            await bot.send_message(row_data[1], "🎉 أخبار سارة! تم مراجعة منشورك وقبوله من طرف الأدمن، وهو الآن معروض للبيع مع كامل صوره داخل البوت.")
        except Exception: 
            pass
        await notify_all_users(row_data[2], row_data[4], row_data[3])
    else:
        await bot.answer_callback_query(call.id, "❌ تعذر العثور على البيانات.")
        
    await review_pending(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
async def reject_order(call):
    if call.from_user.id != ADMIN_ID: return
    order_id = int(call.data.split("_")[1])
    
    async with await get_db() as db:
        cursor = await db.execute("SELECT user_id FROM pending_orders WHERE id=?", [order_id])
        rows = cursor.rows
        user_id = rows[0][0] if rows else None
        await db.execute("DELETE FROM pending_orders WHERE id=?", [order_id])

    await bot.answer_callback_query(call.id, "❌ تم رفض السلعة وحذفها نهائياً.", show_alert=True)
    if user_id:
        try: 
            await bot.send_message(user_id, "⚠️ للاسف، تم رفض منشور السلعة الذي أرسلته من طرف الإدارة.")
        except Exception: 
            pass
    
    await review_pending(call)

@bot.callback_query_handler(func=lambda call: call.data == "set_sold")
async def set_sold_step(call):
    if call.from_user.id != ADMIN_ID: return
    user_states[call.from_user.id] = {'step': 'sell_id'}
    await bot.edit_message_text("🔄 أرسل لي الآن (رقم ID الحساب) الذي قمت ببيعه ليتم إخفاؤه من المتجر:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'sell_id')
async def process_sell_id(message):
    if message.from_user.id != ADMIN_ID: return
    acc_id = message.text.strip()
    if not acc_id.isdigit():
        await bot.send_message(message.chat.id, "⚠️ يرجى إرسال رقم الـ ID صحيح (أرقام فقط):")
        return
    
    user_states[message.from_user.id] = {'step': 'confirm_sell', 'acc_id': acc_id}
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("✅ نعم، متأكد", callback_data="yes_sell"), InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel"))
    await bot.send_message(message.chat.id, f"⚠️ هل أنت متأكد من تحويل الحساب رقم ({acc_id}) إلى قائمة المبيعات (مباع)؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "yes_sell")
async def confirm_sell(call):
    if call.from_user.id != ADMIN_ID: return
    state = user_states.get(call.from_user.id)
    if not state or 'acc_id' not in state: return
    acc_id = state['acc_id']

    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM accounts WHERE id=?", [acc_id])
        if cursor.rows:
            await db.execute("UPDATE accounts SET is_sold=1 WHERE id=?", [acc_id])
            success = True
        else:
            success = False

    if success:
        await bot.send_message(call.message.chat.id, f"✅ تم نقل الحساب رقم {acc_id} إلى المبيعات السابقة بنجاح!")
    else:
        await bot.send_message(call.message.chat.id, f"❌ لم يتم العثور على حساب يحمل الرقم {acc_id} في القاعدة.")
    user_states.pop(call.from_user.id, None)

@bot.callback_query_handler(func=lambda call: call.data == "del_acc")
async def del_acc_step(call):
    if call.from_user.id != ADMIN_ID: return
    user_states[call.from_user.id] = {'step': 'delete_id'}
    await bot.edit_message_text("❌ أرسل لي (رقم ID الحساب) لحذفه نهائياً من المتجر والقاعدة:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'delete_id')
async def process_delete_id(message):
    if message.from_user.id != ADMIN_ID: return
    acc_id = message.text.strip()
    if not acc_id.isdigit():
        await bot.send_message(message.chat.id, "⚠️ يرجى إرسال رقم الـ ID صحيح (أرقام فقط):")
        return

    user_states[message.from_user.id] = {'step': 'confirm_del', 'acc_id': acc_id}
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🗑️ نعم، احذف نهائياً", callback_data="yes_del"), InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel"))
    await bot.send_message(message.chat.id, f"⚠️ تحذير: هل أنت متأكد من حذف الحساب رقم ({acc_id}) نهائياً من قاعدة البيانات؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "yes_del")
async def confirm_del(call):
    if call.from_user.id != ADMIN_ID: return
    state = user_states.get(call.from_user.id)
    if not state or 'acc_id' not in state: return
    acc_id = state['acc_id']

    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM accounts WHERE id=?", [acc_id])
        if cursor.rows:
            await db.execute("DELETE FROM accounts WHERE id=?", [acc_id])
            success = True
        else:
            success = False

    if success:
        await bot.send_message(call.message.chat.id, f"🗑️ تم حذف الحساب رقم {acc_id} نهائياً!")
    else:
        await bot.send_message(call.message.chat.id, f"❌ لم يتم العثور على حساب يحمل الرقم {acc_id} في القاعدة.")
    user_states.pop(call.from_user.id, None)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
async def buy_callback(call):
    acc_id = call.data.split("_")[1]
    user = call.from_user
    username = f"@{user.username}" if user.username else "لا يملك معرف"
    admin_alert = f"🔔 طلب شراء جديد داخل البوت!\n\n👤 الزبون: {user.first_name} ({username})\n🆔 آيدي الزبون: {user.id}\n\n🆔 رقم الحساب المطلوب (ID): {acc_id}\n\n👉 [اضغط هنا لمراسلة الزبون مباشرة](tg://user?id={user.id})"
    await bot.send_message(ADMIN_ID, admin_alert, parse_mode="Markdown")
    await bot.answer_callback_query(call.id, "✅ تم إرسال طلب الشراء للأدمن بنجاح! سيتواصل معك في أقرب وقت لتسليم الحساب.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "broadcast")
async def broadcast_step(call):
    if call.from_user.id != ADMIN_ID: return
    user_states[call.from_user.id] = {'step': 'broadcast_msg'}
    await bot.edit_message_text("📢 أرسل الآن نص الإعلان الذي تريد تعميمه لجميع مستخدمي البوت:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'broadcast_msg')
async def send_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    async with await get_db() as db:
        res = await db.execute("SELECT user_id FROM users")
        users = res.rows
            
    count = 0
    await bot.send_message(message.chat.id, f"⏳ جاري بدء إرسال الإعلان إلى {len(users)} مستخدم...")
    async with await get_db() as db:
        for user in users:
            try:
                await bot.send_message(user[0], message.text)
                count += 1
            except Exception:
                await db.execute("DELETE FROM users WHERE user_id = ?", [user[0]])
                
    await bot.send_message(message.chat.id, f"✅ تم انتهاء الإرسال بنجاح وتعميم المنشور على {count} زبون نشط.")
    user_states.pop(message.from_user.id, None)

@bot.callback_query_handler(func=lambda call: call.data == "sold_accs")
async def show_sold(call):
    async with await get_db() as db:
        res = await db.execute("SELECT * FROM accounts WHERE is_sold=1")
        accs = res.rows
            
    if not accs:
        await bot.answer_callback_query(call.id, "لا توجد مبيعات مؤرشفة بعد داخل البوت!", show_alert=True)
        return
    await bot.send_message(message.chat.id, "📦 هذه قائمة بالحسابات التي تم بيعها سابقاً ومؤرشفة:")
    for acc in accs:
        await bot.send_message(message.chat.id, f"✅ تم بيع حساب رقم: {acc[0]} \n📝 الوصف: {acc[2]}")

if __name__ == '__main__':
    keep_alive()
    print("🚀 [تشغيل الاحترافي مع Flask]: البوت يعمل 24/7 بسلاسة تامة...")
    asyncio.run(bot.infinity_polling(timeout=60, long_polling_timeout=5))
