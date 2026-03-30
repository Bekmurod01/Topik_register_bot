import logging
import os
import asyncio
from typing import Any

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))
ADMIN_THREAD_ID = int(os.getenv("ADMIN_THREAD_ID", "0"))
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "+998 XX XXX XX XX")
ADMIN_TELEGRAM = os.getenv("ADMIN_TELEGRAM", "@admin_username")
PAYMENT_REMINDER_MINUTES = int(os.getenv("PAYMENT_REMINDER_MINUTES", "120"))

WAITING_PDF, WAITING_PAYMENT = range(2)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def user_mention_text(user: Any) -> str:
    if user.full_name:
        return user.full_name
    if user.username:
        return f"@{user.username}"
    return str(user.id)


STEP_1_TEXT = (
    "🇰🇷 Koreys tili (TOPIK) imtihoniga ro‘yxatdan o‘tish\n\n"
    "Ro‘yxatdan o‘tishni boshlash uchun hujjatlaringizni PDF (elektron) formatda yuboring.\n\n"
    "📄 Talablar:\n"
    "• Hujjatlar aniq va o‘qiladigan bo‘lishi kerak\n"
    "• Faqat PDF format qabul qilinadi\n\n"
    "⬇️ Faylni shu yerga yuboring"
)

NOT_PDF_TEXT = "❌ Iltimos, hujjatni faqat PDF formatda yuboring."
START_TEXT_INSTEAD_OF_FILE = "📄 Iltimos, ro‘yxatdan o‘tish uchun hujjatlaringizni PDF formatda yuboring."
ALREADY_SUBMITTED_TEXT = (
    "ℹ️ Siz allaqachon hujjat yuborgansiz.\n\n"
    "Keyingi bosqich — to‘lovni amalga oshirish."
)

PAYMENT_UNDER_REVIEW_TEXT = (
    "ℹ️ Siz to‘lov skrinshotini yuborgansiz.\n\n"
    "Hozir admin tasdiqlashini kuting."
)

CONFIRMATION_TEXT = (
    "✅ Hujjatlaringiz muvaffaqiyatli qabul qilindi!\n\n"
    "Operatorlarimiz hujjatlaringizni ko‘rib chiqmoqda.\n\n"
    "⏳ Keyingi bosqich: to‘lovni amalga oshirish"
)

PAYMENT_TEXT = (
    "💳 To‘lov ma’lumotlari\n\n"
    "Karta raqami:\n"
    "5614 6818 1895 2651\n\n"
    "Qabul qiluvchi:\n"
    "Mamataliyev Bekmurod\n\n"
    "💰 To‘lov miqdori:\n"
    "• Koreys tili imtihoni: 400 000 so‘m\n"
    "• Xizmat narxi: 100 000 so‘m\n\n"
    "Jami: 500 000 so‘m\n\n"
    "📌 To‘lovni amalga oshirgandan so‘ng, iltimos, to‘lov chekini (skrinshot) shu yerga yuboring."
)

ADMIN_CONTACT_TEXT = (
    "👨‍💼 Admin bilan bog‘lanish\n\n"
    "Savollar bo‘lsa, admin bilan bog‘laning:\n"
    f"📱 Telefon: {ADMIN_PHONE}\n"
    f"📩 Telegram: {ADMIN_TELEGRAM}\n"
    "⏰ Ish vaqti: 09:00 – 18:00"
)

PAYMENT_RECEIVED_TEXT = (
    "✅ To‘lov skrinshoti qabul qilindi!\n\n"
    "To‘lovingiz tekshirilmoqda. Tasdiqlangandan so‘ng sizga xabar beriladi.\n\n"
    "🙏 Sabringiz uchun rahmat!"
)

PAYMENT_DELAY_TEXT = "⏰ Eslatma: ro‘yxatdan o‘tishni yakunlash uchun to‘lovni amalga oshirishingiz kerak."
ADMIN_FORWARD_ERROR_TEXT = (
    "⚠️ Hujjat yuborishda texnik muammo yuz berdi. "
    "Iltimos, birozdan so‘ng qayta urinib ko‘ring yoki admin bilan bog‘laning."
)

PAYMENT_FORWARD_ERROR_TEXT = (
    "⚠️ To‘lov skrinshotini yuborishda texnik muammo yuz berdi. "
    "Iltimos, birozdan so‘ng qayta yuboring yoki admin bilan bog‘laning."
)

USER_PDF_APPROVED_TEXT = "✅ Hujjatingiz admin tomonidan tasdiqlandi."
USER_PAYMENT_APPROVED_TEXT = (
    "✅ To‘lovingiz admin tomonidan tasdiqlandi. "
    "Ro‘yxatdan o‘tish muvaffaqiyatli yakunlandi."
)
USER_PDF_REJECTED_TEXT = (
    "❌ Hujjatingiz admin tomonidan rad etildi. "
    "Iltimos, hujjatlaringizni to‘g‘rilab qayta yuboring."
)
USER_PAYMENT_REJECTED_TEXT = (
    "❌ To‘lov skrinshoti admin tomonidan rad etildi. "
    "Iltimos, to‘lovni tekshirib qayta skrinshot yuboring."
)


def admin_contact_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton("📞 Admin bilan bog‘lanish")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def approval_button(user_id: int, stage: str) -> InlineKeyboardMarkup:
    keyboard = [[
        InlineKeyboardButton("✅ Tasdiqlandi", callback_data=f"approve:{stage}:{user_id}"),
        InlineKeyboardButton("❌ Rad etildi", callback_data=f"reject:{stage}:{user_id}"),
    ]]
    return InlineKeyboardMarkup(keyboard)


def admin_target_kwargs() -> dict[str, int]:
    target = {"chat_id": ADMIN_GROUP_ID}
    if ADMIN_THREAD_ID:
        target["message_thread_id"] = ADMIN_THREAD_ID
    return target


async def validate_admin_target(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        chat = await context.bot.get_chat(ADMIN_GROUP_ID)
        logger.info("Admin target chat validated: id=%s type=%s", chat.id, chat.type)
    except TelegramError as e:
        raise RuntimeError(
            "ADMIN_GROUP_ID noto'g'ri yoki bot admin guruhga qo'shilmagan. "
            "Guruhga botni qo'shing, /chatid orqali ID ni oling va .env ni yangilang. "
            f"Telegram xabari: {e}"
        ) from e


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data

    # If previous registration was fully approved, start a fresh flow.
    if user_data.get("last_registration_approved"):
        user_data["submitted_pdf"] = False
        user_data["awaiting_payment"] = False
        user_data["payment_submitted"] = False
        user_data["last_registration_approved"] = False

    if user_data.get("submitted_pdf"):
        if user_data.get("payment_submitted"):
            await update.effective_message.reply_text(PAYMENT_UNDER_REVIEW_TEXT, reply_markup=admin_contact_menu_keyboard())
        else:
            await update.effective_message.reply_text(ALREADY_SUBMITTED_TEXT, reply_markup=admin_contact_menu_keyboard())
        return WAITING_PAYMENT

    user_data["submitted_pdf"] = False
    user_data["awaiting_payment"] = False
    user_data["payment_submitted"] = False

    await update.effective_message.reply_text(STEP_1_TEXT, reply_markup=admin_contact_menu_keyboard())
    return WAITING_PDF


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    await update.effective_message.reply_text(
        f"Chat ID: {chat.id}\nType: {chat.type}"
    )


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    user = update.effective_user
    user_data = context.user_data

    if user_data.get("submitted_pdf"):
        await message.reply_text(ALREADY_SUBMITTED_TEXT)
        return WAITING_PAYMENT

    document = message.document
    is_pdf = bool(document and (
        (document.mime_type and document.mime_type.lower() == "application/pdf")
        or (document.file_name and document.file_name.lower().endswith(".pdf"))
    ))

    if not is_pdf:
        await message.reply_text(NOT_PDF_TEXT)
        return WAITING_PDF

    applicant = user_mention_text(user)
    caption = (
        "📥 Yangi ro‘yxatdan o‘tish arizasi\n\n"
        f"👤 Foydalanuvchi: {applicant}\n"
        f"🆔 ID: {user.id}\n\n"
        "📄 Hujjat biriktirildi"
    )

    target = admin_target_kwargs()
    approval_markup = approval_button(user.id, "pdf")
    try:
        await context.bot.send_document(
            document=document.file_id,
            caption=caption,
            reply_markup=approval_markup,
            **target,
        )
    except TelegramError as e:
        if "message_thread_id" in target:
            logger.warning("Forward with thread failed, retrying without thread: %s", e)
            try:
                await context.bot.send_document(
                    chat_id=ADMIN_GROUP_ID,
                    document=document.file_id,
                    caption=caption,
                    reply_markup=approval_markup,
                )
            except TelegramError:
                logger.exception("Failed to forward registration PDF to admin group")
                await message.reply_text(ADMIN_FORWARD_ERROR_TEXT)
                return WAITING_PDF
        else:
            logger.exception("Failed to forward registration PDF to admin group")
            await message.reply_text(ADMIN_FORWARD_ERROR_TEXT)
            return WAITING_PDF

    user_data["submitted_pdf"] = True
    user_data["awaiting_payment"] = True

    await message.reply_text(CONFIRMATION_TEXT, reply_markup=admin_contact_menu_keyboard())
    await message.reply_text(PAYMENT_TEXT)

    schedule_payment_reminder(update, context)
    return WAITING_PAYMENT


async def handle_text_before_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(START_TEXT_INSTEAD_OF_FILE, reply_markup=admin_contact_menu_keyboard())
    return WAITING_PDF


async def handle_admin_contact_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(ADMIN_CONTACT_TEXT, reply_markup=admin_contact_menu_keyboard())
    if context.user_data.get("submitted_pdf"):
        return WAITING_PAYMENT
    return WAITING_PDF


async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    user = update.effective_user
    user_data = context.user_data

    if not user_data.get("submitted_pdf"):
        await message.reply_text(START_TEXT_INSTEAD_OF_FILE)
        return WAITING_PDF

    applicant = user_mention_text(user)
    caption = (
        "💳 To‘lov skrinshoti\n\n"
        f"👤 Foydalanuvchi: {applicant}\n"
        f"🆔 ID: {user.id}\n\n"
        "📌 To‘lov tekshirish uchun yuborildi"
    )

    target = admin_target_kwargs()
    approval_markup = approval_button(user.id, "payment")

    if message.photo:
        try:
            await context.bot.send_photo(
                photo=message.photo[-1].file_id,
                caption=caption,
                reply_markup=approval_markup,
                **target,
            )
        except TelegramError as e:
            if "message_thread_id" in target:
                logger.warning("Payment photo forward with thread failed, retrying without thread: %s", e)
                try:
                    await context.bot.send_photo(
                        chat_id=ADMIN_GROUP_ID,
                        photo=message.photo[-1].file_id,
                        caption=caption,
                        reply_markup=approval_markup,
                    )
                except TelegramError:
                    logger.exception("Failed to forward payment screenshot to admin group")
                    await message.reply_text(PAYMENT_FORWARD_ERROR_TEXT)
                    return WAITING_PAYMENT
            else:
                logger.exception("Failed to forward payment screenshot to admin group")
                await message.reply_text(PAYMENT_FORWARD_ERROR_TEXT)
                return WAITING_PAYMENT
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        try:
            await context.bot.send_document(
                document=message.document.file_id,
                caption=caption,
                reply_markup=approval_markup,
                **target,
            )
        except TelegramError as e:
            if "message_thread_id" in target:
                logger.warning("Payment document forward with thread failed, retrying without thread: %s", e)
                try:
                    await context.bot.send_document(
                        chat_id=ADMIN_GROUP_ID,
                        document=message.document.file_id,
                        caption=caption,
                        reply_markup=approval_markup,
                    )
                except TelegramError:
                    logger.exception("Failed to forward payment image document to admin group")
                    await message.reply_text(PAYMENT_FORWARD_ERROR_TEXT)
                    return WAITING_PAYMENT
            else:
                logger.exception("Failed to forward payment image document to admin group")
                await message.reply_text(PAYMENT_FORWARD_ERROR_TEXT)
                return WAITING_PAYMENT
    else:
        await message.reply_text(PAYMENT_DELAY_TEXT)
        return WAITING_PAYMENT

    user_data["awaiting_payment"] = False
    user_data["payment_submitted"] = True

    await message.reply_text(PAYMENT_RECEIVED_TEXT, reply_markup=admin_contact_menu_keyboard())
    return WAITING_PAYMENT


async def handle_waiting_payment_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(PAYMENT_DELAY_TEXT, reply_markup=admin_contact_menu_keyboard())
    return WAITING_PAYMENT


async def admin_decision_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return

    parts = query.data.split(":")
    if len(parts) != 3:
        return

    action, stage, user_id_raw = parts
    if action not in {"approve", "reject"}:
        return

    await query.answer("Tasdiqlandi" if action == "approve" else "Rad etildi")

    try:
        user_id = int(user_id_raw)
    except ValueError:
        return

    target_user_data = context.application.user_data[user_id]

    if action == "approve":
        if stage == "pdf":
            target_user_data["submitted_pdf"] = True
            target_user_data["awaiting_payment"] = True
            target_user_data["payment_submitted"] = False
            notification_text = USER_PDF_APPROVED_TEXT
        else:
            target_user_data["submitted_pdf"] = False
            target_user_data["awaiting_payment"] = False
            target_user_data["payment_submitted"] = False
            target_user_data["last_registration_approved"] = True
            notification_text = USER_PAYMENT_APPROVED_TEXT
    else:
        if stage == "pdf":
            target_user_data["submitted_pdf"] = False
            target_user_data["awaiting_payment"] = False
            target_user_data["payment_submitted"] = False
            target_user_data["last_registration_approved"] = False
            notification_text = USER_PDF_REJECTED_TEXT
        else:
            target_user_data["submitted_pdf"] = True
            target_user_data["awaiting_payment"] = True
            target_user_data["payment_submitted"] = False
            target_user_data["last_registration_approved"] = False
            notification_text = USER_PAYMENT_REJECTED_TEXT

    try:
        await context.bot.send_message(chat_id=user_id, text=notification_text)
    except TelegramError:
        logger.exception("Failed to notify user about admin decision: action=%s stage=%s user_id=%s", action, stage, user_id)

    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except TelegramError:
        logger.exception("Failed to clear admin decision buttons in admin group")


def schedule_payment_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if context.job_queue is None:
        return

    job_name = f"payment-reminder-{user_id}"
    existing_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in existing_jobs:
        job.schedule_removal()

    context.job_queue.run_once(
        send_payment_reminder,
        when=PAYMENT_REMINDER_MINUTES * 60,
        name=job_name,
        chat_id=user_id,
        data={"user_id": user_id},
    )


async def send_payment_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = context.job.data["user_id"]
    user_data = context.application.user_data.get(user_id, {})

    if user_data.get("awaiting_payment") and not user_data.get("payment_submitted"):
        await context.bot.send_message(chat_id=user_id, text=PAYMENT_DELAY_TEXT)


def build_app() -> Application:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN topilmadi. .env faylida BOT_TOKEN ni sozlang.")
    if not ADMIN_GROUP_ID:
        raise ValueError("ADMIN_GROUP_ID topilmadi. .env faylida ADMIN_GROUP_ID ni sozlang.")

    persistence = PicklePersistence(filepath="bot_state.pkl")
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .post_init(validate_admin_target)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_PDF: [
                MessageHandler(filters.Regex(r"^📞 Admin bilan bog‘lanish$"), handle_admin_contact_menu),
                MessageHandler(filters.Document.ALL, handle_pdf),
                MessageHandler((filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO | filters.VIDEO) & ~filters.COMMAND, handle_text_before_pdf),
            ],
            WAITING_PAYMENT: [
                MessageHandler(filters.Regex(r"^📞 Admin bilan bog‘lanish$"), handle_admin_contact_menu),
                MessageHandler(filters.PHOTO, handle_payment_screenshot),
                MessageHandler(filters.Document.IMAGE, handle_payment_screenshot),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_waiting_payment_text),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        name="topik-registration-flow",
        persistent=True,
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("chatid", chat_id))
    application.add_handler(CallbackQueryHandler(admin_decision_button, pattern="^(approve|reject):"))

    return application


def main() -> None:
    app = build_app()
    # Python 3.14 da default loop avtomatik yaratilmaydi, shuning uchun qo'lda beramiz.
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
