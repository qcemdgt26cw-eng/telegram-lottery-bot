import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from bot.db import (
    init_db,
    register_member,
    candidates,
    cast_vote,
    add_candidate,
    start_vote,
    end_vote,
    results_db,
    draw_winner,
    status,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL = os.environ.get("CHANNEL_USERNAME", "@QCMaste")

ADMIN_IDS = {
    int(x.strip())
    for x in os.environ.get("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}


def is_admin(user_id):
    return user_id in ADMIN_IDS


async def is_channel_member(context, user_id):
    try:
        member = await context.bot.get_chat_member(
            CHANNEL,
            user_id
        )

        return member.status in {
            "creator",
            "administrator",
            "member"
        }

    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not await is_channel_member(context, user.id):

        keyboard = [
            [
                InlineKeyboardButton(
                    "📢 عضویت در کانال",
                    url=f"https://t.me/{CHANNEL.lstrip('@')}"
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ بررسی عضویت",
                    callback_data="check_member"
                )
            ]
        ]

        await update.message.reply_text(
            "برای ثبت‌نام ابتدا عضو کانال QCMaste شوید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    number = register_member(
        user.id,
        user.username,
        user.first_name
    )

    await update.message.reply_text(
        f"✅ ثبت‌نام شما با موفقیت انجام شد.\n\n"
        f"🎫 شماره شرکت: {number}"
    )


async def check_member(update, context):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    if await is_channel_member(context, user.id):

        number = register_member(
            user.id,
            user.username,
            user.first_name
        )

        await query.edit_message_text(
            f"✅ عضویت شما تأیید شد.\n\n"
            f"🎫 شماره شرکت: {number}"
        )

    else:

        await query.edit_message_text(
            "❌ هنوز عضویت شما در کانال تأیید نشده است.\n"
            "ابتدا عضو کانال شوید و دوباره بررسی کنید."
        )


async def vote(update, context):

    current_status = status()

    if current_status["phase"] != "voting":

        await update.message.reply_text(
            "⏳ در حال حاضر رأی‌گیری فعال نیست."
        )

        return

    user = update.effective_user

    if not await is_channel_member(context, user.id):

        await update.message.reply_text(
            "❌ برای رأی دادن باید عضو کانال باشید."
        )

        return

    register_member(
        user.id,
        user.username,
        user.first_name
    )

    candidate_list = candidates()

    if not candidate_list:

        await update.message.reply_text(
            "❌ هنوز نامزدی برای رأی‌گیری ثبت نشده است."
        )

        return

    keyboard = []

    for candidate in candidate_list:

        keyboard.append(
            [
                InlineKeyboardButton(
                    candidate[1],
                    callback_data=f"vote:{candidate[0]}"
                )
            ]
        )

    await update.message.reply_text(
        "🗳️ لطفاً نامزد موردنظر خود را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def vote_callback(update, context):

    query = update.callback_query

    await query.answer()

    candidate_id = int(
        query.data.split(":")[1]
    )

    success, message = cast_vote(
        query.from_user.id,
        candidate_id
    )

    await query.edit_message_text(message)


async def addcandidate(update, context):

    if not is_admin(update.effective_user.id):
        return

    name = " ".join(context.args).strip()

    if not name:

        await update.message.reply_text(
            "مثال:\n/addcandidate علی رضایی"
        )

        return

    add_candidate(name)

    await update.message.reply_text(
        f"✅ نامزد «{name}» اضافه شد."
    )


async def startvote(update, context):

    if not is_admin(update.effective_user.id):
        return

    start_vote()

    await update.message.reply_text(
        "🗳️ رأی‌گیری شروع شد."
    )


async def endvote(update, context):

    if not is_admin(update.effective_user.id):
        return

    end_vote()

    await update.message.reply_text(
        "🛑 رأی‌گیری پایان یافت."
    )


async def results(update, context):

    if not is_admin(update.effective_user.id):
        return

    rows = results_db()

    if not rows:

        await update.message.reply_text(
            "📊 هنوز نتیجه‌ای وجود ندارد."
        )

        return

    text = "📊 نتایج رأی‌گیری:\n\n"

    for row in rows:

        text += (
            f"👤 {row[1]}\n"
            f"🗳️ تعداد رأی: {row[2]}\n\n"
        )

    await update.message.reply_text(text)


async def draw(update, context):

    if not is_admin(update.effective_user.id):
        return

    current_status = status()

    if current_status["phase"] != "ended":

        await update.message.reply_text(
            "⚠️ ابتدا رأی‌گیری را با /endvote پایان دهید."
        )

        return

    winner = draw_winner()

    if not winner:

        await update.message.reply_text(
            "❌ قرعه‌کشی انجام نشد؛ رأی معتبر وجود ندارد."
        )

        return

    await update.message.reply_text(
        "🎉 برنده قرعه‌کشی\n\n"
        f"👤 نام: {winner['name']}\n"
        f"🗳️ رأی: {winner['votes']}\n"
        f"🔐 شناسه قرعه‌کشی: {winner['draw_id']}"
    )


async def bot_status(update, context):

    current_status = status()

    await update.message.reply_text(
        "📊 وضعیت ربات\n\n"
        f"مرحله: {current_status['phase']}\n"
        f"👥 اعضای ثبت‌شده: {current_status['members']}\n"
        f"👤 نامزدها: {current_status['candidates']}\n"
        f"🗳️ رأی‌ها: {current_status['votes']}"
    )


async def admin_help(update, context):

    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "👑 دستورات مدیریت:\n\n"
        "/addcandidate نام\n"
        "/startvote\n"
        "/endvote\n"
        "/results\n"
        "/draw\n"
        "/status"
    )


def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN تنظیم نشده است."
        )

    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("vote", vote)
    )

    application.add_handler(
        CommandHandler("admin", admin_help)
    )

    application.add_handler(
        CommandHandler("addcandidate", addcandidate)
    )

    application.add_handler(
        CommandHandler("startvote", startvote)
    )

    application.add_handler(
        CommandHandler("endvote", endvote)
    )

    application.add_handler(
        CommandHandler("results", results)
    )

    application.add_handler(
        CommandHandler("draw", draw)
    )

    application.add_handler(
        CommandHandler("status", bot_status)
    )

    application.add_handler(
        CallbackQueryHandler(
            check_member,
            pattern="^check_member$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            vote_callback,
            pattern="^vote:"
        )
    )

    logging.info("Telegram bot started")

    application.run_polling()


if __name__ == "__main__":
    main()
