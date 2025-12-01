import os
import sqlite3
from datetime import datetime, date
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask, request

DB = "finance.db"
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app_flask = Flask(__name__)

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount REAL,
        category TEXT,
        note TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS debts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        person TEXT,
        side TEXT,
        amount REAL,
        note TEXT,
        created_at TEXT,
        is_closed INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS fixed_expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        amount REAL,
        day_of_month INTEGER,
        note TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

def db_execute(query, params=(), fetch=False):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return rows

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "هلا! هذا بوت مصروفاتك الشخصي.\n\n"
        "الأوامر:\n"
        "/income مبلغ ملاحظة\n"
        "/expense مبلغ ملاحظة\n"
        "/balance\n"
        "/summary\n"
        "/debt_owe مبلغ الشخص ملاحظة\n"
        "/debt_due مبلغ الشخص ملاحظة\n"
        "/debt_pay مبلغ الشخص\n"
        "/debts\n"
        "/fixed_add مبلغ العنوان اليوم_بالشهر\n"
        "/fixed_list\n"
    )
    await update.message.reply_text(text)

async def income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 1:
        return await update.message.reply_text("اكتبها: /income 25000 راتب")

    amount = float(context.args[0])
    note = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    db_execute(
        "INSERT INTO transactions(user_id,type,amount,category,note,created_at) VALUES(?,?,?,?,?,?)",
        (user_id, "income", amount, "income", note, now_str())
    )
    await update.message.reply_text(f"✅ دخل: {amount:.0f} دينار. {note}")

async def expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 1:
        return await update.message.reply_text("اكتبها: /expense 7000 غداء")

    amount = float(context.args[0])
    note = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    db_execute(
        "INSERT INTO transactions(user_id,type,amount,category,note,created_at) VALUES(?,?,?,?,?,?)",
        (user_id, "expense", amount, "expense", note, now_str())
    )
    await update.message.reply_text(f"✅ صرف: {amount:.0f} دينار. {note}")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rows = db_execute(
        "SELECT type, SUM(amount) FROM transactions WHERE user_id=? GROUP BY type",
        (user_id,), fetch=True
    )
    inc = exp = 0
    for t, s in rows:
        if t == "income": inc = s or 0
        if t == "expense": exp = s or 0
    bal = inc - exp
    await update.message.reply_text(
        f"💰 الرصيد الحالي:\n"
        f"الدخل: {inc:.0f}\n"
        f"الصرف: {exp:.0f}\n"
        f"الرصيد: {bal:.0f} دينار"
    )

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    start_month = date.today().replace(day=1).strftime("%Y-%m-%d")
    rows = db_execute(
        """
        SELECT type, SUM(amount)
        FROM transactions
        WHERE user_id=? AND date(created_at) >= ?
        GROUP BY type
        """,
        (user_id, start_month), fetch=True
    )
    inc = exp = 0
    for t, s in rows:
        if t == "income": inc = s or 0
        if t == "expense": exp = s or 0
    await update.message.reply_text(
        f"📊 ملخص هذا الشهر:\n"
        f"الدخل: {inc:.0f}\n"
        f"الصرف: {exp:.0f}\n"
        f"الصافي: {(inc-exp):.0f} دينار"
    )

async def debt_owe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 2:
        return await update.message.reply_text("اكتبها: /debt_owe 50000 أحمد ملاحظة")

    amount = float(context.args[0])
    person = context.args[1]
    note = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    db_execute(
        "INSERT INTO debts(user_id,person,side,amount,note,created_at) VALUES(?,?,?,?,?,?)",
        (user_id, person, "owe", amount, note, now_str())
    )
    await update.message.reply_text(f"🧾 دين عليك لـ {person}: {amount:.0f} دينار. {note}")

async def debt_due(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 2:
        return await update.message.reply_text("اكتبها: /debt_due 30000 حسن ملاحظة")

    amount = float(context.args[0])
    person = context.args[1]
    note = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    db_execute(
        "INSERT INTO debts(user_id,person,side,amount,note,created_at) VALUES(?,?,?,?,?,?)",
        (user_id, person, "due", amount, note, now_str())
    )
    await update.message.reply_text(f"🧾 دين إلك من {person}: {amount:.0f} دينار. {note}")

async def debt_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 2:
        return await update.message.reply_text("اكتبها: /debt_pay 20000 أحمد")

    pay_amount = float(context.args[0])
    person = context.args[1]

    rows = db_execute(
        """
        SELECT id, amount FROM debts
        WHERE user_id=? AND person=? AND side='owe' AND is_closed=0
        ORDER BY id DESC LIMIT 1
        """,
        (user_id, person), fetch=True
    )
    if not rows:
        return await update.message.reply_text("ماكو دين مفتوح عليك لهالشخص.")

    debt_id, debt_amount = rows[0]
    new_amount = debt_amount - pay_amount

    if new_amount <= 0:
        db_execute("UPDATE debts SET amount=0, is_closed=1 WHERE id=?", (debt_id,))
        await update.message.reply_text(f"✅ سددت الدين بالكامل لـ {person}.")
    else:
        db_execute("UPDATE debts SET amount=? WHERE id=?", (new_amount, debt_id))
        await update.message.reply_text(
            f"✅ دفعت {pay_amount:.0f} لـ {person}.\n"
            f"باقي عليك: {new_amount:.0f} دينار"
        )

async def debts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rows = db_execute(
        """
        SELECT person, side, amount, note
        FROM debts
        WHERE user_id=? AND is_closed=0
        ORDER BY created_at DESC
        """,
        (user_id,), fetch=True
    )
    if not rows:
        return await update.message.reply_text("✅ ما عندك ديون مفتوحة.")

    owe_list, due_list = [], []
    for person, side, amount, note in rows:
        line = f"- {person}: {amount:.0f} ({note})"
        (owe_list if side == "owe" else due_list).append(line)

    text = "📌 الديون المفتوحة:\n"
    if owe_list:
        text += "\n**عليك:**\n" + "\n".join(owe_list) + "\n"
    if due_list:
        text += "\n**إلك:**\n" + "\n".join(due_list)

    await update.message.reply_text(text, parse_mode="Markdown")

async def fixed_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 3:
        return await update.message.reply_text("اكتبها: /fixed_add 20000 نت 15")

    amount = float(context.args[0])
    title = context.args[1]
    day = int(context.args[2])
    note = " ".join(context.args[3:]) if len(context.args) > 3 else ""

    db_execute(
        "INSERT INTO fixed_expenses(user_id,title,amount,day_of_month,note,created_at) VALUES(?,?,?,?,?,?)",
        (user_id, title, amount, day, note, now_str())
    )
    await update.message.reply_text(f"📌 مصروف ثابت: {title} {amount:.0f} يوم {day}")

async def fixed_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rows = db_execute(
        "SELECT title, amount, day_of_month, note FROM fixed_expenses WHERE user_id=? ORDER BY day_of_month",
        (user_id,), fetch=True
    )
    if not rows:
        return await update.message.reply_text("ما عندك مصاريف ثابتة بعد.")

    text = "📅 مصاريفك الثابتة:\n"
    for title, amount, day, note in rows:
        text += f"- {title}: {amount:.0f} دينار (يوم {day}) {note}\n"
    await update.message.reply_text(text)

tg_app = Application.builder().token(TOKEN).build()
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("income", income))
tg_app.add_handler(CommandHandler("expense", expense))
tg_app.add_handler(CommandHandler("balance", balance))
tg_app.add_handler(CommandHandler("summary", summary))
tg_app.add_handler(CommandHandler("debt_owe", debt_owe))
tg_app.add_handler(CommandHandler("debt_due", debt_due))
tg_app.add_handler(CommandHandler("debt_pay", debt_pay))
tg_app.add_handler(CommandHandler("debts", debts))
tg_app.add_handler(CommandHandler("fixed_add", fixed_add))
tg_app.add_handler(CommandHandler("fixed_list", fixed_list))

@app_flask.get("/")
def home():
    return "ok"

@app_flask.post("/webhook")
def webhook():
    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    tg_app.update_queue.put_nowait(update)
    return "ok"

async def on_startup(app: Application):
    await app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

def main():
    init_db()
    tg_app.post_init = on_startup
    tg_app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=f"{WEBHOOK_URL}/webhook"
    )

if __name__ == "__main__":
    main()
