# TOPIK Bot - Payment API Integration Guide

## Overview

The bot has been upgraded with integrated payment system support for **Click** and **Payme** payment platforms. The system uses **API-based verification as the primary payment confirmation method**, with optional screenshot support as secondary verification.

## Key Features

✅ **API-First Payment Verification**
- Main payment verification happens through Click or Payme APIs
- No dependency on manual screenshot review for payment confirmation
- Fast, secure, and automated processing

✅ **Dual Payment Gateway Support**
- Click payment system integration
- Payme payment system integration
- User can choose their preferred payment method

✅ **Optional Screenshot Support**
- Screenshots requested ONLY after successful API payment verification
- Used as supplementary documentation, not primary verification
- Optional: users can skip screenshot submission

✅ **Uzbek Language UI**
- All messages in Uzbek (o'zbek tili)
- Clear and simple user experience

## Payment Flow

```
1. User completes PDF submission
   ↓
2. Bot shows "💳 To'lov qilish" (Pay) button in main menu
   ↓
3. User clicks payment button
   ↓
4. Bot displays payment method choice:
   - Click
   - Payme
   ↓
5. User selects payment method
   ↓
6. Bot sends payment link (inline button)
   ↓
7. User completes payment in external app
   ↓
8. Bot polls API every 5-10 seconds for payment status
   ↓
9a. If PAYMENT VERIFIED ✅:
    - Send success notification
    - Ask for optional screenshot
    - Notify admin: "API orqali tasdiqlangan to'lov" (Verified via API)
    ↓
9b. If PAYMENT FAILED ❌:
    - Send failure notification
    - User must retry payment
    - Screenshot will NOT be accepted
   ↓
10. User optionally sends screenshot (or skips with "❌ Yo'q")
    ↓
11. If screenshot sent:
    - Screenshot forwarded to admin group
    - Marked as "API orqali tasdiqlangan" (Verified via API)
    ↓
12. Registration process continues
```

## Configuration

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The following packages are required:
- `python-telegram-bot[job-queue]==21.6`
- `python-dotenv==1.0.1`
- `requests==2.31.0`

### 2. Configure .env File

Update your `.env` file with payment API credentials:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token
ADMIN_GROUP_ID=your_admin_group_id
ADMIN_PHONE=+998 XX XXX XX XX
ADMIN_TELEGRAM=@your_username

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

### 3. Getting Payment API Credentials

#### Click Payment System
1. Visit: https://click.uz
2. Register as merchant
3. Get your `MERCHANT_ID` and `API_KEY`
4. Add credentials to `.env`

#### Payme Payment System
1. Visit: https://merchant.payme.uz
2. Register as merchant
3. Get your `MERCHANT_ID` and `API_KEY`
4. Add credentials to `.env`

## API Integration Details

### Click Payment API

**Create Payment:**
```
POST https://api.click.uz/v2/merchant/invoice/create
Authorization: Bearer {CLICK_API_KEY}
```

**Verify Payment:**
```
GET https://api.click.uz/v2/merchant/invoice/status?merchant_trans_id={payment_id}
Authorization: Bearer {CLICK_API_KEY}
```

Status Codes:
- `0` = Pending
- `1` = Confirmed ✅
- `2` = Cancelled ❌

### Payme Payment API

**Create Payment:**
```
POST https://checkout.payme.uz/api/subscribe-create
Auth: {MERCHANT_ID}:{API_KEY}
Method: Subscribe.Create
```

**Verify Payment:**
```
POST https://checkout.payme.uz/api/get-statement
Auth: {MERCHANT_ID}:{API_KEY}
Method: GetStatement
```

Status Codes:
- `0` = Pending
- `1` = Confirmed ✅
- `2` = Cancelled ❌

## User States

The bot manages 7 conversation states:

| State ID | State Name | Purpose |
|----------|-----------|---------|
| 0 | WAITING_NAME | Collect user's name |
| 1 | WAITING_PHONE | Collect phone number |
| 2 | WAITING_PDF | Receive registration documents |
| 3 | WAITING_PDF_CONFIRM | Ask if more documents needed |
| 4 | WAITING_PAYMENT_METHOD | Choose Click or Payme |
| 5 | WAITING_PAYMENT_VERIFICATION | Wait for API confirmation |
| 6 | WAITING_OPTIONAL_SCREENSHOT | Optional screenshot support |

## Payment Status Flow

```
User Data Flags:
- submitted_pdf: Document submission status
- awaiting_payment: Waiting for payment to start
- payment_verified: ✅ API confirmed payment
- payment_method: "Click" or "Payme"
- payment_id: Unique transaction identifier
- receipt_id: Payment system receipt ID
- awaiting_payment_verification: Polling for API status
- payment_started_at: ISO timestamp of payment initiation
```

## Admin Notifications

### PDF Submission
```
📥 Yangi ro'yxatdan o'tish arizasi

👤 Foydalanuvchi: [Name]
📱 Telefon: [Phone]
🆔 ID: [User ID]

📄 Hujjat #1 biriktirildi

[Approve/Reject Buttons]
```

### API-Verified Payment
```
✅ API orqali tasdiqlangan to'lov

👤 Foydalanuvchi: [Name]
📱 Telefon: [Phone]
🆔 ID: [User ID]
💳 Tizim: Click/Payme
💰 Miqdor: 500,000 UZS

📌 To'lov API orqali tasdiqlandi
```

### Optional Screenshot (after API payment verified)
```
📎 Qo'shimcha to'lov skrinsyoti (API tasdiqlangan)

👤 Foydalanuvchi: [Name]
📱 Telefon: [Phone]
🆔 ID: [User ID]

📌 API orqali tasdiqlangan to'lovning qo'shimcha skrinsyoti
```

## Menu Buttons

The main menu displays three buttons:

| Button | Action |
|--------|--------|
| 📌 Yangi ariza | Start new registration |
| 💳 To'lov qilish | Initiate payment |
| 📞 Admin bilan bog'lanish | Contact admin |

## Payment Verification Algorithm

1. **User initiates payment** → Bot creates payment link via API
2. **User completes payment** → User redirected back to bot
3. **Bot starts polling** → Checks payment status every 5 seconds
4. **Status check loop:**
   - First check: 5 seconds
   - Subsequent checks: 10 seconds
   - Max attempts: 5 checks (≈50 seconds total)
5. **If payment confirmed:**
   - Set `payment_verified = True`
   - Ask for optional screenshot
   - Notify admin
6. **If payment not confirmed after max attempts:**
   - Set `payment_verified = False`
   - Send failure message
   - User must try again

## Error Handling

### API Connection Errors
- Automatically retries 5 times with increasing wait times
- Friendly error message if all retries fail
- User can manually initiate payment again

### Invalid Payment Credentials
- Bot will fail to start with configuration error
- Check `.env` file for correct API keys
- Verify CLICK_MERCHANT_ID and PAYME_MERCHANT_ID

### Admin Group Not Found
- Bot will not start
- Run `/chatid` command in admin group
- Update ADMIN_GROUP_ID in `.env`

## Running the Bot

```bash
# Activate virtual environment (if using one)
# For Windows:
.\.venv\Scripts\Activate.ps1

# Start the bot
python bot.py
```

## Troubleshooting

### Bot won't start
- Check BOT_TOKEN is valid
- Check ADMIN_GROUP_ID is correct
- Run `/chatid` in admin group to verify

### Payment API errors
- Verify CLICK_MERCHANT_ID and CLICK_API_KEY
- Verify PAYME_MERCHANT_ID and PAYME_API_KEY
- Check API credentials are active on merchant portal

### Payment not verifying
- Allow longer wait time (up to 50 seconds)
- Check payment status manually in payment system portal
- Verify payment was actually completed in payment app

### User gets screenshot request but didn't pay
- This should not happen - screenshot is only shown after API verification
- If it happens, check payment API configuration

## Security Notes

- API keys stored in `.env` (not in code)
- Payment verification done server-to-server (secure)
- Payment links include unique transaction IDs
- User data persisted in `bot_state.pkl` file

## Future Enhancements

Possible improvements:
- Receipt number storage for audit trail
- Payment timeout notifications
- Retry payment mechanism
- Payment history dashboard
- Multiple currency support
- Webhook-based payment notifications (instead of polling)

---

**Version:** 2.0 (Payment API Integration)  
**Last Updated:** March 31, 2026  
**Language:** Uzbek (o'zbek tili)  
**Primary Verification:** API-based (Click/Payme)  
**Secondary Verification:** Optional screenshot support
