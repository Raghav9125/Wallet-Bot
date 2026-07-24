import logging
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters
from config import Config
from database import Database
from handlers import admin, user

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',level=logging.INFO)

def build_application():
    config=Config.from_env(); db=Database(config.database_path); app=Application.builder().token(config.bot_token).build(); app.bot_data['db']=db; app.bot_data['admin_ids']=config.admin_ids
    user_conv=ConversationHandler(
        entry_points=[CallbackQueryHandler(user.callback_router,pattern=r'^(understood:|finalpay:|user:cancel)')],
        states={
            user.WAITING_FIRST_RECEIPT:[MessageHandler(filters.PHOTO,user.receive_first_receipt),CallbackQueryHandler(user.callback_router,pattern=r'^user:cancel$'),MessageHandler(~filters.PHOTO & ~filters.COMMAND,user.receive_first_receipt)],
            user.WAITING_FIRST_UTR:[MessageHandler(filters.TEXT & ~filters.COMMAND,user.receive_first_utr),CallbackQueryHandler(user.callback_router,pattern=r'^user:cancel$')],
            user.WAITING_FINAL_RECEIPT:[MessageHandler(filters.PHOTO,user.receive_final_receipt),CallbackQueryHandler(user.callback_router,pattern=r'^user:cancel$'),MessageHandler(~filters.PHOTO & ~filters.COMMAND,user.receive_final_receipt)],
            user.WAITING_FINAL_UTR:[MessageHandler(filters.TEXT & ~filters.COMMAND,user.receive_final_utr),CallbackQueryHandler(user.callback_router,pattern=r'^user:cancel$')],
        }, fallbacks=[CommandHandler('cancel',user.cancel_text),CommandHandler('start',user.start)],allow_reentry=True)
    admin_conv=ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.admin_callback,pattern=r'^admin:(set:|price:|reject:)')],
        states={admin.WAITING_SETTING:[MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND),admin.receive_setting)],admin.WAITING_PRICE:[MessageHandler(filters.TEXT & ~filters.COMMAND,admin.receive_price)],admin.WAITING_REJECT:[MessageHandler(filters.TEXT & ~filters.COMMAND,admin.receive_reject)]},
        fallbacks=[CommandHandler('admin',admin.admin_command)],allow_reentry=True)
    app.add_handler(CommandHandler('start',user.start)); app.add_handler(CommandHandler('admin',admin.admin_command)); app.add_handler(user_conv); app.add_handler(admin_conv)
    pattern=(r'(?i)^\s*(?:open|open\s+krwana\s+hai|open\s+karwana\s+hai|business\s+wallet|bharat\s*pay|bharatpe|paytm\s+business|bot|hi|hlo|hello)\s*[!.?]*\s*$')
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(pattern),user.start))
    app.add_handler(CallbackQueryHandler(user.callback_router,pattern=r'^(user:|svc:|finalpay:)'))
    app.add_handler(CallbackQueryHandler(admin.admin_callback,pattern=r'^admin:'))
    return app

def main(): build_application().run_polling(allowed_updates=Update.ALL_TYPES,drop_pending_updates=False)
if __name__=='__main__': main()
