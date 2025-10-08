
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os, subprocess, threading, time, zipfile, datetime

API_TOKEN = '8148704690:AAFKB7WaeHDDgHqWSqRRBpXbe3Kew1S_yCk'  # <-- Replace with your bot token
ADMIN_ID = 7108706050              # <-- Replace with your Telegram ID
FORCE_JOIN_CHANNEL = "@black_cyber_shield"

bot = telebot.TeleBot(API_TOKEN)
users = {}  # {user_id: {paid: bool, runs: int, banned: bool}}
file_status = {}
running_scripts = {}
ai_logs = []
free_run_limit = 2

if not os.path.exists('uploads'):
    os.makedirs('uploads')

def is_paid(uid): return users.get(uid, {}).get('paid', False)
def is_banned(uid): return users.get(uid, {}).get('banned', False)
def can_run(uid): return not is_banned(uid) and (is_paid(uid) or users.get(uid, {}).get('runs', 0) < free_run_limit)
def increment_run(uid): users.setdefault(uid, {}).update({'runs': users[uid].get('runs', 0) + 1})
def reset_runs(): [users[u].update({'runs': 0}) for u in users]
def send_admin(msg): bot.send_message(ADMIN_ID, msg)

def is_joined(uid):
    try:
        member = bot.get_chat_member(FORCE_JOIN_CHANNEL, uid)
        return member.status in ["member", "administrator", "creator"]
    except: return False

def force_join_check(uid):
    if not is_joined(uid):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔗 Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL.strip('@')}"))
        bot.send_message(uid, "⚠️ বট ব্যবহার করতে আমাদের চ্যানেল join করুন:", reply_markup=markup)
        return False
    return True

def get_user_buttons():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📢 Updates Channel", callback_data="updates"),
        InlineKeyboardButton("📤 Upload File", callback_data="upload"),
        InlineKeyboardButton("📂 Check Files", callback_data="file_manager"),
        InlineKeyboardButton("📊 Statistics", callback_data="stats"),
        InlineKeyboardButton("⚡ Bot Speed", callback_data="speed"),
        InlineKeyboardButton("📞 Contact Owner", callback_data="contact")
    )
    return markup

def get_admin_buttons():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 User List", callback_data="user_list"),
        InlineKeyboardButton("✅ Make Paid", callback_data="make_paid"),
        InlineKeyboardButton("🚫 Ban User", callback_data="ban_user"),
        InlineKeyboardButton("🔓 Unban User", callback_data="unban_user"),
        InlineKeyboardButton("🔄 Reset Runs", callback_data="reset_runs"),
        InlineKeyboardButton("🛠 Set Free Limit", callback_data="set_limit"),
        InlineKeyboardButton("🔍 Find User Info", callback_data="find_user"),
        InlineKeyboardButton("🗑 Delete User Files", callback_data="delete_files"),
        InlineKeyboardButton("📨 Broadcast", callback_data="broadcast")
    )
    return markup

@bot.message_handler(commands=['start'])
def start_handler(msg):
    uid = msg.from_user.id
    if uid not in users:
        users[uid] = {'paid': False, 'runs': 0, 'banned': False}
        send_admin(f"🆕 New User: {msg.from_user.first_name} ({uid})")
    if is_banned(uid): return bot.send_message(uid, "🚫 আপনি ব্যানড।")
    if not force_join_check(uid): return
    bot.send_message(uid, "👋 স্বাগতম! নিচের অপশনগুলো ব্যবহার করুন:", reply_markup=get_user_buttons())

@bot.message_handler(commands=['admin'])
def admin_handler(msg):
    if msg.from_user.id != ADMIN_ID:
        return bot.send_message(msg.chat.id, "❌ আপনি অ্যাডমিন নন।")
    bot.send_message(ADMIN_ID, "🛠 Admin Panel:", reply_markup=get_admin_buttons())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    if not force_join_check(uid): return
    data = call.data

    if data == "speed":
        ping = round((time.time() - call.message.date) * 1000)
        bot.answer_callback_query(call.id, text=f"⚡ {ping}ms")
    elif data == "upload":
        bot.send_message(uid, "📤 .py / .js / .txt / .zip ফাইল পাঠান")
    elif data == "stats":
        u = users.get(uid, {})
        bot.send_message(uid, f"👤 Status: {'Paid ✅' if u.get('paid') else 'Free ❌'}\nRuns: {u.get('runs', 0)} / {free_run_limit}\nBan: {'🚫' if u.get('banned') else '✅'}")
    elif data == "file_manager":
        fs = file_status.get(uid, {})
        bot.send_message(uid, "📂 Files:\n" + "\n".join([f"{f} - {'✅' if s else '❌'}" for f, s in fs.items()]) if fs else "❌ কোনো ফাইল নেই")
    elif data == "contact":
        bot.send_message(uid, "📞 Owner: @BcS_RaiFuL")
    elif data == "updates":
        bot.send_message(uid, f"📢 Join Updates: https://t.me/{FORCE_JOIN_CHANNEL.strip('@')}")
    elif uid == ADMIN_ID:
        if data == "user_list":
            bot.send_message(uid, "\n".join([f"{u} | {'Paid' if i['paid'] else 'Free'} | Runs: {i['runs']} | {'Ban' if i['banned'] else 'OK'}" for u,i in users.items()]) or "❌ No users")
        elif data == "make_paid":
            bot.send_message(uid, "🆔 ইউজার ID দিন যাকে Paid করবেন:"); bot.register_next_step_handler_by_chat_id(uid, lambda m: set_paid(m, True))
        elif data == "ban_user":
            bot.send_message(uid, "🆔 ইউজার ID দিন যাকে Ban করবেন:"); bot.register_next_step_handler_by_chat_id(uid, lambda m: set_ban(m, True))
        elif data == "unban_user":
            bot.send_message(uid, "🆔 ইউজার ID দিন যাকে Unban করবেন:"); bot.register_next_step_handler_by_chat_id(uid, lambda m: set_ban(m, False))
        elif data == "reset_runs":
            reset_runs(); bot.send_message(uid, "✅ সব ইউজারের রান রিসেট হয়েছে।")
        elif data == "set_limit":
            bot.send_message(uid, "🔢 নতুন ফ্রি রান লিমিট দিন:"); bot.register_next_step_handler_by_chat_id(uid, set_limit)
        elif data == "find_user":
            bot.send_message(uid, "🆔 ইউজার ID দিন:"); bot.register_next_step_handler_by_chat_id(uid, find_user)
        elif data == "delete_files":
            bot.send_message(uid, "🆔 ইউজার ID দিন যার ফাইল ডিলিট করতে চান:"); bot.register_next_step_handler_by_chat_id(uid, delete_user_files)
        elif data == "broadcast":
            bot.send_message(uid, "📨 মেসেজ দিন:"); bot.register_next_step_handler_by_chat_id(uid, broadcast_msg)
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['document'])
def handle_doc(msg):
    uid = msg.from_user.id
    if is_banned(uid): return bot.send_message(uid, "🚫 আপনি ব্যানড।")
    if not force_join_check(uid): return
    if not can_run(uid): return bot.send_message(uid, "⚠️ রান সীমা শেষ।")

    ext = msg.document.file_name.split('.')[-1].lower()
    if ext not in ['py', 'js', 'txt', 'zip']:
        return bot.send_message(uid, "❌ ফাইল ফরম্যাট অনুমোদিত নয়।")

    file_info = bot.get_file(msg.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    path = f"uploads/{uid}/{msg.document.file_name}"
    os.makedirs(f"uploads/{uid}", exist_ok=True)
    with open(path, 'wb') as f: f.write(downloaded)

    file_status.setdefault(uid, {})[msg.document.file_name] = True
    bot.send_message(uid, f"✅ ফাইল আপলোড হয়েছে: {msg.document.file_name}")
    try: bot.forward_message(ADMIN_ID, uid, msg.message_id)
    except: pass
    threading.Thread(target=run_code, args=(uid, path, ext)).start()

def run_code(uid, path, ext):
    if uid in running_scripts: return bot.send_message(uid, "⚙️ স্ক্রিপ্ট চলছে...")
    running_scripts[uid] = True
    increment_run(uid)
    ai_logs.append(f"{datetime.datetime.now()} - {uid} ran {os.path.basename(path)}")

    try:
        if ext == 'py':
            # Auto-install requirements (basic parsing)
            with open(path, 'r') as f:
                lines = f.read().splitlines()
            modules = [line.split()[1] for line in lines if line.startswith("import ") or line.startswith("from ")]
            for m in set(modules):
                try: subprocess.run(['pip3', 'install', m], timeout=30)
                except: pass
            res = subprocess.run(['python3', path], capture_output=True, text=True, timeout=60)
        elif ext == 'js':
            res = subprocess.run(['node', path], capture_output=True, text=True, timeout=60)
        elif ext == 'zip':
            extract_dir = path + "_unzipped"
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(path, 'r') as z:
                z.extractall(extract_dir)
            for f in os.listdir(extract_dir):
                if f.endswith('.py'):
                    return run_code(uid, os.path.join(extract_dir, f), 'py')
                elif f.endswith('.js'):
                    return run_code(uid, os.path.join(extract_dir, f), 'js')
            return bot.send_message(uid, "❗️ .zip ফাইলে .py/.js পাওয়া যায়নি।")
        else:
            return bot.send_message(uid, "⚠️ ফাইল ফরম্যাট সাপোর্ট নেই।")

        output = res.stdout.strip() + '\n' + res.stderr.strip()
        bot.send_message(uid, f"📤 Output:\n<pre>{output[:4000]}</pre>", parse_mode="HTML")
    except subprocess.TimeoutExpired:
        bot.send_message(uid, "⏱️ স্ক্রিপ্ট টাইমআউট!")
    except Exception as e:
        bot.send_message(uid, f"❌ Error: {e}")
    running_scripts.pop(uid, None)

def set_paid(msg, val): modify_user_flag(msg, 'paid', val)
def set_ban(msg, val): modify_user_flag(msg, 'banned', val)
def modify_user_flag(msg, key, val):
    try:
        uid = int(msg.text.strip())
        users.setdefault(uid, {'paid': False, 'runs': 0, 'banned': False})
        users[uid][key] = val
        bot.send_message(ADMIN_ID, f"✅ ইউজার {uid} {key} set to {val}")
        bot.send_message(uid, f"🎉 আপনার স্ট্যাটাস পরিবর্তন হয়েছে: {key} = {val}")
    except: bot.send_message(ADMIN_ID, "⚠️ ভুল ID")

def broadcast_msg(msg):
    for u in users:
        try: bot.send_message(u, f"📢 {msg.text}")
        except: continue
    bot.send_message(ADMIN_ID, "✅ ব্রডকাস্ট শেষ।")

def set_limit(msg):
    global free_run_limit
    try:
        free_run_limit = int(msg.text.strip())
        bot.send_message(ADMIN_ID, f"🔄 নতুন রান সীমা: {free_run_limit}")
    except: bot.send_message(ADMIN_ID, "⚠️ সঠিক সংখ্যা দিন।")

def find_user(msg):
    try:
        uid = int(msg.text.strip())
        if uid not in users: return bot.send_message(ADMIN_ID, "❌ ইউজার খুঁজে পাওয়া যায়নি।")
        u = users[uid]
        bot.send_message(ADMIN_ID, f"User: {uid}\nPaid: {u['paid']}\nRuns: {u['runs']}\nBanned: {u['banned']}")
    except: bot.send_message(ADMIN_ID, "⚠️ ভুল ID")

def delete_user_files(msg):
    try:
        uid = int(msg.text.strip())
        folder = f"uploads/{uid}"
        if os.path.exists(folder):
            for f in os.listdir(folder): os.remove(os.path.join(folder, f))
            os.rmdir(folder)
            bot.send_message(ADMIN_ID, "🗑 ফাইল মুছে ফেলা হয়েছে।")
        else: bot.send_message(ADMIN_ID, "❌ কোনো ফাইল পাওয়া যায়নি।")
    except: bot.send_message(ADMIN_ID, "⚠️ ভুল ID")

bot.delete_webhook()
bot.infinity_polling()
