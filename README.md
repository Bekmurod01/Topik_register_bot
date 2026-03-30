# TOPIK Register Bot

Telegram bot for TOPIK registration workflow:
- PDF hujjat qabul qilish
- Admin guruhga avtomatik yuborish
- To'lov yo'riqnomasi va admin contact tugmasi
- To'lov skrinshotini qabul qilish va admin guruhga yuborish
- Kechikkan to'lov uchun eslatma

## 1) Setup

1. Python 3.10+ o'rnating.
2. Virtual environment yarating va yoqing.
3. Paketlarni o'rnating:

```bash
pip install -r requirements.txt
```

4. `.env.example` faylidan nusxa olib `.env` yarating va qiymatlarni to'ldiring:

```env
BOT_TOKEN=...
ADMIN_GROUP_ID=-100...
ADMIN_THREAD_ID=0
ADMIN_PHONE=+998 XX XXX XX XX
ADMIN_TELEGRAM=@admin_username
PAYMENT_REMINDER_MINUTES=120
```

## 2) Run

```bash
python bot.py
```

## 3) Muhim eslatmalar

- `ADMIN_GROUP_ID` bot qo'shilgan guruh/supergroup ID bo'lishi kerak.
- `ADMIN_THREAD_ID` (ixtiyoriy) forum/supergroup topic ichiga yuborish uchun kerak bo'ladi. Topic ishlatmasangiz `0` qoldiring.
- Bot admin guruhga fayl yuborishi uchun guruhda yozish ruxsati bo'lishi kerak.
- User holati `bot_state.pkl` faylida saqlanadi (restartdan keyin ham saqlanadi).

## 4) Troubleshooting

- Agar ishga tushishda `Chat not found` chiqsa, `ADMIN_GROUP_ID` noto'g'ri yoki bot guruhga qo'shilmagan bo'ladi.
- Botni admin guruhga qo'shing, guruh ichida `/chatid` yuboring va chiqqan ID ni `.env` dagi `ADMIN_GROUP_ID` ga yozing.
