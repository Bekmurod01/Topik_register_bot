import logging
import os
import asyncio
import uuid
import hashlib
import hmac
from typing import Any
from datetime import datetime

import requests
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

# Bot & Admin Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))
ADMIN_THREAD_ID = int(os.getenv("ADMIN_THREAD_ID", "0"))
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "+998 XX XXX XX XX")
ADMIN_TELEGRAM = os.getenv("ADMIN_TELEGRAM", "@admin_username")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", "")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin")
PAYMENT_REMINDER_MINUTES = int(os.getenv("PAYMENT_REMINDER_MINUTES", "120"))

# Payment Configuration
PAYMENT_AMOUNT = int(os.getenv("PAYMENT_AMOUNT", "500000"))
PAYMENT_CURRENCY = os.getenv("PAYMENT_CURRENCY", "UZS")
PAYMENT_DESCRIPTION = os.getenv("PAYMENT_DESCRIPTION", "TOPIK registration and exam fee")

# Click Payment API
CLICK_MERCHANT_ID = os.getenv("CLICK_MERCHANT_ID", "")
CLICK_API_KEY = os.getenv("CLICK_API_KEY", "")
CLICK_API_URL = "https://api.click.uz/v2"

# Payme Payment API
PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID", "")
PAYME_API_KEY = os.getenv("PAYME_API_KEY", "")
PAYME_API_URL = "https://checkout.payme.uz/api"

# Conversation States
WAITING_NAME, WAITING_LOCATION, WAITING_PHONE, WAITING_EXAM_TYPE = 0, 1, 2, 3
WAITING_PDF, WAITING_PDF_CONFIRM = 4, 5
WAITING_PAYMENT_METHOD, WAITING_PAYMENT_VERIFICATION = 6, 7
WAITING_OPTIONAL_SCREENSHOT = 8

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


# ============================================================================
# TEXT MESSAGES - UZBEK
# ============================================================================

STEP_1_TEXT = "📄 Hujjatlaringizni PDF formatda yuboring\n\nBir nechta fayl yuborishingiz mumkin"

WELCOME_TEXT = (
    "🇰🇷 TOPIK ro‘yxatdan o‘tish botiga xush kelibsiz!\n\n"
    "Ro‘yxatdan o‘tishni boshlaymiz 👇"
)
ASK_NAME_TEXT = "👤 Ismingizni kiriting:"

ASK_PHONE_TEXT = "📱 Iltimos, telefon raqamingizni yuboring"
ASK_LOCATION_TEXT = (
    "📍 Qayerdansiz?\n\n"
    "Shahar yoki viloyatingizni yozing\n"
    "(masalan: Toshkent shahri, Samarqand viloyati)"
)
PROFILE_SAVED_TEXT = (
    "✅ Ma'lumotlaringiz qabul qilindi!\n\n"
    "Endi ro'yxatdan o'tishni davom ettirishingiz mumkin."
)

NAME_INVALID_TEXT = "✍️ Iltimos, ismingizni matn ko'rinishida kiriting."
LOCATION_INVALID_TEXT = "📍 Iltimos, manzilingizni matn ko'rinishida kiriting."
PHONE_REQUEST_TEXT = "📲 Telefon raqamingizni tugma orqali yuboring."
PHONE_OWN_CONTACT_TEXT = "❗ Iltimos, faqat o'zingizning telefon raqamingizni yuboring."

ASK_EXAM_TYPE_TEXT = "📝 Imtihon turini tanlang:"
EXAM_TYPE_PAPER_TEXT = "📝 Qog‘oz shaklida (Paper-based)"
EXAM_TYPE_COMPUTER_TEXT = "💻 Kompyuterda (Computer-based)"

MENU_NEW_APPLICATION = "📌 Yangi ariza"
MENU_ADMIN_CONTACT = "📞 Admin bilan bog'lanish"
MENU_PAY = "💳 To'lov qilish"

NOT_PDF_TEXT = "❌ Iltimos, hujjatni faqat PDF formatda yuboring."
START_TEXT_INSTEAD_OF_FILE = "📄 Iltimos, ro'yxatdan o'tish uchun hujjatlaringizni PDF formatda yuboring."
ASK_ANOTHER_PDF_TEXT = "📎 Yana hujjat qo‘shmoqchimisiz?"
SEND_ANOTHER_PDF_TEXT = "📄 Keyingi PDF hujjatni yuboring."
ALL_PDFS_RECEIVED_TEXT = "✅ Barcha hujjatlar qabul qilindi."
YES_BUTTON_TEXT = "➕ Ha, yana yuboraman"
NO_BUTTON_TEXT = "✅ Yo‘q, davom etish"
PDF_ONLY_ERROR_TEXT = "❌ Iltimos, faqat PDF formatdagi fayl yuboring."

ALREADY_SUBMITTED_TEXT = (
    "ℹ️ Siz allaqachon hujjat yuborgansiz.\n\n"
    "Keyingi bosqich — to'lovni amalga oshirish."
)

CONFIRMATION_TEXT = (
    "✅ Hujjatlaringiz muvaffaqiyatli qabul qilindi!\n\n"
    "Operatorlarimiz hujjatlaringizni ko'rib chiqmoqda.\n\n"
    "⏳ Keyingi bosqich: to'lovni amalga oshirish"
)

PAYMENT_METHOD_TEXT = (
    "💳 Qaysi to'lov tizimini ishlatmoqchisiz?\n\n"
    "Quyidagi variantlardan birini tanlang:"
)

PAYMENT_SUCCESS_TEXT = (
    "✅ To'lovingiz muvaffaqiyatli qabul qilindi!\n\n"
    "Ro'yxatdan o'tish jarayoni davom etmoqda."
)

PAYMENT_FAILED_TEXT = (
    "❌ To'lov qabul qilinmadi.\n\n"
    "Iltimos, qayta urinib ko'ring yoki admin bilan bog'laning:\n\n"
    f"📱 Telefon: {ADMIN_PHONE}\n"
    f"📩 Telegram: {ADMIN_TELEGRAM}"
)

SCREENSHOT_REQUEST_TEXT = (
    "📎 To'lov skrinshotini ixtiyoriy sifatida yuboring (qo'shimcha tasdiqlash uchun)."
)

SCREENSHOT_RECEIVED_TEXT = (
    "✅ Skrinshotingiz qabul qilindi!\n\n"
    "Ro'yxatdan o'tish jarayoni davom etmoqda."
)

PAYMENT_UNDER_REVIEW_TEXT = (
    "ℹ️ To'lovingiz tekshirilmoqda.\n\n"
    "Hozir admin tasdiqlashini kuting."
)

PAYMENT_DELAY_TEXT = "⏰ Eslatma: ro'yxatdan o'tishni yakunlash uchun to'lovni amalga oshirishingiz kerak."

ADMIN_FORWARD_ERROR_TEXT = (
    "⚠️ Hujjat yuborishda texnik muammo yuz berdi. "
    "Iltimos, birozdan so'ng qayta urinib ko'ring yoki admin bilan bog'laning."
)

PAYMENT_FORWARD_ERROR_TEXT = (
    "⚠️ To'lov skrinshotini yuborishda texnik muammo yuz berdi. "
    "Iltimos, birozdan so'ng qayta yuboring yoki admin bilan bog'laning."
)

USER_PDF_APPROVED_TEXT = "✅ Hujjatingiz admin tomonidan tasdiqlandi."
USER_PAYMENT_APPROVED_TEXT = (
    "🎉 To‘lovingiz tasdiqlandi!\n\n"
    "Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz."
)
USER_PDF_REJECTED_TEXT = (
    "❌ Hujjatingiz admin tomonidan rad etildi. "
    "Iltimos, hujjatlaringizni to'g'rilab qayta yuboring."
)
USER_PAYMENT_REJECTED_TEXT = "❌ To‘lov tasdiqlanmadi\n\nIltimos, admin bilan bog‘laning"

FINAL_APPLICATION_RECEIVED_TEXT = (
    "✅ To‘lov skrinshoti qabul qilindi!\n\n"
    "To‘lovingiz tekshirilmoqda. Tasdiqlangandan so‘ng sizga xabar beriladi.\n\n"
    "🙏 Sabringiz uchun rahmat!"
)

ADMIN_CONTACT_TEXT = (
    "👨‍💼 Admin bilan bog'lanish\n\n"
    "Savollar bo'lsa, admin bilan bog'laning:\n"
    f"📱 Telefon: {ADMIN_PHONE}\n"
    f"📩 Telegram: {ADMIN_TELEGRAM}\n"
    "⏰ Ish vaqti: 09:00 – 18:00"
)

PAPER_PAYMENT_INFO_TEXT = (
    "💳 To‘lov ma’lumotlari\n\n"
    "Karta raqami:\n"
    "5614 6818 1895 2651\n\n"
    "Qabul qiluvchi:\n"
    "Mamataliyev Bekmurod\n\n"
    "💰 To‘lov miqdori:\n"
    "• Koreys tili imtihoni (qog‘oz shaklida): 250 000 so‘m\n"
    "• Xizmat narxi: 120 000 so‘m\n\n"
    "Jami: 370 000 so‘m\n\n"
    "📌 To‘lovdan so‘ng skrinshot yuboring"
)

COMPUTER_PAYMENT_INFO_TEXT = (
    "💳 To‘lov ma’lumotlari\n\n"
    "Karta raqami:\n"
    "5614 6818 1895 2651\n\n"
    "Qabul qiluvchi:\n"
    "Mamataliyev Bekmurod\n\n"
    "💰 To‘lov miqdori:\n"
    "• Koreys tili imtihoni (kompyuterda): 400 000 so‘m\n"
    "• Xizmat narxi: 120 000 so‘m\n\n"
    "Jami: 520 000 so‘m\n\n"
    "📌 To‘lovdan so‘ng skrinshot yuboring"
)

ADMIN_MENU_APPLICATIONS = "📋 Arizalar"
ADMIN_MENU_STATS = "📊 Statistika"
ADMIN_MENU_BACK = "🔙 Orqaga"
ADMIN_DENIED_TEXT = "⛔ Sizda ruxsat yo‘q"


# ============================================================================
# KEYBOARDS
# ============================================================================

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(MENU_NEW_APPLICATION)],
        [KeyboardButton(MENU_ADMIN_CONTACT)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton("📲 Raqamni yuborish", request_contact=True)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def exam_type_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(EXAM_TYPE_PAPER_TEXT)],
        [KeyboardButton(EXAM_TYPE_COMPUTER_TEXT)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def pdf_more_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(YES_BUTTON_TEXT), KeyboardButton(NO_BUTTON_TEXT)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def payment_method_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[
        InlineKeyboardButton("💳 Click", callback_data="payment_click"),
        InlineKeyboardButton("💰 Payme", callback_data="payment_payme"),
    ]]
    return InlineKeyboardMarkup(keyboard)


def screenshot_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(YES_BUTTON_TEXT), KeyboardButton(NO_BUTTON_TEXT)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(ADMIN_MENU_APPLICATIONS)],
        [KeyboardButton(ADMIN_MENU_STATS)],
        [KeyboardButton(ADMIN_MENU_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def approval_button(user_id: int, stage: str, application_id: str = "") -> InlineKeyboardMarkup:
    approve_data = f"approve:{stage}:{user_id}:{application_id}" if application_id else f"approve:{stage}:{user_id}"
    reject_data = f"reject:{stage}:{user_id}:{application_id}" if application_id else f"reject:{stage}:{user_id}"
    keyboard = [[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=approve_data),
        InlineKeyboardButton("❌ Bekor qilish", callback_data=reject_data),
    ]]
    return InlineKeyboardMarkup(keyboard)


def selected_exam_type_label(user_data: dict[str, Any]) -> str:
    exam_type = user_data.get("exam_type")
    if exam_type == "paper":
        return "Paper-based (qog‘oz shaklida)"
    if exam_type == "computer":
        return "Computer-based (kompyuterda)"
    return "Tanlanmagan"


def selected_exam_payment_text(user_data: dict[str, Any]) -> str:
    if user_data.get("exam_type") == "paper":
        return PAPER_PAYMENT_INFO_TEXT
    return COMPUTER_PAYMENT_INFO_TEXT


def is_admin_user(user_id: int) -> bool:
    if not ADMIN_USER_ID:
        return False
    try:
        return user_id == int(ADMIN_USER_ID)
    except ValueError:
        return False


def get_applications_store(context: ContextTypes.DEFAULT_TYPE) -> list[dict[str, Any]]:
    apps = context.application.bot_data.get("applications")
    if not isinstance(apps, list):
        apps = []
        context.application.bot_data["applications"] = apps
    return apps


def update_application_status(context: ContextTypes.DEFAULT_TYPE, application_id: str, new_status: str) -> None:
    for app in get_applications_store(context):
        if app.get("id") == application_id:
            app["status"] = new_status
            return


# ============================================================================
# PAYMENT INTEGRATION - CLICK & PAYME
# ============================================================================

def generate_payment_id(user_id: int) -> str:
    """Generate unique payment ID for transaction tracking."""
    return f"topik-{user_id}-{uuid.uuid4().hex[:8]}"


async def create_click_payment(user_id: int, amount: int) -> dict:
    """Create Click payment and get payment URL."""
    try:
        payment_id = generate_payment_id(user_id)
        
        payload = {
            "merchant_id": CLICK_MERCHANT_ID,
            "service_id": CLICK_MERCHANT_ID,
            "amount": amount,
            "return_url": "https://t.me/TOPIK_registration_bot",
            "merchant_trans_id": payment_id,
        }

        response = requests.post(
            f"{CLICK_API_URL}/merchant/invoice/create",
            json=payload,
            headers={"Authorization": f"Bearer {CLICK_API_KEY}"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            return {
                "success": True,
                "payment_id": payment_id,
                "url": data.get("url"),
                "invoice_id": data.get("invoice_id"),
                "provider": "Click",
            }
        else:
            logger.error(f"Click API error: {data.get('error')}")
            return {"success": False, "error": data.get("error", "Unknown error")}
    except Exception as e:
        logger.exception("Failed to create Click payment")
        return {"success": False, "error": str(e)}


async def create_payme_payment(user_id: int, amount: int) -> dict:
    """Create Payme payment and get payment URL."""
    try:
        payment_id = generate_payment_id(user_id)
        
        payload = {
            "id": f"{PAYME_MERCHANT_ID}-{payment_id}",
            "method": "Subscribe.Create",
            "params": {
                "account": {
                    "phone_number": str(user_id),
                },
                "amount": amount * 100,  # Payme uses tiyin (1/100)
                "currency": "UZS",
                "description": PAYMENT_DESCRIPTION,
                "return_url": "https://t.me/TOPIK_registration_bot",
            },
            "key": "1",
        }

        response = requests.post(
            f"{PAYME_API_URL}/subscribe-create",
            json=payload,
            auth=(PAYME_MERCHANT_ID, PAYME_API_KEY),
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if data.get("result"):
            return {
                "success": True,
                "payment_id": payment_id,
                "url": data["result"].get("checkout_url"),
                "receipt_id": data["result"].get("receipt_id"),
                "provider": "Payme",
            }
        else:
            error = data.get("error", {}).get("message", "Unknown error")
            logger.error(f"Payme API error: {error}")
            return {"success": False, "error": error}
    except Exception as e:
        logger.exception("Failed to create Payme payment")
        return {"success": False, "error": str(e)}


async def verify_click_payment(payment_id: str) -> dict:
    """Verify Click payment status."""
    try:
        response = requests.get(
            f"{CLICK_API_URL}/merchant/invoice/status",
            params={"merchant_trans_id": payment_id},
            headers={"Authorization": f"Bearer {CLICK_API_KEY}"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            status = data.get("status")
            if status == 1:
                return {"success": True, "paid": True, "provider": "Click"}
            elif status == 0:
                return {"success": True, "paid": False, "provider": "Click", "reason": "pending"}
            else:
                return {"success": True, "paid": False, "provider": "Click", "reason": "cancelled"}
        else:
            return {"success": False, "error": data.get("error")}
    except Exception as e:
        logger.exception("Failed to verify Click payment")
        return {"success": False, "error": str(e)}


async def verify_payme_payment(receipt_id: str) -> dict:
    """Verify Payme payment status."""
    try:
        payload = {
            "id": f"{PAYME_MERCHANT_ID}-{receipt_id}",
            "method": "GetStatement",
            "params": {
                "id": receipt_id,
            },
            "key": "1",
        }

        response = requests.post(
            f"{PAYME_API_URL}/get-statement",
            json=payload,
            auth=(PAYME_MERCHANT_ID, PAYME_API_KEY),
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if data.get("result"):
            status = data["result"].get("state")
            if status == 1:
                return {"success": True, "paid": True, "provider": "Payme"}
            elif status == 0:
                return {"success": True, "paid": False, "provider": "Payme", "reason": "pending"}
            else:
                return {"success": True, "paid": False, "provider": "Payme", "reason": "cancelled"}
        else:
            error = data.get("error", {}).get("message", "Unknown error")
            return {"success": False, "error": error}
    except Exception as e:
        logger.exception("Failed to verify Payme payment")
        return {"success": False, "error": str(e)}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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


# ============================================================================
# CONVERSATION HANDLERS
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data

    if user_data.get("last_registration_approved"):
        user_data["submitted_pdf"] = False
        user_data["awaiting_payment"] = False
        user_data["payment_verified"] = False
        user_data["last_registration_approved"] = False

    if user_data.get("submitted_pdf"):
        if user_data.get("payment_verified"):
            await update.effective_message.reply_text(
                "✅ To'lovingiz tekshirildi.\n\nRo'yxatdan o'tish davom etmoqda.",
                reply_markup=main_menu_keyboard()
            )
            return WAITING_PAYMENT_METHOD

        if user_data.get("awaiting_manual_receipt"):
            await update.effective_message.reply_text(
                selected_exam_payment_text(user_data),
                reply_markup=main_menu_keyboard(),
            )
            return WAITING_OPTIONAL_SCREENSHOT

        await update.effective_message.reply_text(ALREADY_SUBMITTED_TEXT, reply_markup=main_menu_keyboard())
        return WAITING_PAYMENT_METHOD

    if user_data.get("awaiting_manual_receipt") and user_data.get("exam_type") in {"paper", "computer"}:
        await update.effective_message.reply_text(
            selected_exam_payment_text(user_data),
            reply_markup=main_menu_keyboard(),
        )
        return WAITING_OPTIONAL_SCREENSHOT

    if user_data.get("awaiting_pdf_more"):
        await update.effective_message.reply_text(ASK_ANOTHER_PDF_TEXT, reply_markup=pdf_more_keyboard())
        return WAITING_PDF_CONFIRM

    if not user_data.get("applicant_name"):
        await update.effective_message.reply_text(WELCOME_TEXT)
        await update.effective_message.reply_text(ASK_NAME_TEXT)
        return WAITING_NAME

    if not user_data.get("user_location"):
        await update.effective_message.reply_text(ASK_LOCATION_TEXT)
        return WAITING_LOCATION

    if not user_data.get("phone_number"):
        await update.effective_message.reply_text(ASK_PHONE_TEXT, reply_markup=phone_request_keyboard())
        return WAITING_PHONE

    if user_data.get("exam_type") not in {"paper", "computer"}:
        await update.effective_message.reply_text(ASK_EXAM_TYPE_TEXT, reply_markup=exam_type_keyboard())
        return WAITING_EXAM_TYPE

    await update.effective_message.reply_text(STEP_1_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PDF


async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    if not message.text:
        await message.reply_text(NAME_INVALID_TEXT)
        return WAITING_NAME

    context.user_data["applicant_name"] = message.text.strip()
    await message.reply_text(ASK_LOCATION_TEXT)
    return WAITING_LOCATION


async def handle_location_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    if not message.text:
        await message.reply_text(LOCATION_INVALID_TEXT)
        return WAITING_LOCATION

    context.user_data["user_location"] = message.text.strip()
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
    await message.reply_text(PROFILE_SAVED_TEXT)
    await message.reply_text(ASK_EXAM_TYPE_TEXT, reply_markup=exam_type_keyboard())
    return WAITING_EXAM_TYPE


async def handle_exam_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip()
    user_data = context.user_data

    if text == EXAM_TYPE_PAPER_TEXT:
        user_data["exam_type"] = "paper"
    elif text == EXAM_TYPE_COMPUTER_TEXT:
        user_data["exam_type"] = "computer"
    else:
        await update.effective_message.reply_text(ASK_EXAM_TYPE_TEXT, reply_markup=exam_type_keyboard())
        return WAITING_EXAM_TYPE

    user_data["awaiting_manual_receipt"] = False
    user_data["submitted_pdf"] = False
    user_data["awaiting_pdf_more"] = False
    user_data["uploaded_pdfs"] = []
    user_data["awaiting_payment"] = False
    user_data["payment_verified"] = False

    await update.effective_message.reply_text(STEP_1_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PDF


async def handle_waiting_name_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(NAME_INVALID_TEXT)
    return WAITING_NAME


async def handle_waiting_location_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(LOCATION_INVALID_TEXT)
    return WAITING_LOCATION


async def handle_waiting_phone_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(PHONE_REQUEST_TEXT, reply_markup=phone_request_keyboard())
    return WAITING_PHONE


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    await update.effective_message.reply_text(f"Chat ID: {chat.id}\nType: {chat.type}")


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    user = update.effective_user
    user_data = context.user_data

    if user_data.get("submitted_pdf"):
        await message.reply_text(ALREADY_SUBMITTED_TEXT)
        return WAITING_PAYMENT_METHOD

    document = message.document
    is_pdf = bool(document and (
        (document.mime_type and document.mime_type.lower() == "application/pdf")
        or (document.file_name and document.file_name.lower().endswith(".pdf"))
    ))

    if not is_pdf:
        await message.reply_text(PDF_ONLY_ERROR_TEXT)
        return WAITING_PDF

    uploaded_pdfs = user_data.setdefault("uploaded_pdfs", [])
    uploaded_pdfs.append(document.file_id)

    user_data["awaiting_pdf_more"] = True
    await message.reply_text(ASK_ANOTHER_PDF_TEXT, reply_markup=pdf_more_keyboard())
    return WAITING_PDF_CONFIRM


async def handle_text_before_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(STEP_1_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PDF


async def handle_admin_contact_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(ADMIN_CONTACT_TEXT, reply_markup=main_menu_keyboard())
    if context.user_data.get("awaiting_manual_receipt"):
        return WAITING_OPTIONAL_SCREENSHOT
    if context.user_data.get("submitted_pdf"):
        return WAITING_PAYMENT_METHOD
    return WAITING_PDF


async def handle_new_application_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    user_data["submitted_pdf"] = False
    user_data["awaiting_payment"] = False
    user_data["payment_verified"] = False
    user_data["awaiting_pdf_more"] = False
    user_data["uploaded_pdfs"] = []
    user_data["applicant_name"] = ""
    user_data["user_location"] = ""
    user_data["phone_number"] = ""
    user_data["exam_type"] = ""
    user_data["awaiting_manual_receipt"] = False

    await update.effective_message.reply_text(WELCOME_TEXT)
    await update.effective_message.reply_text(ASK_NAME_TEXT)
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
    user_data["awaiting_manual_receipt"] = True

    await update.effective_message.reply_text(ALL_PDFS_RECEIVED_TEXT, reply_markup=main_menu_keyboard())
    await update.effective_message.reply_text(selected_exam_payment_text(user_data), reply_markup=main_menu_keyboard())

    schedule_payment_reminder(update, context)
    return WAITING_OPTIONAL_SCREENSHOT


async def handle_pdf_more_invalid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(ASK_ANOTHER_PDF_TEXT, reply_markup=pdf_more_keyboard())
    return WAITING_PDF_CONFIRM


async def handle_payment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data

    if not user_data.get("submitted_pdf"):
        await update.effective_message.reply_text(STEP_1_TEXT, reply_markup=main_menu_keyboard())
        return WAITING_PDF

    if user_data.get("exam_type") not in {"paper", "computer"}:
        await update.effective_message.reply_text(ASK_EXAM_TYPE_TEXT, reply_markup=exam_type_keyboard())
        return WAITING_EXAM_TYPE

    if user_data.get("payment_verified"):
        await update.effective_message.reply_text(
            "✅ To'lovingiz allaqachon tekshirildi.\n\nRo'yxatdan o'tish davom etmoqda.",
            reply_markup=main_menu_keyboard()
        )
        return WAITING_PAYMENT_METHOD

    user_data["awaiting_manual_receipt"] = True
    user_data["awaiting_payment"] = True
    await update.effective_message.reply_text(selected_exam_payment_text(user_data), reply_markup=main_menu_keyboard())
    return WAITING_OPTIONAL_SCREENSHOT


async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment method selection (Click or Payme)."""
    query = update.callback_query
    user = update.effective_user
    user_data = context.user_data

    await query.answer()

    if query.data == "payment_click":
        provider = "Click"
        result = await create_click_payment(user.id, PAYMENT_AMOUNT)
    elif query.data == "payment_payme":
        provider = "Payme"
        result = await create_payme_payment(user.id, PAYMENT_AMOUNT)
    else:
        await query.edit_message_text(PAYMENT_METHOD_TEXT, reply_markup=payment_method_keyboard())
        return WAITING_PAYMENT_METHOD

    if not result.get("success"):
        await query.edit_message_text(
            f"❌ {provider} to'lov yaratishda xatolik.\n\n"
            f"Xatolik: {result.get('error')}\n\n"
            "Qayta urinib ko'ring.",
            reply_markup=payment_method_keyboard()
        )
        return WAITING_PAYMENT_METHOD

    user_data["payment_method"] = provider
    user_data["payment_id"] = result.get("payment_id")
    user_data["receipt_id"] = result.get("receipt_id")
    user_data["payment_url"] = result.get("url")

    payment_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 To'lov sahifasini ochish", url=result.get("url"))
    ]])

    await query.edit_message_text(
        f"💳 {provider} orqali to'lov\n\n"
        f"💰 Miqdor: {PAYMENT_AMOUNT:,} {PAYMENT_CURRENCY}\n"
        f"📝 Tavsif: {PAYMENT_DESCRIPTION}\n\n"
        f"⏳ To'lov tugmasi orqali to'lovni amalga oshiring.",
        reply_markup=payment_keyboard
    )

    user_data["awaiting_payment_verification"] = True
    user_data["payment_started_at"] = datetime.now().isoformat()

    if context.job_queue:
        job_name = f"verify-payment-{user.id}"
        existing_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in existing_jobs:
            job.schedule_removal()

        context.job_queue.run_once(
            verify_payment_status,
            when=5,
            name=job_name,
            chat_id=user.id,
            data={"user_id": user.id},
        )

    return WAITING_PAYMENT_VERIFICATION


async def verify_payment_status(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verify payment status with API and notify user."""
    user_id = context.job.data["user_id"]
    user_data = context.application.user_data.get(user_id, {})

    if not user_data.get("awaiting_payment_verification"):
        return

    provider = user_data.get("payment_method")
    payment_verified = False

    if provider == "Click":
        payment_id = user_data.get("payment_id")
        result = await verify_click_payment(payment_id)
        payment_verified = result.get("paid", False) if result.get("success") else False
    elif provider == "Payme":
        receipt_id = user_data.get("receipt_id")
        result = await verify_payme_payment(receipt_id)
        payment_verified = result.get("paid", False) if result.get("success") else False

    if payment_verified:
        user_data["payment_verified"] = True
        user_data["awaiting_payment_verification"] = False

        await context.bot.send_message(
            chat_id=user_id,
            text=PAYMENT_SUCCESS_TEXT
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=SCREENSHOT_REQUEST_TEXT,
            reply_markup=screenshot_keyboard()
        )

        applicant = user_data.get("applicant_name", "Noma'lum")
        phone_number = user_data.get("phone_number", "Noma'lum")
        exam_type = selected_exam_type_label(user_data)
        admin_msg = (
            f"✅ API orqali tasdiqlangan to'lov\n\n"
            f"👤 Foydalanuvchi: {applicant}\n"
            f"📱 Telefon: {phone_number}\n"
            f"🧾 Imtihon turi: {exam_type}\n"
            f"🆔 ID: {user_id}\n"
            f"💳 Tizim: {provider}\n"
            f"💰 Miqdor: {PAYMENT_AMOUNT:,} {PAYMENT_CURRENCY}\n\n"
            f"📌 To'lov API orqali tasdiqlandi"
        )

        target = admin_target_kwargs()
        try:
            await context.bot.send_message(
                text=admin_msg,
                **target,
            )
        except TelegramError:
            logger.exception("Failed to notify admin about API verified payment")

    else:
        if context.job_queue:
            job_name = f"verify-payment-{user_id}"
            existing_jobs = context.job_queue.get_jobs_by_name(job_name)
            if len(existing_jobs) < 5:
                context.job_queue.run_once(
                    verify_payment_status,
                    when=10,
                    name=job_name,
                    chat_id=user_id,
                    data={"user_id": user_id},
                )
            else:
                user_data["awaiting_payment_verification"] = False
                await context.bot.send_message(
                    chat_id=user_id,
                    text=PAYMENT_FAILED_TEXT
                )


async def handle_optional_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle optional screenshot after successful payment."""
    message = update.effective_message
    user = update.effective_user
    user_data = context.user_data

    manual_receipt_mode = bool(user_data.get("awaiting_manual_receipt"))

    if not user_data.get("payment_verified") and not manual_receipt_mode:
        await message.reply_text(
            "❌ To'lov avval tekshirilishi kerak.\n\n"
            "Iltimos, avval to'lov qiling.",
            reply_markup=main_menu_keyboard()
        )
        return WAITING_PAYMENT_METHOD

    if message.text and message.text == NO_BUTTON_TEXT and not manual_receipt_mode:
        await message.reply_text(
            "✅ Ro'yxatdan o'tish jarayoni davom etmoqda.\n\n"
            "Operatorlarimiz hujjatlaringizni ko'rib chiqmoqda.",
            reply_markup=main_menu_keyboard()
        )
        return WAITING_PAYMENT_METHOD

    screenshot_kind = ""
    screenshot_file_id = ""
    if message.photo:
        screenshot_kind = "photo"
        screenshot_file_id = message.photo[-1].file_id
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        screenshot_kind = "document"
        screenshot_file_id = message.document.file_id
    else:
        await message.reply_text(
            "📎 Iltimos, to'lov chekini rasm ko'rinishida yuboring.",
            reply_markup=main_menu_keyboard()
        )
        return WAITING_OPTIONAL_SCREENSHOT

    applicant = user_data.get("applicant_name") or user_mention_text(user)
    phone_number = user_data.get("phone_number", "Noma'lum")
    location = user_data.get("user_location", "Noma'lum")
    exam_type = selected_exam_type_label(user_data)

    admin_summary = (
        "📥 Yangi ro‘yxatdan o‘tish arizasi\n\n"
        f"👤 Ism: {applicant}\n"
        f"📱 Telefon: {phone_number}\n"
        f"📍 Manzil: {location}\n"
        f"📝 Imtihon turi: {exam_type}\n\n"
        "📌 Holat: ⏳ Kutilmoqda"
    )

    target = admin_target_kwargs()
    uploaded_pdfs = user_data.get("uploaded_pdfs", [])
    application_id = uuid.uuid4().hex[:8]

    try:
        summary_message = await context.bot.send_message(
            text=admin_summary,
            reply_markup=approval_button(user.id, "payment", application_id),
            **target,
        )

        get_applications_store(context).append({
            "id": application_id,
            "user_id": user.id,
            "name": applicant,
            "phone": phone_number,
            "location": location,
            "exam_type": exam_type,
            "pdfs": list(uploaded_pdfs),
            "screenshot_type": screenshot_kind,
            "screenshot_file_id": screenshot_file_id,
            "status": "⏳ Kutilmoqda",
            "summary_message_id": summary_message.message_id,
            "created_at": datetime.now().isoformat(),
        })

        for pdf_file_id in uploaded_pdfs:
            await context.bot.send_document(
                document=pdf_file_id,
                caption="📄 Hujjat",
                **target,
            )

        if screenshot_kind == "photo":
            await context.bot.send_photo(
                photo=screenshot_file_id,
                caption="💳 To‘lov skrinshoti",
                **target,
            )
        else:
            await context.bot.send_document(
                document=screenshot_file_id,
                caption="💳 To‘lov skrinshoti",
                **target,
            )
    except TelegramError:
        logger.exception("Failed to send full application package to admin group")
        await message.reply_text(PAYMENT_FORWARD_ERROR_TEXT)
        return WAITING_OPTIONAL_SCREENSHOT

    user_data["awaiting_manual_receipt"] = False
    user_data["awaiting_payment"] = False
    user_data["submitted_pdf"] = True
    user_data["payment_verified"] = False
    user_data["last_application_id"] = application_id
    await message.reply_text(FINAL_APPLICATION_RECEIVED_TEXT, reply_markup=main_menu_keyboard())
    return WAITING_PAYMENT_METHOD


async def handle_waiting_payment_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle text messages during payment wait."""
    if update.effective_message.text == MENU_NEW_APPLICATION:
        return await handle_new_application_menu(update, context)
    elif update.effective_message.text == MENU_ADMIN_CONTACT:
        return await handle_admin_contact_menu(update, context)
    elif update.effective_message.text == MENU_PAY:
        return await handle_payment_menu(update, context)
    else:
        await update.effective_message.reply_text(PAYMENT_DELAY_TEXT, reply_markup=main_menu_keyboard())
        return WAITING_PAYMENT_METHOD


async def admin_decision_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin approval/rejection buttons."""
    query = update.callback_query
    if query is None or query.data is None:
        return

    actor = query.from_user
    if actor is None:
        return

    is_allowed = is_admin_user(actor.id)

    if not is_allowed:
        await query.answer("Faqat admin bu tugmalardan foydalana oladi.", show_alert=True)
        return

    parts = query.data.split(":")
    if len(parts) not in {3, 4}:
        return

    action, stage, user_id_raw = parts[:3]
    application_id = parts[3] if len(parts) == 4 else ""
    if action not in {"approve", "reject"}:
        return

    await query.answer("Tasdiqlandi" if action == "approve" else "Bekor qilindi")

    try:
        user_id = int(user_id_raw)
    except ValueError:
        return

    target_user_data = context.application.user_data[user_id]

    if action == "approve":
        if stage == "pdf":
            target_user_data["submitted_pdf"] = True
            target_user_data["awaiting_payment"] = True
            target_user_data["payment_verified"] = False
            notification_text = USER_PDF_APPROVED_TEXT
        else:
            target_user_data["submitted_pdf"] = False
            target_user_data["awaiting_payment"] = False
            target_user_data["payment_verified"] = False
            target_user_data["uploaded_pdfs"] = []
            target_user_data["last_registration_approved"] = True
            notification_text = USER_PAYMENT_APPROVED_TEXT
            if application_id:
                update_application_status(context, application_id, "✅ Tasdiqlandi")
    else:
        if stage == "pdf":
            target_user_data["submitted_pdf"] = False
            target_user_data["awaiting_payment"] = False
            target_user_data["payment_verified"] = False
            target_user_data["last_registration_approved"] = False
            notification_text = USER_PDF_REJECTED_TEXT
        else:
            target_user_data["submitted_pdf"] = True
            target_user_data["awaiting_payment"] = True
            target_user_data["payment_verified"] = False
            target_user_data["last_registration_approved"] = False
            notification_text = USER_PAYMENT_REJECTED_TEXT
            if application_id:
                update_application_status(context, application_id, "❌ Bekor qilindi")

    if query.message is not None and application_id:
        try:
            current_text = query.message.text or ""
            if "📌 Holat:" in current_text:
                base = current_text.split("📌 Holat:", 1)[0].rstrip()
                status_value = "✅ Tasdiqlandi" if action == "approve" else "❌ Bekor qilindi"
                await query.message.edit_text(
                    f"{base}\n\n📌 Holat: {status_value}",
                    reply_markup=None,
                )
            else:
                await query.message.edit_reply_markup(reply_markup=None)
        except TelegramError:
            logger.exception("Failed to update admin summary status")

    try:
        await context.bot.send_message(chat_id=user_id, text=notification_text)
    except TelegramError:
        logger.exception("Failed to notify user about admin decision: action=%s stage=%s user_id=%s", action, stage, user_id)

    if query.message is not None and not application_id:
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except TelegramError:
            logger.exception("Failed to clear admin decision buttons in admin group")


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or not is_admin_user(user.id):
        await update.effective_message.reply_text(ADMIN_DENIED_TEXT)
        return

    await update.effective_message.reply_text("👨‍💼 Admin panel", reply_markup=admin_panel_keyboard())


async def admin_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    if not is_admin_user(user.id):
        await message.reply_text(ADMIN_DENIED_TEXT)
        return

    text = message.text or ""
    if text == ADMIN_MENU_BACK:
        await message.reply_text("Asosiy menyu", reply_markup=main_menu_keyboard())
        return

    if text == ADMIN_MENU_STATS:
        apps = get_applications_store(context)
        total = len(apps)
        pending = sum(1 for a in apps if a.get("status") == "⏳ Kutilmoqda")
        approved = sum(1 for a in apps if a.get("status") == "✅ Tasdiqlandi")
        rejected = sum(1 for a in apps if a.get("status") == "❌ Bekor qilindi")
        await message.reply_text(
            "📊 Statistika\n\n"
            f"Jami arizalar: {total}\n"
            f"⏳ Kutilmoqda: {pending}\n"
            f"✅ Tasdiqlandi: {approved}\n"
            f"❌ Bekor qilindi: {rejected}",
            reply_markup=admin_panel_keyboard(),
        )
        return

    if text == ADMIN_MENU_APPLICATIONS:
        apps = get_applications_store(context)
        if not apps:
            await message.reply_text("📭 Hozircha arizalar yo‘q.", reply_markup=admin_panel_keyboard())
            return

        target = admin_target_kwargs()
        for app in reversed(apps[-20:]):
            await message.reply_text(
                "📥 Foydalanuvchi\n\n"
                f"👤 {app.get('name', 'Noma\'lum')}\n"
                f"📱 {app.get('phone', 'Noma\'lum')}\n"
                f"📍 {app.get('location', 'Noma\'lum')}\n"
                f"📝 {app.get('exam_type', 'Noma\'lum')}\n"
                f"📌 Holat: {app.get('status', '⏳ Kutilmoqda')}",
                reply_markup=admin_panel_keyboard(),
            )

            for pdf_file_id in app.get("pdfs", []):
                await context.bot.send_document(
                    document=pdf_file_id,
                    caption="📄 Hujjat",
                    chat_id=message.chat_id,
                )

            screenshot_id = app.get("screenshot_file_id")
            if screenshot_id:
                if app.get("screenshot_type") == "photo":
                    await context.bot.send_photo(
                        photo=screenshot_id,
                        caption="💳 To‘lov skrinshoti",
                        chat_id=message.chat_id,
                    )
                else:
                    await context.bot.send_document(
                        document=screenshot_id,
                        caption="💳 To‘lov skrinshoti",
                        chat_id=message.chat_id,
                    )

        return


def schedule_payment_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Schedule payment reminder after PDF submission."""
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
    """Send payment reminder if user hasn't completed payment."""
    user_id = context.job.data["user_id"]
    user_data = context.application.user_data.get(user_id, {})

    if user_data.get("awaiting_payment") and not user_data.get("payment_verified"):
        await context.bot.send_message(chat_id=user_id, text=PAYMENT_DELAY_TEXT)


# ============================================================================
# APPLICATION BUILDER
# ============================================================================

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
            WAITING_LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location_input),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_waiting_location_other),
            ],
            WAITING_PHONE: [
                MessageHandler(filters.CONTACT, handle_phone_contact),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_waiting_phone_other),
            ],
            WAITING_EXAM_TYPE: [
                MessageHandler(filters.Regex(r"^📝 Qog‘oz shaklida \(Paper-based\)$"), handle_exam_type_selection),
                MessageHandler(filters.Regex(r"^💻 Kompyuterda \(Computer-based\)$"), handle_exam_type_selection),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_exam_type_selection),
            ],
            WAITING_PDF: [
                MessageHandler(filters.Regex(r"^📌 Yangi ariza$"), handle_new_application_menu),
                MessageHandler(filters.Regex(r"^📞 Admin bilan bog'lanish$"), handle_admin_contact_menu),
                MessageHandler(filters.Regex(r"^💳 To'lov qilish$"), handle_payment_menu),
                MessageHandler(filters.Document.ALL, handle_pdf),
                MessageHandler((filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO | filters.VIDEO) & ~filters.COMMAND, handle_text_before_pdf),
            ],
            WAITING_PDF_CONFIRM: [
                MessageHandler(filters.Regex(r"^📌 Yangi ariza$"), handle_new_application_menu),
                MessageHandler(filters.Regex(r"^📞 Admin bilan bog'lanish$"), handle_admin_contact_menu),
                MessageHandler(filters.Regex(r"^💳 To'lov qilish$"), handle_payment_menu),
                MessageHandler(filters.Regex(r"^➕ Ha, yana yuboraman$"), handle_pdf_more_yes),
                MessageHandler(filters.Regex(r"^✅ Yo‘q, davom etish$"), handle_pdf_more_no),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_pdf_more_invalid),
            ],
            WAITING_PAYMENT_METHOD: [
                MessageHandler(filters.Regex(r"^📌 Yangi ariza$"), handle_new_application_menu),
                MessageHandler(filters.Regex(r"^📞 Admin bilan bog'lanish$"), handle_admin_contact_menu),
                MessageHandler(filters.Regex(r"^💳 To'lov qilish$"), handle_payment_menu),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_waiting_payment_text),
                CallbackQueryHandler(handle_payment_method_selection, pattern="^payment_"),
            ],
            WAITING_PAYMENT_VERIFICATION: [
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_waiting_payment_text),
            ],
            WAITING_OPTIONAL_SCREENSHOT: [
                MessageHandler(filters.Regex(r"^❌ Yo'q$"), handle_optional_screenshot),
                MessageHandler(filters.PHOTO, handle_optional_screenshot),
                MessageHandler(filters.Document.IMAGE, handle_optional_screenshot),
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_optional_screenshot),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        name="topik-registration-flow",
        persistent=True,
    )

    application.add_handler(CommandHandler("admin", admin_panel), group=-1)
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^(📋 Arizalar|📊 Statistika|🔙 Orqaga)$") & ~filters.COMMAND,
            admin_menu_text,
        ),
        group=-1,
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("chatid", chat_id))
    application.add_handler(CallbackQueryHandler(admin_decision_button, pattern="^(approve|reject):"))

    return application


def main() -> None:
    app = build_app()
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
