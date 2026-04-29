# TOPIK Register Bot

Telegram bot for TOPIK registration workflow:
- PDF hujjat qabul qilish
- Admin guruhga avtomatik yuborish
- **💳 API orqali to'lov qilish (Click/Payme)**
- **✅ Avtomatik to'lov tekshirish**
- To'lov skrinshotini ixtiyoriy sifatida qabul qilish
- Kechikkan to'lov uchun eslatma

## Features

✅ **Payment API Integration**
- Click payment system support
- Payme payment system support
- Automatic payment verification via API
- Optional screenshot support (after API verification)

✅ **Simple Uzbek UI**
- All messages in Uzbek
- Clear and intuitive workflow
- Main menu with payment button

✅ **Admin Dashboard**
- Real-time notifications
- Approve/reject buttons for documents
- Payment status tracking
- Screenshot management (optional)

## 1) Setup

1. Python 3.10+ o'rnating.
2. Virtual environment yarating va yoqing.
3. Paketlarni o'rnating:

```bash
pip install -r requirements.txt
```

4. `.env` yarating va qiymatlarni to'ldiring:

```env
# Bot Configuration
BOT_TOKEN=your_token_here
ADMIN_GROUP_ID=-100xxxxx
ADMIN_PHONE=+998 XX XXX XX XX
ADMIN_TELEGRAM=@admin_username

# Payment Configuration
PAYMENT_AMOUNT=500000
PAYMENT_CURRENCY=UZS
PAYMENT_DESCRIPTION=TOPIK registration and exam fee

# Click Payment API
CLICK_MERCHANT_ID=your_click_merchant_id
CLICK_API_KEY=your_click_api_key

# Payme Payment API
PAYME_MERCHANT_ID=your_payme_merchant_id
PAYME_API_KEY=your_payme_api_key

# Admin Info
ADMIN_USER_ID=5614681818952651
ADMIN_NAME=Mamataliyev Begmurod
```

## 2) Get Payment API Credentials

### Click Payment
- Website: https://click.uz
- Register as merchant
- Get MERCHANT_ID and API_KEY
- Add to `.env`

### Payme Payment
- Website: https://merchant.payme.uz
- Register as merchant
- Get MERCHANT_ID and API_KEY
- Add to `.env`

See [PAYMENT_INTEGRATION.md](PAYMENT_INTEGRATION.md) for detailed setup guide.

## 3) Run

```bash
python bot.py
```

## 4) Muhim eslatmalar

- `ADMIN_GROUP_ID` bot qo'shilgan guruh/supergroup ID bo'lishi kerak.
- Bot admin guruhga fayl yuborishi uchun guruhda yozish ruxsati bo'lishi kerak.
- User holati `bot_state.pkl` faylida saqlanadi (restartdan keyin ham saqlanadi).
- Payment API credentials `.env` faylida xavfsiz saqlanadi.

## 5) Troubleshooting

- Agar ishga tushishda `Chat not found` chiqsa, `ADMIN_GROUP_ID` noto'g'ri yoki bot guruhga qo'shilmagan bo'ladi.
- Botni admin guruhga qo'shing, guruh ichida `/chatid` yuboring va chiqqan ID ni `.env` dagi `ADMIN_GROUP_ID` ga yozing.
- Payment API errors uchun: CLICK_MERCHANT_ID, CLICK_API_KEY, PAYME_MERCHANT_ID, PAYME_API_KEY ni tekshiring.

## Documentation

- [PAYMENT_INTEGRATION.md](PAYMENT_INTEGRATION.md) - Payment API integration guide
- [Full user flow documentation](PAYMENT_INTEGRATION.md#payment-flow)
