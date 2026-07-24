# India Business Wallet Telegram Bot

Professional multi-file Telegram bot with:

- Apply Now flow
- Wallet service selection
- Editable service prices
- Manual QR payment
- Receipt screenshot upload
- UTR submission and duplicate-UTR blocking
- Automatic application number
- Admin approval/rejection/status management
- WhatsApp and channel links editable from admin panel
- QR, UPI ID and payment name editable from admin panel
- Persistent SQLite database

## 1. Create Telegram bot

Open `@BotFather`, create a bot and copy the token.

## 2. Find your Telegram numeric ID

Open a trusted ID bot such as `@userinfobot` and copy your numeric ID.

## 3. Railway Variables

Add these variables in Railway:

```env
BOT_TOKEN=your_bot_token
ADMIN_IDS=your_numeric_telegram_id
DATABASE_PATH=data/india_business_wallet.db
```

For multiple admins:

```env
ADMIN_IDS=123456789,987654321
```

## 4. Railway deployment

1. Upload all project files to a GitHub repository.
2. Connect repository to Railway.
3. Add Variables.
4. Railway will run the Procfile worker automatically.
5. Open your Telegram bot and send `/start`.
6. Send `/admin` from the admin Telegram account.

## 5. First admin setup

Open `/admin` and set:

- Payment QR
- UPI ID
- Payment Name
- WhatsApp Link
- Official Channel Link
- Prices, if required

## Important Railway database note

SQLite data can be lost when Railway redeploys unless persistent storage is attached.

Recommended:
- Add a Railway Volume and mount it at `/data`
- Then set:

```env
DATABASE_PATH=/data/india_business_wallet.db
```

Without a volume, the bot still works, but data persistence across redeploys is not guaranteed.

## Commands

- `/start` — User dashboard
- `/admin` — Admin panel
- `/cancel` — Cancel active application flow

## Default prices

- Google Pay Business: ₹1500
- All other wallets: ₹1000
