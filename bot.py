import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import Config
from database import Database
from handlers import admin, user

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    config = Config.from_env()
    db = Database(config.database_path)

    app = Application.builder().token(config.bot_token).build()
    app.bot_data["db"] = db
    app.bot_data["admin_ids"] = config.admin_ids

    user_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(user.callback_router, pattern=r"^(understood:|user:cancel)")
        ],
        states={
            user.WAITING_RECEIPT: [
                MessageHandler(filters.PHOTO, user.receive_receipt),
                CallbackQueryHandler(user.callback_router, pattern=r"^user:cancel$"),
                MessageHandler(~filters.PHOTO & ~filters.COMMAND, user.receive_receipt),
            ],
            user.WAITING_UTR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, user.receive_utr),
                CallbackQueryHandler(user.callback_router, pattern=r"^user:cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", user.cancel_text),
            CommandHandler("start", user.start),
        ],
        allow_reentry=True,
    )

    admin_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                admin.admin_callback,
                pattern=r"^admin:(set:|price:|reject:)",
            )
        ],
        states={
            admin.WAITING_SETTING: [
                MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), admin.receive_setting)
            ],
            admin.WAITING_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin.receive_price)
            ],
            admin.WAITING_REJECT_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin.receive_reject_reason)
            ],
        },
        fallbacks=[CommandHandler("admin", admin.admin_command)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", user.start))
    app.add_handler(CommandHandler("admin", admin.admin_command))
    app.add_handler(user_conversation)
    app.add_handler(admin_conversation)

    # Open the main dashboard when a user sends any supported keyword.
    open_keywords_pattern = (
        r"(?i)^\s*(?:"
        r"open|open\s+krwana\s+hai|open\s+karwana\s+hai|"
        r"business\s+wallet|bharat\s*pay|bharatpe|"
        r"paytm\s+business|bot|hi|hlo|hello"
        r")\s*[!.?]*\s*$"
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(open_keywords_pattern),
            user.start,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            user.callback_router,
            pattern=r"^(user:|svc:)",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            admin.admin_callback,
            pattern=r"^admin:",
        )
    )

    return app


def main() -> None:
    application = build_application()
    logger.info("India Business Wallet bot started.")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)


if __name__ == "__main__":
    main()
