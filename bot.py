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

# Keep existing state IDs stable for persisted conversations.
WAITING_PDF, WAITING_PAYMENT = range(2)
WAITING_NAME, WAITING_PHONE = 2, 3
WAITING_PDF_CONFIRM = 4

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
    "📄 Iltimos, hujjatlaringizni PDF formatda yuboring."
)

WELCOME_NAME_TEXT = (
    "Assalomu alaykum! 🇰🇷 TOPIK ro‘yxatdan o‘tish botiga xush kelibsiz.\n\n"
    "Davom etish uchun, iltimos, ismingizni kiriting."
)

ASK_PHONE_TEXT = "📱 Iltimos, telefon raqamingizni yuboring"
PROFILE_SAVED_TEXT = (
    "✅ Ma’lumotlaringiz qabul qilindi!\n\n"
    "Endi ro‘yxatdan o‘tishni davom ettirishingiz mumkin."
)

NAME_INVALID_TEXT = "✍️ Iltimos, ismingizni matn ko‘rinishida kiriting."
PHONE_REQUEST_TEXT = "📲 Telefon raqamingizni tugma orqali yuboring."
PHONE_OWN_CONTACT_TEXT = "❗ Iltimos, faqat o‘zingizning telefon raqamingizni yuboring."

MENU_NEW_APPLICATION = "📌 Yangi ariza"
MENU_ADMIN_CONTACT = "📞 Admin bilan bog‘lanish"

NOT_PDF_TEXT = "❌ Iltimos, hujjatni faqat PDF formatda yuboring."
START_TEXT_INSTEAD_OF_FILE = "📄 Iltimos, ro‘yxatdan o‘tish uchun hujjatlaringizni PDF formatda yuboring."
ASK_ANOTHER_PDF_TEXT = "📎 Yana PDF hujjat yubormoqchimisiz?"
SEND_ANOTHER_PDF_TEXT = "📄 Yana PDF faylni yuboring."
ALL_PDFS_RECEIVED_TEXT = "✅ Barcha hujjatlar qabul qilindi."
YES_BUTTON_TEXT = "✅ Ha"
NO_BUTTON_TEXT = "❌ Yo‘q"
PDF_ONLY_ERROR_TEXT = "❌ Iltimos, faqat PDF formatdagi fayl yuboring."
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
    "• Xizmat narxi: 120 000 so‘m\n\n"
    "Jami: 520 000 so‘m\n\n"
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


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(MENU_NEW_APPLICATION)],
        [KeyboardButton(MENU_ADMIN_CONTACT)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton("📲 Raqamni yuborish", request_contact=True)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def pdf_more_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(YES_BUTTON_TEXT), KeyboardButton(NO_BUTTON_TEXT)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


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
            await update.effective_message.reply_text(PAYMENT_UNDER_REVIEW_TEXT, reply_markup=main_menu_keyboard())
        else:
            await update.effective_message.reply_text(ALREADY_SUBMITTED_TEXT, reply_markup=main_menu_keyboard())
        return WAITING_PAYMENT

    if user_data.get("awaiting_pdf_more"):
        await update.effective_message.reply_text(ASK_ANOTHER_PDF_TEXT, reply_markup=pdf_more_keyboard())
        return WAITING_PDF_CONFIRM

    user_data["submitted_pdf"] = False
    user_data["awaiting_payment"] = False
    user_data["payment_submitted"] = False
    user_data["awaiting_pdf_more"] = False
    user_data["uploaded_pdfs"] = []

    if not user_data.get("applicant_name") or not user_data.get("phone_number"):
        await update.effective_message.reply_text(WELCOME_NAME_TEXT)
        return WAITING_NAME

    await update.effective_message.reply_text(STEP_1_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PDF


async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    if not message.text:
        await message.reply_text(NAME_INVALID_TEXT)
        return WAITING_NAME

    context.user_data["applicant_name"] = message.text.strip()
    await message.reply_text(ASK_PHONE_TEXT, reply_markup=phone_request_keyboard())
    return WAITING_PHONE


async def handle_phone_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    contact = message.contact
    user = update.effective_user

    if not contact:
        await message.reply_text(PHONE_REQUEST_TEXT, reply_markup=phone_request_keyboard())
        return WAITING_PHONE

    if contact.user_id and contact.user_id != user.id:
        await message.reply_text(PHONE_OWN_CONTACT_TEXT, reply_markup=phone_request_keyboard())
        return WAITING_PHONE

    context.user_data["phone_number"] = contact.phone_number

    await message.reply_text(PROFILE_SAVED_TEXT, reply_markup=main_menu_keyboard())
    await message.reply_text(STEP_1_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PDF


async def handle_waiting_name_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(NAME_INVALID_TEXT)
    return WAITING_NAME


async def handle_waiting_phone_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(PHONE_REQUEST_TEXT, reply_markup=phone_request_keyboard())
    return WAITING_PHONE


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
        await message.reply_text(PDF_ONLY_ERROR_TEXT)
        return WAITING_PDF

    applicant = context.user_data.get("applicant_name") or user_mention_text(user)
    phone_number = context.user_data.get("phone_number", "Noma’lum")
    uploaded_pdfs = user_data.setdefault("uploaded_pdfs", [])
    uploaded_pdfs.append(document.file_id)
    pdf_index = len(uploaded_pdfs)
    caption = (
        "📥 Yangi ro‘yxatdan o‘tish arizasi\n\n"
        f"👤 Foydalanuvchi: {applicant}\n"
        f"📱 Telefon: {phone_number}\n"
        f"🆔 ID: {user.id}\n\n"
        f"📄 Hujjat #{pdf_index} biriktirildi"
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

    user_data["awaiting_pdf_more"] = True

    await message.reply_text(ASK_ANOTHER_PDF_TEXT, reply_markup=pdf_more_keyboard())
    return WAITING_PDF_CONFIRM


async def handle_text_before_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(STEP_1_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PDF


async def handle_admin_contact_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(ADMIN_CONTACT_TEXT, reply_markup=main_menu_keyboard())
    if context.user_data.get("submitted_pdf"):
        return WAITING_PAYMENT
    return WAITING_PDF


async def handle_new_application_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    user_data["submitted_pdf"] = False
    user_data["awaiting_payment"] = False
    user_data["payment_submitted"] = False
    user_data["last_registration_approved"] = False
    user_data["awaiting_pdf_more"] = False
    user_data["uploaded_pdfs"] = []
    user_data["applicant_name"] = ""
    user_data["phone_number"] = ""

    await update.effective_message.reply_text(WELCOME_NAME_TEXT)
    return WAITING_NAME


async def handle_pdf_more_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(SEND_ANOTHER_PDF_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PDF


async def handle_pdf_more_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    if not user_data.get("uploaded_pdfs"):
        await update.effective_message.reply_text(STEP_1_TEXT, reply_markup=main_menu_keyboard())
        return WAITING_PDF

    user_data["submitted_pdf"] = True
    user_data["awaiting_payment"] = True
    user_data["awaiting_pdf_more"] = False

    await update.effective_message.reply_text(ALL_PDFS_RECEIVED_TEXT, reply_markup=main_menu_keyboard())
    await update.effective_message.reply_text(CONFIRMATION_TEXT, reply_markup=main_menu_keyboard())
    await update.effective_message.reply_text(PAYMENT_TEXT, reply_markup=main_menu_keyboard())

    schedule_payment_reminder(update, context)
    return WAITING_PAYMENT


async def handle_pdf_more_invalid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(ASK_ANOTHER_PDF_TEXT, reply_markup=pdf_more_keyboard())
    return WAITING_PDF_CONFIRM


async def handle_send_pdf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    if user_data.get("submitted_pdf"):
        if user_data.get("payment_submitted"):
            await update.effective_message.reply_text(PAYMENT_UNDER_REVIEW_TEXT, reply_markup=main_menu_keyboard())
        else:
            await update.effective_message.reply_text(ALREADY_SUBMITTED_TEXT, reply_markup=main_menu_keyboard())
        return WAITING_PAYMENT

    await update.effective_message.reply_text(STEP_1_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PDF


async def handle_send_payment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    if not user_data.get("submitted_pdf"):
        await update.effective_message.reply_text(START_TEXT_INSTEAD_OF_FILE, reply_markup=main_menu_keyboard())
        return WAITING_PDF

    if user_data.get("payment_submitted"):
        await update.effective_message.reply_text(PAYMENT_UNDER_REVIEW_TEXT, reply_markup=main_menu_keyboard())
        return WAITING_PAYMENT

    await update.effective_message.reply_text(PAYMENT_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PAYMENT


async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    user = update.effective_user
    user_data = context.user_data

    if not user_data.get("submitted_pdf"):
        await message.reply_text(START_TEXT_INSTEAD_OF_FILE)
        return WAITING_PDF

    applicant = context.user_data.get("applicant_name") or user_mention_text(user)
    phone_number = context.user_data.get("phone_number", "Noma’lum")
    caption = (
        "💳 To‘lov skrinshoti\n\n"
        f"👤 Foydalanuvchi: {applicant}\n"
        f"📱 Telefon: {phone_number}\n"
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

    await message.reply_text(PAYMENT_RECEIVED_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PAYMENT


async def handle_waiting_payment_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(PAYMENT_DELAY_TEXT, reply_markup=main_menu_keyboard())
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
            WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_waiting_name_other),
            ],
            WAITING_PHONE: [
                MessageHandler(filters.CONTACT, handle_phone_contact),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_waiting_phone_other),
            ],
            WAITING_PDF: [
                MessageHandler(filters.Regex(r"^📌 Yangi ariza$"), handle_new_application_menu),
                MessageHandler(filters.Regex(r"^📞 Admin bilan bog‘lanish$"), handle_admin_contact_menu),
                MessageHandler(filters.Document.ALL, handle_pdf),
                MessageHandler((filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO | filters.VIDEO) & ~filters.COMMAND, handle_text_before_pdf),
            ],
            WAITING_PDF_CONFIRM: [
                MessageHandler(filters.Regex(r"^📌 Yangi ariza$"), handle_new_application_menu),
                MessageHandler(filters.Regex(r"^📞 Admin bilan bog‘lanish$"), handle_admin_contact_menu),
                MessageHandler(filters.Regex(r"^✅ Ha$"), handle_pdf_more_yes),
                MessageHandler(filters.Regex(r"^❌ Yo‘q$"), handle_pdf_more_no),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_pdf_more_invalid),
            ],
            WAITING_PAYMENT: [
                MessageHandler(filters.Regex(r"^📌 Yangi ariza$"), handle_new_application_menu),
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
